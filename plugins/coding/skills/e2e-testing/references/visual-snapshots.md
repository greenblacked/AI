# Stable screenshot assertions

A screenshot assertion fails for two reasons that look identical in the report: the page changed, or the machine rendering it did. Everything here removes the second reason, so that a red run means the first. The failure it prevents is the familiar one: baselines that pass on the laptop that made them, fail in CI, and get loosened until the assertion no longer notices a real regression.

The API facts are Playwright's, checked against the `microsoft/playwright` documentation sources at tag `v1.64.1` (`docs/src/test-snapshots-js.md`, `docs/src/docker.md`, `docs/src/ci.md`, `docs/src/test-cli.md` and the API sources under `docs/src/api/` and `docs/src/test-api/`). Option names and defaults change between releases, so re-check them against the version you run. Where a claim is guidance rather than something the documentation states, the text says so.

## Contents

- [Fix the environment before the thresholds](#fix-the-environment-before-the-thresholds)
- [Wait for fonts](#wait-for-fonts)
- [Remove motion and time](#remove-motion-and-time)
- [Mask, hide, or seed what changes](#mask-hide-or-seed-what-changes)
- [Threshold against maxDiffPixels](#threshold-against-maxdiffpixels)
- [Naming baselines per browser and platform](#naming-baselines-per-browser-and-platform)
- [Updating baselines and reviewing the diff](#updating-baselines-and-reviewing-the-diff)
- [Outside Playwright: pixelmatch and odiff](#outside-playwright-pixelmatch-and-odiff)

## Fix the environment before the thresholds

The documentation's own warning is that rendering varies with the host OS, version, settings, hardware, power source, headless mode and other factors, and that screenshots are only reliable when tests run in the environment where the baselines were generated. So the first decision is where baselines are made, and it is made once for the whole team.

Generate and compare in one pinned container. Playwright publishes an image with the browsers and their system dependencies, `mcr.microsoft.com/playwright:v<version>-noble`, where `<version>` is the version of `@playwright/test` in your lockfile. Pin to a specific version: the documentation says a mismatch between the image's Playwright version and the project's leaves Playwright unable to locate browser executables. The image tags also name the Ubuntu release (`noble`, `jammy`, `resolute`). A different Ubuntu release is a different set of system libraries and fonts (guidance, not a documented claim), so treat the release as part of the pin and change it deliberately.

In GitHub Actions, run the job in the container. Playwright's CI guide recommends this for exactly this purpose, consistent screenshots for visual regression testing, and shows the shape:

```yaml
jobs:
  playwright:
    runs-on: ubuntu-latest
    container:
      image: mcr.microsoft.com/playwright:v1.64.1-noble
      options: --user 1001
```

Every shard of a sharded run uses the same image, or two shards render the same page two ways and the failures follow the shard rather than the change.

A developer on macOS or Windows then cannot produce a baseline natively, and that is the point: a baseline made there is the one that fails in CI. Give them one command that runs the update inside the same image (see [Updating baselines](#updating-baselines-and-reviewing-the-diff)). The Docker guide recommends `--ipc=host` when running Chromium, because without it Chromium can run out of memory and crash, and `--init` to avoid zombie processes.

For contributors who cannot run the container at all, `ignoreSnapshots: !process.env.CI` in the config skips snapshot expectations locally and keeps them in CI; the documentation shows that exact line. Use it only if CI really runs the assertions, otherwise it switches visual coverage off while looking green.

## Wait for fonts

A screenshot taken before a web font arrives records the fallback font, and the next run records the real one. The CSS Font Loading specification provides `document.fonts.ready` for this: a promise that resolves when the document is done loading fonts. Three properties of it matter:

- A given `ready` promise is fulfilled only once, and further fonts may load after it. Await it after the content that uses the fonts has rendered, not at navigation start.
- It is fulfilled only after layout completes and no further font loads are needed, so fallback chains are covered.
- It is never rejected, so it does not signal a font that failed to load. A broken font URL passes the wait and renders the fallback.

`page.evaluate` waits for a returned promise, so the wait is one line:

```ts
await page.goto('/pricing');
await page.evaluate(() => document.fonts.ready);
await expect(page).toHaveScreenshot('pricing.png');
```

Put this in a helper or fixture and call it before every screenshot rather than in a few tests. Serve the fonts from your own origin or the test build, so a third-party font CDN is not a variable. Because the wait cannot fail on a font that never loaded, assert once on the thing it cannot check, for instance the computed `font-family` of a heading, or look at the first baseline by eye. Fonts the page does not ship (system fonts) come from the container image, which is a further reason to pin it.

## Remove motion and time

`toHaveScreenshot` disables animations by default (`animations: 'disabled'`). Finite CSS animations, CSS transitions and Web Animations are fast-forwarded to completion and fire `transitionend`; infinite ones are cancelled to their initial state and played again after the screenshot. The text caret is hidden by default (`caret: 'hide'`). The assertion also keeps taking screenshots until two consecutive ones match before it compares, which absorbs a short settling time but not content that never settles.

What this does not cover is motion the browser cannot see as an animation: a carousel advanced by `setInterval`, a canvas or `requestAnimationFrame` loop, video, a count-up number, a skeleton that swaps on a timer. Treat each as its own decision, in order of preference:

1. Put the page in the state you want to capture (pause the carousel, finish the load, wait on the element that signals completion). This is the rule of the rest of this skill: wait on state, not on time.
2. If the app honours `prefers-reduced-motion`, set `reducedMotion: 'reduce'` in `use`. It emulates the media feature and changes nothing in an app that ignores it.
3. Hide or mask the region (next section).

Screenshots capture hover effects present at that moment. Move the pointer somewhere inert before the assertion, as the documentation does: `await page.mouse.move(-1, -1);`.

For anything that reads the clock (a "posted 3 minutes ago" label, a date picker defaulting to today), fix the time instead of masking it. `page.clock.setFixedTime(...)` makes `Date.now` and `new Date()` return a fixed time while timers keep running; `page.clock.install()` fakes more of the timing functions when you need to control them. Call it before the page loads.

## Mask, hide, or seed what changes

Prefer removing the variation at its source: seeded test data, a fixed clock, a stubbed third-party widget. A masked region is a region the test no longer checks, so spend masks only where the source cannot be controlled (an embedded map, an ad slot, a user-uploaded avatar).

`mask` takes locators. Each is overlaid with a box of `maskColor` (default pink `#FF00FF`) covering its bounding box, and the mask is applied to invisible elements too:

```ts
await expect(page).toHaveScreenshot('dashboard.png', {
  mask: [page.getByTestId('last-updated'), page.locator('iframe')],
  maskColor: '#808080',
});
```

A mask hides the content of a box but not its size. If masked text can change length, the box can reflow its neighbours and the comparison fails anyway; fix the width of the container, or hide the element with `stylePath` instead.

`stylePath` applies a stylesheet only while the screenshot is taken, and the documentation states it pierces the Shadow DOM and applies to inner frames. Use `visibility: hidden` to keep layout stable; `display: none` removes the element from layout and shifts everything after it, which changes the picture rather than stabilising it.

```css
/* screenshot.css */
iframe,
[data-volatile] {
  visibility: hidden;
}
```

Both have project-wide defaults under `expect.toHaveScreenshot` in the config. A config-level `stylePath` is the place for the rules every screenshot needs; a per-assertion `mask` is for the exceptions.

Prefer a screenshot of an element (`expect(locator).toHaveScreenshot()`, which exists alongside the page form) over the full page when a component is the subject. A smaller image has fewer pixels that can differ for reasons unrelated to the change, and a failure points at the component. Use `fullPage: true` for the few pages whose overall layout is the subject. This is guidance; the documentation only states that both forms exist.

## Threshold against maxDiffPixels

The options answer different questions, and the usual mistake is to raise one when the other is the one that matters.

| Option | Question it answers | Default |
| --- | --- | --- |
| `threshold` | How different must one pixel be, compared with the same pixel in the baseline, to count as different. Perceived colour difference in the YIQ colour space, from `0` (strict) to `1` (lax). | `0.2` |
| `maxDiffPixels` | How many pixels past the threshold the assertion tolerates. | unset |
| `maxDiffPixelRatio` | The same as a fraction of the total pixels, between `0` and `1`. | unset |

`threshold` is not a share of the image. The pixelmatch documentation, whose library Playwright's comparison uses, says so explicitly: it is a per-pixel perceptual difference where `1` is the difference between black and white, and a percentage of the image is expressed by comparing the returned count against the image size. The two kinds of option therefore give away different things:

- Raising `threshold` makes low-contrast changes invisible everywhere on the page: a colour token moving a few shades, a grey border becoming a slightly different grey.
- Raising `maxDiffPixels` makes small changes invisible anywhere, however stark: a missing icon, one changed digit, a thin rule shifted by a pixel. A fixed count also means different things on a button and on a full page; `maxDiffPixelRatio` scales with the image.

Neither is a fix for nondeterminism. If a baseline needs a tolerance to pass on a second run in the same container, something on the page is still changing; find it with the sections above. Where a small tolerance is legitimate (anti-aliasing noise on a large page), set it per project in the config, write the reason beside the number, and keep it far below the size of the smallest regression you care about. Left unset, no allowance for differing pixels is configured.

```ts
// playwright.config.ts
export default defineConfig({
  expect: {
    // Anti-aliasing noise on the full-page shots; smaller than any icon or glyph.
    toHaveScreenshot: { maxDiffPixelRatio: 0.001 },
  },
});
```

## Naming baselines per browser and platform

Baselines are stored next to the test file in a `<test file>-snapshots` directory, with the browser and the platform in the file name: `example-test-1-chromium-darwin.png` in the documentation's example. The documentation says screenshots differ between browsers and platforms because of rendering, fonts and more, so each combination needs its own file. When a config has multiple projects, the project name replaces the browser name.

Consequences worth acting on:

- Name the projects for what varies the picture, not only the browser: `chromium-desktop`, `chromium-mobile`, `chromium-dark`. Each gets its own baseline, and a viewport or colour-scheme change cannot overwrite another project's.
- Give screenshots that matter explicit names (`toHaveScreenshot('pricing-table.png')`). The auto-generated name (`example-test-1`) is numbered, so inserting a screenshot earlier in a test renames the later ones.
- Commit the whole snapshots directory. The documentation says to commit it and review changes to it.
- If every run happens in the pinned container, only `linux` baselines should exist. A `-darwin` or `-win32` file in a diff is a developer's accidental native run; do not commit it.

`snapshotPathTemplate`, or `expect.toHaveScreenshot.pathTemplate` for screenshots only, changes the location. Its tokens include `{platform}` (the value of `process.platform`), `{projectName}`, `{arg}`, `{ext}`, `{testFilePath}` and `{testName}`. A template that drops `{platform}` gives the same file name on every OS, so a native run on another OS compares against the container's baseline and fails, which is the failure you want. The risk is someone reacting to it by adding `{platform}` back and committing a second set of baselines that CI never reads.

Snapshots are PNG by default; a name ending `.webp` stores a lossless WebP instead, and `expect.toHaveScreenshot.type: 'webp'` does that for unnamed ones.

## Updating baselines and reviewing the diff

Without an update flag, a missing baseline is created but the test that created it fails (`updateSnapshots: 'default'`), so a new screenshot test cannot pass silently in CI. Keep that default.

The flag is `-u` or `--update-snapshots [mode]`; the modes are `all`, `changed`, `missing`, `none` and `default`. With the flag and no value it means `changed`: snapshots that did not match are rewritten, and missing ones are created. Prefer `changed`, restricted to the tests you meant to affect (a file path or `--grep`), over `all`. `all` rewrites every executed snapshot, which makes any incidental sub-threshold difference part of the change and buries the intended one.

Run the update in the pinned image:

```bash
docker run --rm --init --ipc=host -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v1.64.1-noble \
  sh -c 'npm ci && npx playwright test pricing.spec.ts --update-snapshots=changed'
```

Guidance beyond the documentation: mount a named volume at `/work/node_modules` so the container does not overwrite a host install built for another OS, expect root-owned files on a Linux host unless you pass `--user`, and wrap the command in a package script so nobody types it from memory.

When to update, and when not to:

- Update when the change under review intentionally alters how the page looks, and say so in the pull request. A baseline change in a pull request that claims to change behaviour only is a finding.
- Do not update to clear a red run you have not explained. Reproduce the failure in the container first with `--repeat-each`; if it passes some runs and fails others, it is flake in the capture, and the fix belongs in the page or the wait, not the baseline.
- Do not refresh baselines automatically on failure. A job that regenerates and commits on red turns the assertion into a recording of whatever the code did last.

Reviewing the change: open the failed run's report or trace and use the Attachments tab, which shows the image diff, the actual image and the expected image, with a slider to slide one image over the other. Then ask of every changed region whether the source diff explains it. A baseline diff that touches regions the code change cannot reach (a footer, when only a form changed) is either a missed source of variation or an unrelated regression, and either blocks the update. Review the changed PNGs as images, one at a time; a green check on binary files proves only that the commit applies.

Keep baseline updates in their own commit, so that reverting a visual change does not mean untangling it from a code change.

## Outside Playwright: pixelmatch and odiff

If the pipeline captures screenshots with something else (Cypress, Selenium, a Storybook screenshot job), the same rules apply to capture: one pinned environment, fonts awaited, motion removed. The comparison step can then be a library.

**pixelmatch** (`mapbox/pixelmatch`) compares two images and returns the number of mismatched pixels. Its documented behaviour:

- All three images (two inputs and the diff output) must have the same dimensions. The bundled command-line binary exits `0` when images match, `66` when they differ and `65` when their dimensions do not match.
- `threshold` is per-pixel, from `0` to `1`, and defaults to `0.1`. Playwright's default is `0.2`, so copying a number from one to the other is not a no-op.
- `includeAA` defaults to `false`, meaning anti-aliased pixels are detected and ignored. Setting it to `true` disables that detection.
- The result is a count, so the equivalent of `maxDiffPixels` is a comparison you write against the return value, along with the decision that a size mismatch fails the test.

**odiff** (`dmtrKovalenko/odiff`) is a native image-difference tool with a CLI and a Node API in the `odiff-bin` package. Its documented options include `threshold` (0 to 1), `antialiasing`, `ignoreRegions` (an array of `{ x1, y1, x2, y2 }`), `failOnLayoutDiff`, and `captureDiffLines` with `captureDiffCols`, which together give the bounding rectangle of the change. The result is `{ match: true }`, a `layout-diff` reason when the image layouts differ, or a `pixel-diff` reason with a `diffCount`. Two points to read carefully:

- The polarity of the anti-aliasing option is the opposite of pixelmatch's: odiff's `antialiasing: true` means anti-aliased pixels are not counted, while pixelmatch's `includeAA: true` means they are. Check which way a ported configuration points.
- `ignoreRegions` plays the part of Playwright's `mask`. It takes pixel coordinates, so it is only as stable as the layout; fix the source of variation where you control the app.

The odiff README lists a `playwright-odiff` package that adds an odiff-backed screenshot assertion to Playwright. Its behaviour was not checked here, so measure it against Playwright's own comparator before switching.

Whichever comparison runs, keep its diff image (pixelmatch's output, odiff's diff file) as an artefact of the failed run, so a reviewer sees what changed without rerunning the job.
