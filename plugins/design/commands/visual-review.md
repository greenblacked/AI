---
description: Review a rendered page from screenshots - pin the render, capture the viewport, theme and reduced-motion matrix, diff against an optional baseline, run the code checks, then have the screenshot-reader subagent read crops - and report measured and unverified findings separately.
argument-hint: '[page URL or path to a built page] [optional baseline: directory of earlier captures, or a second URL or path]'
allowed-tools: Skill, Agent(screenshot-reader), Read, Write, Glob, Grep
disable-model-invocation: true
---

Review the page `$0` from screenshots. If no page was given, stop and ask for one: there
is nothing to render, and a review of whatever happens to be open would be a review of the
wrong thing. The baseline is `$1`; if it is absent, this is a first run, so say that
before anything else. A first run produces captures to review and to keep, and it cannot
report a regression, because there is nothing earlier to regress from.

The procedure is the `visual-review` skill's. Follow it in its order rather than
improvising one here; this command only fixes the two inputs and the order of the report.

Resolve the inputs before capturing anything, because a wrong target wastes the whole
matrix:

- `$0` is a URL if it names a scheme and host, otherwise a path. Check that a path exists
  with `Glob`. A URL that cannot be reached, or a path with nothing to serve, ends the
  review there, with what was tried; do not substitute a different page.
- `$1`, when given, is either a directory of earlier captures or a second page to render
  as the baseline. Read the directory listing and confirm its files are named by matrix
  cell, as the skill names them, since a baseline that cannot be paired with a capture
  produces no comparison. If it is a page, capture it in the same environment as `$0`, not
  a different one; a baseline from another machine makes every cell differ.
- A baseline nobody has looked at is not evidence that the page was right. Say whether
  this one was reviewed, and if that cannot be established, report it as unreviewed.

Then run the skill's steps, holding to the points where a shortened run goes wrong:

1. **Preflight.** Make the render deterministic before the first capture: fixed browser
   image, fonts loaded, animations off, seeded data, dynamic regions masked. A diff on a
   nondeterministic render is noise, and loosening a threshold to quiet it hides the
   regressions the diff exists for.
2. **Capture** at widths 360, 768 and 1280, in light and dark, with reduced motion on,
   plus the skill's one extra cell with reduced motion off. Drop an axis only by decision
   and say so in the report: a page with no dark theme has no dark cell.
3. **Diff** each cell against `$1` and map each differing region to the element under it.
   With no baseline, skip this step and list it under not reviewed.
4. **Code checks before any image is read.** Overflow, contrast, bounding boxes, DOM
   counts and axe-core, on every cell. A failing check is already a verified finding.
5. **Vision pass last, through the `screenshot-reader` subagent.** Hand it native-resolution
   crops cut from the element boxes in step 4, the DOM facts for each, and one narrow
   question per crop. Do not read the screenshots in this context, and do not send it a
   full-page capture and ask what is wrong. What it reports about geometry, counts or
   exact colours is a lead for a code check, not a finding.

Report in two lists that are never merged:

- **Verified**: each item cites the matrix cell, a selector and a bounding box, the value
  measured and the expectation, with a severity and the smallest fix.
- **Unverified**: what an image suggested and no check confirmed, each with the check that
  would confirm it. No severity until it is confirmed.

After those, give the diff regions, then a **Not reviewed** list: masked regions, cells
not captured and why, states not reached, and the baseline if it was absent or unreviewed.
A cell that was skipped is not a cell that passed, and it never goes under "no issues".

Finish with the one finding to fix first and the one cell to look at by eye.
