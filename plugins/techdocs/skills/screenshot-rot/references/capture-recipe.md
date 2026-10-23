# Capture recipe

Read this when writing the capture scripts and the CI job that regenerates them. The
example uses Playwright's library API in TypeScript; the same options exist in its Python,
Java and .NET bindings under their own naming conventions.

## Contents

- [The manifest](#the-manifest)
- [A worked capture](#a-worked-capture)
- [Determinism checklist](#determinism-checklist)
- [Compare and propose](#compare-and-propose)

## The manifest

Keep one manifest file listing every scripted image. It is what the CI job iterates over
and what a reviewer reads beside an image change:

```yaml
- id: billing-invoices
  output: docs/images/generated/billing-invoices.png
  url: /settings/billing
  target: { role: region, name: Invoices }
  highlight: { role: switch, name: Send invoices by email }
  mask: [avatar]
  alt: "The Send invoices by email switch, in the Invoices section of Billing, turned on"
  used_by:
    - docs/guides/invoices.md
```

Generated images live in their own directory, so nobody edits one by hand thinking it is a
normal asset, and so the inventory can tell scripted from hand-made at a glance.

## A worked capture

```ts
import { chromium } from 'playwright';

const baseUrl = process.env.DOCS_CAPTURE_BASE_URL;
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,
  colorScheme: 'light',
  locale: 'en-GB',
  timezoneId: 'UTC',
  reducedMotion: 'reduce',
  storageState: 'capture/demo-user.json',
});
const page = await context.newPage();
await page.clock.setFixedTime(new Date('2026-01-15T10:00:00Z'));
await page.goto(`${baseUrl}/settings/billing`);

const section = page.getByRole('region', { name: 'Invoices' });
await section.waitFor();

// The callout is part of the capture, so it survives regeneration.
await page
  .getByRole('switch', { name: 'Send invoices by email' })
  .evaluate((el) => { el.style.outline = '3px solid #d9480f'; el.style.outlineOffset = '4px'; });

await section.screenshot({
  path: 'docs/images/generated/billing-invoices.png',
  animations: 'disabled',
  caret: 'hide',
  mask: [page.getByTestId('avatar')],
});
await browser.close();
```

Notes on the choices:

- `deviceScaleFactor: 2` gives sharp images on high-density screens and doubles the pixel
  dimensions; set the displayed width in the page markup so the image is not shown at
  twice its intended size.
- `storageState` loads a session saved once by a login step against the demo tenant, so
  each capture does not repeat the login flow.
- Locating by role and accessible name, as an end-to-end suite would, means a capture
  breaks loudly when a label changes instead of silently photographing the wrong element.
- `page.clock.setFixedTime` fixes what `Date.now()` returns in the page. Where the server
  renders dates, fix them in the demo fixtures instead.
- A locator screenshot crops to that element. Prefer it to a full-page capture whenever
  the point of the image is one region.

## Determinism checklist

Run each capture twice in a row before committing it. If the two images differ, find the
cause from this list before going further:

| Source of change | Fix |
| --- | --- |
| Fonts differ between machines | Capture only in the pinned container image, with the product's fonts installed in it |
| Browser version | Pin the automation library version and its matching browser build |
| Clock and relative times | Fixed clock in the page; fixed timestamps in fixtures |
| Data | Reset the demo tenant from fixtures before every run; never share it with manual testing |
| Animations, transitions, carets, spinners | Reduced motion, animations disabled, caret hidden, wait for the final element |
| Avatars, random IDs, third-party widgets | Mask them, or stub them in the demo environment |
| Late-loading content | Wait for the specific element that completes the view, not for network idle |
| Scrollbars and window chrome | Element screenshots, fixed viewport |

## Compare and propose

The scheduled job, in outline:

1. Build or deploy the release being documented to a capture environment, and reset the
   demo tenant.
2. Run every manifest entry into a scratch directory.
3. Compare each new image with the committed one. A pixel diff with a small per-pixel
   tolerance absorbs anti-aliasing noise: for example `pixelmatch`, or ImageMagick's
   `compare -metric AE -fuzz 2% committed.png new.png diff.png`, which reports the count of
   differing pixels on standard error. Treat a dimension change as a change: `compare` exits 0 when the images
   match, 1 when they differ and 2 on an error, and differing dimensions are an error, so
   a script under `set -e` either dies on the first changed image or reads a resized one
   as a failed tool. Capture the exit status explicitly, compare the dimensions first
   (`identify -format '%wx%h'`), and fail the job only on a 2 with equal dimensions.
4. Copy over only the images past the threshold, and keep their diff images as job
   artefacts.
5. If anything changed, open or update one pull request on a fixed branch, listing each
   changed image, its diff, and the pages in its `used_by`. A reviewer re-reads those pages
   before merging.
6. If a capture fails because its locator no longer matches, fail the job and name the
   manifest entry. That is the most valuable signal the job produces: the UI the page
   describes no longer exists.

Opening the pull request needs a token that can push a branch and create pull requests;
keep that permission on this one scheduled job, running on the default branch, and never
on a job that runs for pull requests from forks. If the pull request is opened with the
workflow's `GITHUB_TOKEN`, other workflows do not run on it automatically.
