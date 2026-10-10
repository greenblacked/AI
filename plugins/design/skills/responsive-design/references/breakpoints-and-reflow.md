# Breakpoints and reflow

## Contents

- The content-first breakpoint method
- Reflow patterns
- Awkward content
- Target sizing
- The widths to verify

## The content-first breakpoint method

1. Open the layout at 320 px.
2. Widen slowly, a few pixels at a time.
3. Stop at the first width where something looks wrong: a line that wraps to a stray word, a row that overflows, two controls that crowd, a column too narrow to read.
4. That width is the breakpoint. Name it for what broke — "the toolbar wraps" — not "tablet".
5. Repeat above that breakpoint until the layout is stable to the widest size you support.

Most layouts need two or three breakpoints, not five. Each one exists because the content demanded it.

## Reflow patterns

| Content | Small screen | Larger screen |
| --- | --- | --- |
| Navigation | A disclosure or a bottom bar | A horizontal bar |
| Sidebar | Stacked above or below the main content | Beside it |
| Card list | One column | Two, then three |
| Toolbar | Wraps, or an overflow menu | A single row |
| Table | Cards, or a scroll region with a sticky first column | The full grid |
| Form | One column, full-width fields | Two columns where the pairing is meaningful |

The rule at every breakpoint: the arrangement changes, the availability does not.

## Awkward content

- **Tables.** Choose one: cards (one row per card, label-value pairs), a horizontal scroll region with the first column sticky, or a reduced column set with the rest behind a detail view. Never drop a column silently.
- **Toolbars.** Wrap them, or move the secondary actions into an overflow menu. Keep the primary action always visible.
- **Long labels and unbroken strings.** Allow wrapping with `overflow-wrap`, or truncate with a visible full value on focus. An email address or a URL will overflow a narrow column otherwise.
- **Dense charts.** Reduce the tick count, hide the legend behind a tap, or switch to a simpler chart on small screens — the same data, fewer decorations.
- **Modals.** They should fit the viewport, scroll internally, and never trap a control off-screen.

## Target sizing

- Aim for 44 by 44 CSS pixels for any interactive target: the comfortable size and the AAA level of WCAG 2.5.5. The AA minimum, 2.5.8, is 24 by 24 with exceptions, so audit against 24.
- Space adjacent targets so a miss lands on nothing rather than on the neighbour.
- Do not rely on hover for anything on a touch device: no hover-only menus or tooltips that carry required information.
- Give form fields enough height to tap and enough label to read.

## The widths to verify

- 320 px — the narrowest common phone; the WCAG reflow width.
- Around each breakpoint, just below and just above.
- 768 px and 1024 px if your layout has tablet and small-laptop states.
- 1440 px and wider, including a very wide display where a max-width keeps the measure readable.
- At 200 percent zoom, which is a `accessibility-audit` check but often reveals a responsive bug first.
