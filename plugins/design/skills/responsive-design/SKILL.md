---
name: responsive-design
description: "Design a layout that works across screen sizes: choose breakpoints from where the content breaks rather than from device names, decide what reflows, wraps or hides at each, and keep the primary task reachable and the touch targets large on the smallest screen. Use for any \"does this work on mobile\" or responsive layout question. Casual asks include \"it breaks on mobile\", \"what breakpoints should we use\", \"the table overflows on a phone\", \"make this responsive\", \"does this work at 320px\" or \"the nav does not fit small screens\". Not for a WCAG reflow audit (accessibility-audit), the visual hierarchy itself (visual-design), a usability review (ui-ux-review), a form's design (form-design), or writing the CSS (code-scaffold)."
allowed-tools: Read, Grep, Glob
---

# Responsive design

A responsive layout is finished when every screen size from 320 px up can complete the primary task, the breakpoints sit where the content actually breaks, and nothing is hidden on a small screen that the task needs.

Responsive design fails in two ways. The first is breakpoints copied from device names — "mobile is 375, tablet is 768" — which fit the phones of one year and break the moment a foldable or a large phone appears. The second is hiding content on small screens to make it fit: a nav collapsed with no replacement, a table that drops columns the user needed, a desktop-only action. Both come from designing the large screen and then shrinking it. The fix is to design the smallest screen first, let the content decide where it needs more room, and only ever change the arrangement, never the availability.

## Scope

Use for: making a layout work from 320 px to a large display; choosing breakpoints; deciding what reflows, wraps, collapses or becomes a scroll region; making touch targets large enough; checking that the primary task survives on a phone.

Do not use for: a WCAG reflow and zoom audit, which is `accessibility-audit`; the visual hierarchy, type and spacing themselves, which is `visual-design`; a usability review of a flow, which is `ui-ux-review`; a form's design, which is `form-design`; writing the CSS and media queries, which is `code-scaffold`.

## Workflow

### 1. Start at 320 px

Design the smallest width first, with the primary task in front of you. If the task cannot be completed at 320 px, that is a design problem to solve now, not a reason to hide it later.

### 2. Let the content set the breakpoints

Resize the window slowly and watch for the first moment something breaks — a line that wraps badly, a row that overflows, a target that crowds its neighbour. That width is the breakpoint. Name it by what breaks, not by a device.

### 3. Change arrangement, not availability

At each breakpoint, decide the reflow: stack, wrap, collapse into a disclosure, or become a horizontal scroll region. What does not change is whether the content exists. Hiding a needed control is not a responsive design.

### 4. Handle the awkward content

Tables, toolbars, long labels and dense charts are where responsive design is won or lost. A table becomes cards, a scroll region with a sticky first column, or a smaller column set — but the data stays reachable. Decide which, per case.

### 5. Size the targets for a thumb

Aim for touch targets of 44 by 44 CSS pixels, with enough spacing that a miss does not hit the neighbour. That is the comfortable size and WCAG's AAA target (2.5.5); the AA minimum is 24 by 24 with exceptions (2.5.8), so a 24 px control can conform and should not be reported as a failure. Design to 44 and audit against 24.

### 6. Verify across the range

Check at 320, around each breakpoint, and wide. Check zoom and text enlargement too, or hand that to `accessibility-audit`. A layout that holds at 320 and 1440 but breaks at 600 is not done.

## Anti-patterns

**Device-name breakpoints.** "Mobile, tablet, desktop" chosen from a device list rather than from where the content breaks, which dates immediately.

**Hiding on mobile.** Dropping a nav, a column or an action to make the small screen fit, leaving the primary task unreachable.

**The horizontal scroll.** A page that scrolls sideways on a phone because one fixed-width element or a long unbroken string overflows.

**Shrinking the desktop.** Designing wide and scaling down, so the small screen is a cramped copy rather than a considered layout.

**Tiny targets.** Links and buttons well under 44 px, or under the 24 px AA minimum, or two controls with no gap, so thumbs miss and hit the wrong one.

**Only testing one width.** Checking a phone and a laptop and assuming everything between and beyond is fine.

## References

- `references/breakpoints-and-reflow.md`: read for the content-first breakpoint method, the reflow patterns for tables, toolbars and dense content, target sizing, and the widths to verify.
