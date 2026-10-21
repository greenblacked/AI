# Code checks before the vision pass

The checks `visual-review` runs on every cell of the matrix before a model sees an image.
Each answers a question exactly that a vision model answers fluently and sometimes
wrongly. A failed check is a verified finding with a selector and a box, so it needs no
image to confirm it.

## Contents

- Collect the facts once
- Did the emulated state apply
- Horizontal overflow at 360
- Colours and contrast
- Bounding boxes: overlap, clipping, target size, spacing
- DOM counts and visibility
- Images and fonts
- axe-core
- What code cannot decide

## Collect the facts once

Run one `evaluate` per element of interest and per cell, save the JSON beside the
screenshot, and reuse it for every crop. The same facts go to the vision pass, so the model
is told what each element is instead of guessing.

```ts
import type { Locator } from '@playwright/test';

const describe = (locator: Locator) =>
  locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return {
      tag: el.localName,
      text: (el.textContent ?? '').trim().slice(0, 120),
      box: { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height },
      visible: el.checkVisibility(),
      color: s.color,
      background: s.backgroundColor,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
    };
  });
```

Only serialisable values cross back from the page, so the function builds plain objects.
Use a stable selector you wrote (`data-testid`, an id, a role and name) as the selector in
the report. A generated path breaks on the next markup change, and a finding that cannot
be found again cannot be fixed. Report the selector together with the box and the matrix
cell.

## Did the emulated state apply

A project that asks for dark mode or reduced motion has asked, not proved. Check in the
page, per cell:

```ts
const state = await page.evaluate(async () => {
  await document.fonts.ready;
  return {
    dark: matchMedia('(prefers-color-scheme: dark)').matches,
    reduced: matchMedia('(prefers-reduced-motion: reduce)').matches,
    bodyBackground: getComputedStyle(document.body).backgroundColor,
    // JSON.stringify writes Infinity as null, which would hide an infinite animation.
    running: document.getAnimations().map((a) => ({
      name: a.animationName ?? a.id,
      ...Object.fromEntries(
        Object.entries(a.effect?.getComputedTiming() ?? {}).map(([k, v]) => [
          k,
          v === Infinity ? 'infinite' : v,
        ]),
      ),
    })),
    faces: [...document.fonts].map((f) => ({ family: f.family, status: f.status })),
  };
});
```

- `dark` and `reduced` must match the cell. If they do not, every screenshot in that cell
  is mislabelled.
- Pages that switch theme with a class or attribute rather than the media query need that
  switch applied too; check the class or attribute and that `bodyBackground` actually
  differs between the two schemes.
- `running` is read before the screenshot, so Playwright's `animations: "disabled"` has
  not acted on it yet; it lists what that option will have to stop. An entry with
  infinite iterations is the usual cause of a capture that differs run to run. Under
  reduced motion a page may keep short or non-moving animations, such as a fade, so the
  check there is that nothing left moves or loops, not that the list is empty.
- `faces` lists every `@font-face` the stylesheets declare, and one the page never
  renders (an unused italic, weight or subset) stays `unloaded`; that is not a failure.
  Fail on any face with status `error`, which failed to download, and for each family,
  weight and style the design renders call `document.fonts.load()` and expect at least
  one face back, as the `e2e-testing` skill's visual-snapshot reference shows.
  `document.fonts.status` reads `loaded` and `document.fonts.check()` returns true even
  when no face for the family exists, because the browser falls back without an error, so
  neither proves the right font rendered; a system font is not in the set at all, and the
  DevTools check below is the one that sees it.

## Horizontal overflow at 360

```ts
const overflow = await page.evaluate(() => {
  const root = document.documentElement;
  const offenders = [...document.querySelectorAll('body *')]
    .map((el) => ({ el, r: el.getBoundingClientRect() }))
    .filter(({ r }) => r.width > 0 && (r.right > root.clientWidth || r.left < 0))
    .map(({ el, r }) => ({ tag: el.localName, id: el.id, cls: el.className, right: r.right }));
  return { scrollWidth: root.scrollWidth, clientWidth: root.clientWidth, offenders };
});
```

`scrollWidth > clientWidth` on the root is the finding; the offenders are the cause. Exclude
elements inside a deliberate horizontal scroller (a code block or a data table with
`overflow-x: auto`), whose own overflow is intended. Report the offenders deepest first,
because a wide child usually makes its ancestors report as offenders too. WCAG reflow
conformance at its own width belongs to `accessibility-audit`; this check is about whether
the layout holds at the narrowest cell.

## Colours and contrast

Read what the browser computed, not what the stylesheet says or the image seems to show:

```ts
const style = await locator.evaluate((el) => {
  const s = getComputedStyle(el);
  return {
    color: s.color,
    background: s.backgroundColor,
    fontSize: s.fontSize,
    fontWeight: s.fontWeight,
    opacity: s.opacity,
  };
});
```

- `backgroundColor` is often transparent; the visible background is the nearest ancestor
  with a non-transparent one, blended with any alpha. Walk up and blend before comparing.
- Compare computed values with the design tokens the page is meant to use. A different
  value in dark mode is the usual defect.
- A background image, gradient or video behind text cannot be reduced to one colour. Mark
  the contrast of such text unverified instead of guessing.
- For the ratio itself, use axe-core's `color-contrast` rule rather than your own
  arithmetic, and keep its `incomplete` results (a node it could neither pass nor fail) in
  the unverified list. The thresholds for normal and large text are the WCAG 1.4.3 ones;
  `accessibility-audit` carries them.

## Bounding boxes: overlap, clipping, target size, spacing

Boxes from `getBoundingClientRect` answer questions about geometry exactly:

- **Overlap.** Two boxes intersect when each starts before the other ends on both axes.
  Check siblings and any pair the vision pass suspects. An intersecting pair where one is
  a deliberate overlay (a badge, a tooltip) is expected; the finding is the unexpected one.
- **Clipped text.** An element whose `scrollWidth > clientWidth` or `scrollHeight >
  clientHeight` with `overflow` hidden, or with `text-overflow: ellipsis` where the full
  text matters, is cutting content off.
- **Outside the viewport.** A box with `right > innerWidth` or `left < 0` that is not in a
  scroller.
- **Target size.** Compare the width and height of interactive elements with the
  threshold your target criterion sets (see target size in `accessibility-audit`) and
  include padding that is part of the hit area.
- **Spacing.** Gaps between siblings are differences between boxes. Compare them with the
  spacing scale or the computed `gap`, `margin` and `padding`, and report a gap that
  differs from its siblings by selector pair.
- **Stacking and visibility.** `document.elementFromPoint` at a control's centre should
  return the control or a descendant; anything else means it is covered.

## DOM counts and visibility

The vision pass miscounts repeated items. Count in the DOM and compare with the fixture:

```ts
const counts = await page.evaluate(() => ({
  cards: document.querySelectorAll('[data-testid="product-card"]').length,
  visibleCards: [...document.querySelectorAll('[data-testid="product-card"]')].filter((el) =>
    el.checkVisibility(),
  ).length,
}));
```

Present but not visible and visible but not present are different defects. The expected
count comes from the seeded data, which is why step 1 seeds it.

## Images and fonts

- A broken image shows as `complete && naturalWidth === 0` on the `img` element.
- Check `alt` is present and that decorative images have an empty one, not a missing one.
- Listen for page `console` errors and failed requests during the capture; a missing asset
  often shows in them before it shows as an empty box.
- A fallback font is the cause of a reflow, not a layout bug, so report it as such. The
  computed `font-family` cannot show it: it returns the declared list whatever rendered.
  In Chromium, ask the DevTools protocol which faces drew the node's glyphs:

  ```ts
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');
  await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: 'h1' });
  const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
  // [{ familyName, isCustomFont, glyphCount }, ...]
  ```

  A web font shows `isCustomFont: true`. Any entry that is not the expected face, with its
  `glyphCount`, is text that fell back, including single glyphs the font does not cover.

## axe-core

Playwright documents the `@axe-core/playwright` package for running the axe engine in a
test. It scans the page in its current state, so interact with the page first to reveal
anything hidden behind a control.

```ts
import AxeBuilder from '@axe-core/playwright';

const results = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
  .analyze();
// results.violations -> verified findings, each node has a target selector
// results.incomplete -> unverified: axe could neither pass nor fail the node
```

- Each violation node carries a `target` selector, which is the selector half of a
  finding; take the box from the page.
- `incomplete` results are axe asking for a human or another check. Report them as
  unverified with the failure summary it gives.
- An empty `violations` list is not an accessibility pass. Playwright's own guidance
  says automated testing cannot detect every WCAG violation. The keyboard, focus and screen
  reader work stays with `accessibility-audit`.
- Run it in every theme cell, not once. Contrast failures live in the dark theme as often
  as the light one.

## What code cannot decide

Hand these to the vision pass, and label what comes back unverified until a check or a
person confirms it:

- whether an image, icon or illustration is the right one and reads as intended;
- whether the composition looks balanced, or a dark theme looks coherent as a whole;
- whether truncated text loses meaning;
- rendering artefacts with no DOM cause (a corrupted image, a canvas or video frame);
- text over a gradient, photograph or video.

For each, the report says which check would settle it if one exists, and otherwise that it
needs a person.
