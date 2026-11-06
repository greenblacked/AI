---
paths:
  - "**/*.css"
---

# Page CSS floors

Loads when a stylesheet is read or edited. These are the floor rules of the
`distinctive-page-design` lint, the ones where a failure lands on a visitor and not on a
reviewer. That skill holds the full rule table and the lint that checks all of them on a
page.

- Give every interactive element a visible `:focus-visible` style, and draw it with
  `outline` or `box-shadow`. A focus style that changes `border-width` moves the layout
  on every Tab press.
- Answer any animation or transition with a `prefers-reduced-motion: reduce` block that
  removes or shortens it.
- Set body text to at least 16px with a line height of at least 1.3.
- Do not size anything `width: 100vw`. The viewport width includes the scrollbar, so the
  page scrolls sideways; use `100%`. A full-bleed band uses
  `margin-inline: calc(50% - 50vw)` on a container that is itself centred.
- Do not set `overflow: hidden` (or `overflow-x: hidden`) on `html` or `body`. It hides a
  layout fault instead of fixing it.
- Do not start a reveal at `opacity: 0` unless a scripting guard (a class set by the
  script) applies it; without scripting the content stays invisible.
- Keep the reasons for design choices in the decision record, not in comments here; the
  stylesheet ships to every visitor.
