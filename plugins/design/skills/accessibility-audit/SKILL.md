---
name: accessibility-audit
description: "Audit a page, flow or component against WCAG 2.2 Level AA: run the automated tools first because they are cheap, then the manual pass that automation cannot do (keyboard end to end, focus visible and not obscured, 200 percent zoom, 320 px reflow, screen reader names, reduced motion, target size), and report each finding with its success criterion number, level, severity and fix. Use for any \"is this accessible\" or WCAG 2.2 AA question. Casual asks include \"audit this for WCAG\", \"can a keyboard user get through checkout\", \"axe says it's clean, are we done\", \"screen reader users can't get past the nav\" or \"will this pass an accessibility review\". Not for a whole-site audit across performance, security and SEO, or for building a site (website-builder), writing role-based test locators (e2e-testing), a general usability review (ui-ux-review) or tokens and themes (design-system)."
allowed-tools: "Read, Grep, Glob, Bash(npx:*)"
---

# Accessibility Audit

An audit is finished when every failure found carries the success criterion it breaks, the level of that criterion, a severity and a fix at the right place, and when the report says what was tested and what was not.

Automated tools find only part of the problems. Passing them is a floor, not a verdict, and "axe is clean" is never "accessible": no tool can tell whether a focus order makes sense, whether a label means what it says, or whether a flow can be finished without a mouse. The common failure is to run the scanner on the landing page, report the count and stop, which leaves every dialog, menu, error state and form unexamined. This skill puts the scanner first because it is cheap, then makes the manual pass non-optional and fixes its order.

## Scope

Use for: auditing a page, a flow or a component against WCAG 2.2 Level AA; checking whether a fix worked; finding out what to fix first on a page that already fails; turning "axe is clean" into an honest statement of what was and was not tested.

Do not use for: auditing a whole site across performance, security, SEO and code health, or building one, which is `website-builder`; writing browser tests that locate elements by role, which is `e2e-testing`; a general usability review, which is `ui-ux-review`; defining tokens and component states so contrast holds in every theme, which is `design-system`; reviewing a diff, which is `code-review`.

## Workflow

### 1. Scope the sample and pin the target

State the target (WCAG 2.2 Level AA), what is in scope (the pages, the flow from start to finish, or the one component) and the build under test, by URL and commit or version. List the states to reach, because audits fail on states and not on first load: menus open, dialogs, validation errors, loading, empty, each theme. Audit a flow end to end rather than its first page.

### 2. Run the automated pass

Run at least two engines and run each on every state in the sample, not only on load. Axe is the usual first choice, and pa11y or Lighthouse's accessibility category gives a second opinion.

```bash
npx @axe-core/cli https://example.com/checkout --tags wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa
npx pa11y --runner axe --runner htmlcs https://example.com/checkout
npx lighthouse https://example.com/checkout --only-categories=accessibility --output=json --output-path=./a11y.json
```

Confirm from the tool's own help or documentation that the ruleset you selected includes WCAG 2.2 rules. A tag the installed version does not know can be ignored silently and you will have tested less than you think. Record the tool versions. Treat the result as a list of leads, not a score; each violation still needs the element and the fix.

### 3. Run the manual pass, in this order

Work through `references/wcag22-checklist.md`, which gives the procedure and the criterion for each item. The order matters: keyboard first, because a failure there makes the rest unreachable.

1. Keyboard end to end: complete the flow with no pointer. Check for traps, order and every control reachable and operable.
2. Focus visible (2.4.7) at every step, and not obscured by a sticky header, banner or cookie bar (2.4.11).
3. Zoom to 200 percent (1.4.4) and reflow at 320 CSS px wide (1.4.10): nothing lost, nothing needing two-dimensional scrolling.
4. Screen reader: every control has an accessible name, role and state; dynamic changes are announced; headings and landmarks give a usable outline. Use at least one real screen reader and say which.
5. Contrast of text (1.4.3) and of controls and graphics (1.4.11), in every theme and state, not only the default.
6. Target size (2.5.8) and dragging alternatives (2.5.7).
7. Motion: with the system's reduced motion setting on, non-essential animation stops or reduces. The relevant criterion is 2.3.3 at Level AAA; the setting is how you test it.
8. Authentication (3.3.8), redundant entry (3.3.7) and consistent help (3.2.6) where the flow has sign-in, repeated forms or a help mechanism.

### 4. Map each finding to a criterion

Name the success criterion number, its title and its level. Look the number up in <https://www.w3.org/TR/WCAG22/> rather than citing from memory. A finding at Level AAA is reported as advisory, since the target is AA. Do not cite 4.1.1 Parsing: it is obsolete and was removed in 2.2, so an old tool that still reports it is out of date.

### 5. Rate severity and place the fix

Rate by what the user loses, not by how the tool labels it.

| Severity | Meaning |
| --- | --- |
| Blocker | A user of a keyboard or assistive technology cannot complete the task. |
| Serious | The task can be completed only with a workaround or guesswork. |
| Moderate | The task is completable but slower or more confusing. |
| Minor | A real failure with little effect on the task. |

Place the fix at the component, token or template that causes it and list every instance it covers, because fixing one button and leaving forty is not a fix. Quote the element, a selector or the file and line.

### 6. Report what was and was not tested

Lead with blockers. State the sample, the engines and versions, the browsers and screen reader combinations used, and the states not reached. Use the wording "no failures found in the tested sample" rather than "conforms" or "accessible" unless a full-site, full-criteria evaluation was actually done, which this skill does not do. Close with the retest that confirms each fix.

## Anti-patterns

**Reporting the scanner's count.** A clean run on the landing page says nothing about the checkout dialog.

**Citing a criterion from memory.** A wrong number or level sends the fixer to the wrong rule. Look it up.

**Auditing only the default theme.** Contrast and focus appearance fail in dark mode and in the error state, which a scan of the default misses.

**Fixing instances.** A mislabelled icon button repeated across a component library is one defect in one place.

**Claiming conformance from a sample.** A page audit supports a statement about that page.

## References

- `references/wcag22-checklist.md`: read at step 3 for the manual-pass procedure, and at step 4 for the criterion numbers, levels and thresholds, including what is new in WCAG 2.2.
