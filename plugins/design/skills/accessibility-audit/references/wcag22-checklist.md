# WCAG 2.2 manual-pass checklist

Read this during an audit, at steps 3 and 4 of `SKILL.md`. The standard is WCAG 2.2, at <https://www.w3.org/TR/WCAG22/>. WCAG 2.2 was first published on 5 October 2023 and republished on 12 December 2024 with errata; it is still 2.2.

## Contents

- What is new in 2.2
- The manual pass, item by item
- Thresholds worth knowing
- Criteria that look related and are not the target
- Where a number is not given here
- Reporting a finding

## What is new in 2.2

| Criterion | Level | One line |
| --- | --- | --- |
| 2.4.11 Focus Not Obscured (Minimum) | AA | The keyboard-focused element is not hidden by other page content such as a sticky header. Read the criterion for the exact test. |
| 2.5.7 Dragging Movements | AA | Functions that use dragging need an alternative that does not. Read the criterion for the exceptions. |
| 2.5.8 Target Size (Minimum) | AA | Targets are at least 24 by 24 CSS pixels, except where Spacing, Equivalent, Inline, User Agent Control or Essential applies. |
| 3.2.6 Consistent Help | A | Help that repeats across pages stays in a consistent place. |
| 3.3.7 Redundant Entry | A | Do not make users re-enter what they already gave in the same process. Read the criterion for the exceptions. |
| 3.3.8 Accessible Authentication (Minimum) | AA | Signing in must not rely on a cognitive function test without an alternative. Read the criterion for what counts. |
| 2.4.13 Focus Appearance | AAA | A stronger rule for the focus indicator, new in 2.2. Advisory when the target is AA. |

Success criterion 4.1.1 Parsing was obsolete and is removed in 2.2. If a tool still reports it, the tool is out of date, and the finding is dropped rather than rated.

## The manual pass, item by item

Run the items in this order. Record for each one the page or state, what you did, what happened and the criterion.

| Step | How to test | Criterion |
| --- | --- | --- |
| Keyboard end to end | Put the pointer away. Tab, Shift+Tab, Enter, Space and arrow keys through the whole flow. Look for a control you cannot reach, a control you cannot operate, a trap you cannot leave, and an order that jumps. | Look up keyboard operability, no keyboard trap and focus order in the standard and cite the numbers. |
| Focus visible | At every stop, can you see where focus is, in every theme? | 2.4.7 Focus Visible, AA. 2.4.13 is the AAA advisory. |
| Focus not obscured | Tab through with a sticky header, footer, cookie banner or chat widget showing. The focused element must not be entirely hidden. | 2.4.11 Focus Not Obscured (Minimum), AA. |
| 200 percent zoom | Browser zoom to 200 percent at a desktop width. Text still readable, nothing clipped, no overlap, all functions still there. | 1.4.4 Resize Text, AA. |
| 320 px reflow | Viewport 320 CSS px wide (about 1280 px at 400 percent zoom). Vertical-scrolling content has no horizontal scrolling. For content that scrolls horizontally the width in the criterion is a height of 256 CSS px. Check the criterion's exceptions before reporting a table, map or diagram. | 1.4.10 Reflow, AA. |
| Screen reader names | With a screen reader, move through the flow. Every control announces a name that matches its visible label, a role and its state (expanded, selected, invalid). Check that a status change, such as an error appearing or a cart updating, is announced without moving focus. Say which reader and browser. | Look up name, role, value and status messages and cite the numbers. |
| Contrast | Measure text against its background in every theme and state, including hover, focus, disabled-looking and error. Measure control borders and icons that carry meaning. Over images or translucent surfaces, measure against the worst case behind them. | 1.4.3 Contrast (Minimum), AA, and 1.4.11 Non-text Contrast, AA. |
| Target size | Measure the clickable area of each pointer target, not its icon. Mark the ones under 24 by 24 CSS pixels and check the exceptions before reporting. | 2.5.8 Target Size (Minimum), AA. 2.5.5 Target Size (Enhanced), 44 by 44 CSS px, is AAA and advisory. |
| Dragging | For each drag interaction (sliders, sortable lists, maps, file drop), find the pointer or keyboard alternative that does not drag. | 2.5.7 Dragging Movements, AA. |
| Reduced motion | Turn on the system reduced-motion setting, reload, and check that parallax, auto-advancing carousels and large movements stop or tone down. The `prefers-reduced-motion` media query is a technique for honouring this; it is not the wording of any criterion. | 2.3.3 Animation from Interactions, AAA, so advisory at AA. |
| Authentication | Try to sign in and see whether any step depends on memorising or retyping something. Check the criterion's alternatives and exceptions before reporting. | 3.3.8 Accessible Authentication (Minimum), AA. |
| Redundant entry | In a multi-step form, is anything asked twice that the user already gave? Check the criterion's exceptions. | 3.3.7 Redundant Entry, A. |
| Consistent help | On several pages, is the help link or contact in the same relative place? | 3.2.6 Consistent Help, A. |

## Thresholds worth knowing

- 1.4.3 Contrast (Minimum): 4.5:1 for text, 3:1 for large-scale text, which is at least 18 point, or 14 point bold.
- 1.4.11 Non-text Contrast: 3:1 for user interface components and graphical objects needed to understand the content.
- 1.4.10 Reflow: content works at 320 CSS px width for vertical scrolling and 256 CSS px height for horizontal scrolling.
- 1.4.4 Resize Text: text can be resized up to 200 percent without loss of content or function.
- 2.5.8 Target Size (Minimum): 24 by 24 CSS pixels, with the exceptions listed above.

## Criteria that look related and are not the target

- 2.4.13 Focus Appearance (AAA): report as advisory.
- 2.5.5 Target Size (Enhanced), 44 by 44 CSS pixels (AAA): report as advisory. Platform guidance may still ask for 44; that is a usability point for `ui-ux-review`.
- 2.3.3 Animation from Interactions (AAA): the tested behaviour is reduced motion, reported as advisory.

## Where a number is not given here

This checklist names the criteria new in 2.2 and the ones whose thresholds are quoted above. For anything else, including keyboard operability, keyboard traps, focus order, name, role and value, status messages, labels, headings, language and alternative text, open <https://www.w3.org/TR/WCAG22/>, find the criterion and copy its number, title and level into the finding. Do not report from memory: a wrong number sends the fixer to the wrong rule.

## Reporting a finding

```text
[Serious] Menu button has no accessible name
Criterion: look up and copy from the standard, with its title and level
Where: header nav, button.menu-toggle, components/Header.tsx line 42
Found by: screen reader pass (name announced as "button"), axe also flags it
Impact: a screen reader user cannot tell what the button does.
Fix: give it an accessible name that matches the visible label, in the component, so all 6 uses are fixed.
Retest: tab to it with a screen reader and confirm the announced name; rerun axe on the open menu state.
```
