---
name: visual-review
description: "Review a rendered web UI from screenshots without trusting a vision model for what code can measure: pin the environment (browser image, fonts, animations off, seeded data, masked regions), capture a viewport and theme matrix, pixel-diff against a baseline, run contrast, overflow, bounding-box, DOM-count and axe-core checks, then read native-resolution crops with DOM facts attached. Every finding cites a selector and box or is labelled unverified. Use for screenshot review or visual regression of a page. Casual asks include \"check the screenshots for layout bugs\", \"did this break dark mode\", \"does the mobile layout overflow\", or \"have the model look at the page\". Not for a flow heuristic review (ui-ux-review), a WCAG audit (accessibility-audit), breakpoints (responsive-design), flaky suites or CI screenshot diffs failing on fonts (e2e-testing) or hierarchy (visual-design)."
allowed-tools: "Read, Write, Glob, Grep, Bash(npx:*), Bash(node:*)"
---

# Visual Review

Review a rendered page from its screenshots, and report only what the evidence supports:
measured facts as verified, anything the model saw but code did not confirm as unverified.

A vision model reads a screenshot fluently and confidently, and it is wrong in exactly the
places a reviewer relies on it: whether two boxes overlap, whether a column is aligned,
how many cards are in a row, what the exact colour of a border is, whether small text is
legible. Code answers every one of those questions exactly. So the order matters. Make the
render deterministic, measure everything measurable, and spend the model's eyes only on
what is left, with the measurements beside the image so it is judging with facts rather
than guessing.

## Scope

Use for: a built page, component or Storybook story that renders in a browser you can
drive; a change that should not alter the way anything looks; a theme, breakpoint or
reduced-motion variant that may have broken; screenshot diffs that fail for no visible
reason.

Do not use for: a heuristic review of a flow or screen against usability principles
(`ui-ux-review`); a WCAG 2.2 conformance audit with the keyboard and screen-reader pass
(`accessibility-audit`), though axe-core runs here as one check; choosing breakpoints or
reflow behaviour (`responsive-design`); judging hierarchy, type and spacing as design
decisions (`visual-design`); keeping a browser test suite from flaking (`e2e-testing`).

## Workflow

### 1. Preflight: make the render deterministic

A diff against a baseline is only meaningful when the same input renders the same pixels.
Settle all five before capturing anything, because a finding on a nondeterministic render
cannot be told apart from noise.

- **Fixed browser image.** Capture in the same browser build, OS and font set that
  produced the baseline. Playwright's own guidance is to run tests in the environment
  where the baselines were generated, because rendering varies with host OS, version,
  hardware and headless mode. Use its Docker image for both baseline and comparison.
- **Fonts loaded.** Wait for `document.fonts.ready` and confirm the intended families
  resolved. Two identical frames of a fallback font still match each other.
- **Animations off.** Disable CSS animations, transitions and Web Animations for the
  capture, and move the pointer off the page so no hover state is baked in.
- **Seeded data.** Stub the network with fixed fixtures, a fixed locale and time zone, and
  a frozen clock, so lists, dates and counts are the same on every run.
- **Masked dynamic regions.** Mask what cannot be made stable (ads, embeds, live
  timestamps, avatars) and list each mask in the report, since a masked region is a region
  that was not reviewed.

Read `references/playwright-snapshots.md` for the settings, the config for the matrix and
the pixel-diff options. If there is no baseline yet, say so: the first run only produces
one, and a baseline nobody has reviewed is not evidence that the page is right.

### 2. Capture the matrix

Capture each page or state at widths 360, 768 and 1280, in light and dark, with reduced
motion on. Add one extra cell with reduced motion off at 1280 in light, because content
that only appears once an entrance animation finishes is invisible to the reduced
variant. Name every file with its cell (`checkout-w360-dark.png`) so a finding can point
at the exact capture.

Trim the matrix only by decision: a page with no dark theme drops that axis, and the
report says it did. Do not trim it because it is slow.

### 3. Pixel-diff against the baseline

Compare each capture with its baseline, cell by cell. A size mismatch is itself a finding
(the layout changed height or width), not an error to work around. Group differing pixels
into regions, then map each region to the DOM element under it in the same viewport so the
diff arrives as selectors and boxes rather than a red smear.

Leave the comparison thresholds alone while triaging. If a diff is noise, fix the
environment in step 1; loosening a threshold is the last resort and the report names the
value and the reason.

### 4. Code checks first

Run these before any model sees an image, on every cell of the matrix:

- the emulated state really applied: `matchMedia` for colour scheme and reduced motion,
  computed animation and transition durations, fonts loaded;
- horizontal overflow at 360, and the elements that cause it;
- computed colours and text/background contrast, with axe-core for the contrast rule;
- bounding boxes: overlap, clipping, elements outside the viewport, target sizes, gaps;
- DOM counts against the fixture data, and visible versus present;
- axe-core, with its `incomplete` results kept as unverified.

Read `references/code-checks.md` for the snippets, what each result means and which ones
code cannot decide. Each check that fails is already a verified finding; it needs no
image to confirm it.

### 5. Vision pass on native-resolution crops

Use the model only for what code could not settle: whether the composition reads
correctly, whether an image or icon is the right one, whether text looks truncated in a
way that matters, whether the dark theme looks coherent. Keep it narrow.

- **Crop, do not downscale.** Give the model one region at the capture's native
  resolution, not a whole full-page screenshot that gets resized before it is read. Small
  text and thin borders are the first things a resize destroys. Crop by the element boxes
  from step 4.
- **Attach the DOM facts.** With each crop, pass the selector, bounding box, visible text,
  computed font size, colour and background, and the matrix cell. A model told what the
  element is and measures stops inventing it.
- **Ask one narrow question per crop** ("is the label cut off at the right edge of this
  button?"), and ask what it sees before asking whether it is wrong.
- **Treat its geometry as a lead.** Overlap, alignment, counts and exact colours it
  reports are hypotheses for step 4's checks, not findings.

Delegate the reading to the `screenshot-reader` subagent: it keeps the images out of the
main context and returns observations in a fixed shape. Give it the crops, the DOM facts
and the questions, nothing else, and verify what comes back the same way.

### 6. Report verified and unverified separately

Every finding cites a selector and a bounding box, with the matrix cell, or it is
labelled unverified. Keep the two in separate lists; a reader should be able to act on the
first without reading the second.

```text
Verified (measured by code)
  1. [cell] selector, box x,y,w,h: what was measured, the value, the expectation.
Unverified (seen in an image, not confirmed by a check)
  1. [cell] crop, what the model reported, why code could not settle it, how to confirm.
Diff regions
  [cell] region box, nearest element, baseline changed or new.
Not reviewed
  masked regions, matrix cells skipped and why, states not captured.
```

State a severity and the smallest fix for each verified finding. An unverified finding
carries the check that would confirm it and does not get a severity until it is.

## Anti-patterns

**Sending the full-page screenshot and asking what is wrong.** The model resizes it, finds
plausible problems in the blur and misses the real ones. Measure first and crop.

**Believing the model on overlap, alignment or counts.** It answers with the same
confidence whether it is right or wrong. A bounding-box intersection or a DOM count takes
one line and is exact.

**Loosening the diff threshold until CI is green.** The diff stops seeing the regressions
it exists for. Fix the environment, then mask, then loosen last and say so.

**Capturing in one environment and comparing in another.** Font hinting and anti-aliasing
differ between machines, so every diff lights up. Generate and compare in the same image.

**Reporting a pass for a cell that was not captured.** A skipped cell and a masked region
go under "Not reviewed", never under "no issues".

**Reviewing a baseline that was never reviewed.** Updating snapshots to make a failure go
away records the bug as the new truth. Read the baseline diff before accepting it.
