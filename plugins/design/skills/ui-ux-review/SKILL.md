---
name: ui-ux-review
description: "Review one screen or flow (a live URL, screenshot, Figma frame or its code) against usability heuristics and platform guidance, and return ranked findings that each carry the evidence, the consequence for a user and the smallest fix. Walks the primary task path and every state before any polish, and rates severity 0 to 4 rather than taste. Use for UX feedback on a screen, flow or mockup. Casual asks include \"what's wrong with this screen\", \"does this flow make sense\", \"why do people drop off here\", \"review my UI\", \"is this form confusing\", \"give me UX feedback\" or a mockup shared for critique. Not for a WCAG conformance audit (accessibility-audit), tokens or theming (design-system), a test with real participants (usability-test-plan), designing or changing a form (form-design), or building or auditing a whole site (website-builder)."
allowed-tools: "Read, Grep, Glob, Bash(npx:*)"
---

# UI and UX Review

A review is finished when each finding says what is wrong, where it is, what it costs a user and the smallest change that removes the cost, and when the ones on the primary task path come first.

The job fails in three reliable ways. The reviewer opens with what is visible and cheap to say, such as spacing, radius and colour, and runs out of attention before reaching the form that loses people. The reviewer reports taste ("the radius should be 8px") that nobody can verify or disagree with usefully, so the author argues about preference and the real problems wait. And the reviewer looks at each screen in its resting state only, so the empty list, the failed submit and the disabled button that never explains itself are never seen. This skill fixes the order, demands evidence and a consequence for every finding, and forces the walk through the states.

## Scope

Use for: reviewing one screen or one flow, in any form the user can show you, for usability problems; a second opinion before a design ships; checking a build against its mock; finding why a flow loses people when the cause is not yet known.

Do not use for: a conformance audit against WCAG, which is `accessibility-audit`; defining tokens, themes or component state rules, which is `design-system`; finding out what real people do, which is `usability-test-plan`; a whole-site audit across performance, security, SEO and code health, or building and redesigning a site, which is `website-builder`; reviewing the code of a change, which is `code-review`.

## Workflow

### 1. Fix the user and the task

Write one sentence naming who is using this screen and what they are trying to finish, and one naming what success looks like. If the user cannot say, state your assumption at the top of the review and keep it visible. Findings are consequences for that person doing that task, so without the sentence there is nothing to rank against.

### 2. Capture evidence before opinions

Collect what you will cite: a screenshot at 360 px wide and one at 1440 px wide for a web page, the Figma frame name for a mock, the file and line for code, and the exact selector or component for each element you will talk about. A finding with no locator cannot be fixed or disputed. For a live URL a screenshot tool is enough, and this one is already likely to be installed:

```bash
npx playwright screenshot --viewport-size=360,800 --full-page https://example.com/path narrow.png
npx playwright screenshot --viewport-size=1440,900 --full-page https://example.com/path wide.png
```

If a page or flow sits behind a login or cannot be reached, say which parts you could not see rather than reviewing around them.

### 3. Walk the primary task path first

Go from entry to done as the person in step 1 would, counting the steps, the decisions and the places where they must remember something from an earlier screen. Record findings on that path before looking at anything off it. A secondary page with a misaligned icon does not belong in the same list as a checkout that drops the cart on a back button.

### 4. Walk every state of every control on the path

For each interactive element, check hover, focus, pressed, disabled, loading, empty and error, plus success where the control submits something. Use the matrix in `references/heuristics.md`. These are where most real defects sit, because mocks show the resting state and the happy data. A disabled button with no reason, a spinner with no end, an empty list that looks broken and an error that names a code instead of a fix are all findings.

### 5. Test against the heuristics and the platform

Read `references/heuristics.md` for Nielsen's ten heuristics with what each looks like on a screen, and for the platform sizes and conventions. Name the heuristic each finding violates by number. Check native conventions for the platform the screen ships on: a control smaller than the platform's default size, or a pattern that works unlike every other app on that platform, is a finding when it costs the user something on the task path.

### 6. Write each finding in one shape

Every finding has five parts: the problem, the evidence, the consequence for the user, the smallest fix and a severity from 0 to 4.

```text
[3] Primary action is disabled with no explanation (heuristic 1, 9)
Evidence: checkout.png (360 px), button.pay in the Payment frame, state: disabled.
Consequence: a user with a valid card cannot tell which field is blocking Pay and abandons.
Fix: keep the button enabled, validate on press, and focus the first invalid field with its message.
```

Severity combines how often the problem is met, how much it hurts when met and whether users can get past it once they know. The scale and its calibration are in `references/heuristics.md`.

If you cannot write the consequence, you do not have a finding, you have a preference. Drop it, or list it once under "observations, not findings" with no severity, and keep that list short.

### 7. Rank and hand over

Order by severity, then by position on the primary task path. Lead with anything rated 3 or 4 and say plainly when there is none. State what you did not review: states you could not reach, viewports you did not capture, flows you were not shown. Close with what this review cannot settle, which is what real users do. Say that a test with five participants answers it, and name `usability-test-plan`. Do not pad the list to look thorough, because a long list of 1s hides the one 4.

## Anti-patterns

**Reporting taste as a finding.** "Use 8px radius" has no consequence and invites a preference argument. Report the consequence of the inconsistency ("two button radii on one screen make the secondary action look disabled") or leave it out.

**Reviewing the screenshot and not the states.** The resting state is the one that was designed. The others are the ones users meet when something goes wrong.

**A review with no severity.** The author fixes the easiest ten findings and ships the one catastrophe.

**Copying every heuristic into a finding.** Ten heuristics are a lens, not a template. A finding names the heuristic that explains it and no more.

**Calling it validated.** An expert review finds likely problems. Only people using it finds out which ones matter.

## References

- `references/heuristics.md`: read at step 4 for the state matrix, and at steps 5 and 6 for the ten heuristics with what each looks like on a screen, the severity scale and the platform control sizes.
