# Playwright snapshot settings

Settings for the capture, matrix and pixel-diff steps of `visual-review`. The option names
and defaults below come from the Playwright documentation
([visual comparisons](https://playwright.dev/docs/test-snapshots), the
[`toHaveScreenshot` assertion](https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot-1)
and the [emulation guide](https://playwright.dev/docs/emulation)) and the
[pixelmatch README](https://github.com/mapbox/pixelmatch). Defaults change between
releases, so check the version you have installed before relying on one.

## Contents

- Same environment for baseline and comparison
- The viewport and theme matrix as projects
- Capture options that make a render repeatable
- Masking what cannot be stabilised
- Thresholds, and what to do before touching them
- Diffing outside the test runner
- Updating baselines

## Same environment for baseline and comparison

Playwright warns that rendering varies with host OS, version, settings, hardware, power
source and headless mode, and tells you to run where the baselines were generated.
Snapshot file names carry the browser and platform (`example-test-1-chromium-darwin.png`)
because screenshots differ between them, so a baseline made on a laptop will not be
found, or will not match, on a Linux runner.

Generate and compare inside the published Playwright image, at the tag that matches your
installed `@playwright/test`, so fonts, anti-aliasing and the browser build are identical.
The image is for trusted code; Microsoft says not to use it to visit untrusted sites.

```bash
docker pull mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble
docker run --rm --ipc=host -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v${PLAYWRIGHT_VERSION}-noble \
  npx playwright test --project=w360-dark
```

The image does not contain the Playwright package, so install your dependencies inside
the container or bake them into a derived image. Record the image tag next to the
baselines; a baseline with no recorded environment cannot be reproduced.

## The viewport and theme matrix as projects

Each cell of the matrix is a project. The project name replaces `chromium` in the
snapshot file name, so every cell gets its own baseline without extra naming.

```ts
// playwright.config.ts
import { defineConfig } from '@playwright/test';

const widths = [360, 768, 1280];
const schemes = ['light', 'dark'] as const;

export default defineConfig({
  projects: [
    ...widths.flatMap((width) =>
      schemes.map((colorScheme) => ({
        name: `w${width}-${colorScheme}`,
        use: {
          viewport: { width, height: 800 },
          colorScheme,
          reducedMotion: 'reduce' as const,
        },
      })),
    ),
    // One extra cell: motion on, so content gated by an entrance animation is seen.
    {
      name: 'w1280-light-motion',
      use: {
        viewport: { width: 1280, height: 800 },
        colorScheme: 'light',
        reducedMotion: 'no-preference',
      },
    },
  ],
});
```

`colorScheme` takes `light`, `dark` or `no-preference`; `reducedMotion` takes `reduce` or
`no-preference`, and `no-preference` is the default. The height is a choice: use
`fullPage` to capture below it. Pick one `deviceScaleFactor` for the whole matrix and keep
it, since a baseline and a capture at different factors differ in dimensions and cannot be
compared.

The emulation is a request, not a proof. Confirm in the page that it took effect, with the
`matchMedia` checks in `references/code-checks.md`.

## Capture options that make a render repeatable

```ts
import { test, expect } from '@playwright/test';

test('checkout', async ({ page }) => {
  await page.goto('/checkout');
  await page.evaluate(() => document.fonts.ready);
  await page.mouse.move(-1, -1); // keep the pointer off every hover state
  await expect(page).toHaveScreenshot('checkout.png', {
    animations: 'disabled',
    caret: 'hide',
    fullPage: true,
    mask: [page.locator('[data-testid="live-clock"]')],
  });
});
```

What each setting does, as documented:

| Option | Behaviour | Default |
| --- | --- | --- |
| `animations` | `disabled` fast-forwards finite animations to completion and cancels infinite ones to their initial state | `disabled` for `toHaveScreenshot`, `allow` for `page.screenshot` |
| `caret` | `hide` hides the text caret | `hide` |
| `fullPage` | captures the whole scrollable page rather than the viewport | `false` |
| `scale` | `css` gives one pixel per CSS pixel, `device` one per device pixel | `css` for `toHaveScreenshot`, `device` for `page.screenshot` |
| `stylePath` | a stylesheet applied while capturing, piercing shadow DOM and inner frames | none |
| `mask`, `maskColor` | overlay locators with a solid box covering the bounding box, including invisible elements | pink `#FF00FF` |

`toHaveScreenshot` waits until two consecutive screenshots match, then compares the last
one. That settles motion and late paints but not a font that has not started loading, so
the explicit wait for `document.fonts.ready` stays.

The `scale` defaults differ between `toHaveScreenshot` and `page.screenshot`. A crop taken
with `locator.screenshot` for the vision pass defaults to device pixels, so set `scale`
explicitly if the baseline was taken at `css`.

## Masking what cannot be stabilised

Seed the data first (fixed fixtures through network stubs, a fixed locale and time zone, a
frozen clock) and mask only what stays dynamic: embeds, ads, avatars, a live timestamp.
`stylePath` can hide volatile elements across the whole suite without editing each test:

```css
/* screenshot.css */
iframe {
  visibility: hidden;
}
```

Hiding with `visibility` keeps the layout box, so neighbours do not shift. Every mask and
hidden selector goes in the report's "Not reviewed" list; whatever sits under a mask was
not looked at.

## Thresholds, and what to do before touching them

Playwright's `threshold` is a per-pixel perceived colour difference from 0 (strict) to 1
(lax), and defaults to 0.2. `maxDiffPixels` is an acceptable count of differing pixels and
`maxDiffPixelRatio` an acceptable ratio of differing pixels to total, between 0 and 1;
`maxDiffPixels` is unset by default. Playwright's `threshold` is not the same default as
standalone pixelmatch, which uses 0.1, so a threshold copied between the two changes
meaning.

Work down this order and stop at the first fix that makes the diff stable:

1. Same image for baseline and comparison.
2. Wait for fonts and for the page to settle.
3. Disable animations and move the pointer off the page.
4. Seed the data and freeze the clock.
5. Mask or hide the region that stays dynamic.
6. Only then loosen `maxDiffPixels`, `maxDiffPixelRatio` or `threshold`, on that test
   alone, and write the value and the reason in the report.

A global loosening is the same defect as deleting the test: it hides the regressions the
diff exists to find.

## Diffing outside the test runner

When the captures come from a script or another tool, pixelmatch compares two raw images:

```js
const diffPixels = pixelmatch(baseline.data, actual.data, diff.data, width, height, {
  threshold: 0.1,
});
```

- All three images, including the diff output, need the same dimensions. Treat a size
  mismatch as a finding in its own right (the page changed height or width) and not as
  something to crop away. The pixelmatch CLI exits with a distinct code for it.
- `includeAA` is `false` by default, so anti-aliased pixels are detected and ignored.
  Turning it on makes font rendering differences count.
- `ignoreMask` takes one value per pixel, `width * height` long; non-zero pixels are
  excluded from the comparison and drawn as unchanged. Use it for the same regions you
  would mask in Playwright.
- `windowSize` returns the largest count of differing pixels in any N by N window rather
  than the total, which separates one real defect from a scatter of single-pixel noise.
- The return value is a count. To allow a share of the image to differ, compare the count
  with `width * height` yourself.

To turn a diff into reviewable regions, group neighbouring differing pixels into boxes,
then call `document.elementFromPoint` at each box centre in the same viewport and report
that element's selector and bounding box next to the box. A region with no element is
usually the page background and means the layout shifted.

## Updating baselines

`npx playwright test --update-snapshots` rewrites the baselines. Run it only after reading
the diff, and review the changed images in the pull request, because an accepted update
records the defect as the new truth. Commit the snapshot directory with the change that
caused it, not separately.
