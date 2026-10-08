# Handoff checklist

## Contents

- Accessibility annotations
- Acceptance criteria patterns
- The handoff pack
- Walking the handoff
- Build review checklist
- Common handoff defects

## Accessibility annotations

State these on the design; they are decisions, not a later audit.

- **Role** of each interactive element (button, link, checkbox, tab, dialog, list).
- **Accessible name** for each: the visible label, or the `aria-label` where none is visible.
- **Focus order** through the screen, and where focus goes on open, close and after a delete.
- **Heading structure:** one `h1`, no skipped levels, headings that describe their section.
- **Contrast** of every text and UI pairing against WCAG AA, using the design-system tokens.
- **Target size** of every control against the platform minimum.
- **Motion:** what animates, and the reduced-motion alternative.
- **Errors:** how each message is associated with its field, and the summary for a failed submit.
- **Zoom:** the screen at 200% and with large text, without loss of content or function.

Where the design cannot meet a requirement, record the decision and its consequence for a user, rather than leaving it to the build.

## Acceptance criteria patterns

Write criteria a tester who did not design it can mark pass or fail. One behaviour each.

```text
State:
  Given <a state or input>,
  When <the user does something>,
  Then <the observable result>.

Extremes:
  Given <the longest/shortest/zero/many case>,
  When <it renders>,
  Then <how it wraps, truncates, scrolls or hides>.

Accessibility:
  Given <a keyboard or assistive-tech user>,
  When <they operate the control>,
  Then <the name, order and announcement they get>.

Responsive:
  Given <a viewport or zoom>,
  When <the screen renders>,
  Then <what reflows, hides or stacks>.
```

Avoid criteria that cannot be tested: "looks good", "feels fast", "matches the mock", "is accessible".

## The handoff pack

- [ ] Annotated designs, in the tool, linked from the written spec
- [ ] State matrix filled for every interactive element
- [ ] Content extremes designed, not defaulted
- [ ] Responsive behaviour per breakpoint, with a drop priority
- [ ] Token and component map, and any token requests listed
- [ ] Accessibility annotations
- [ ] Final copy, not placeholder
- [ ] Acceptance criteria per screen and component
- [ ] Open decisions marked as not-for-the-build-to-make
- [ ] A walkthrough booked with the engineer

## Walking the handoff

Read the spec with the engineer who will build it, screen by screen, and watch for the questions they ask — each one is a gap. Fix the gap in the spec during the walk rather than answering it verbally, because the answer has to outlive the conversation. End with the engineer able to state the states, the breakpoints and the criteria back.

## Build review checklist

Compare the build to the spec, not to memory.

- [ ] Every state from the matrix, not just the default
- [ ] The empty, loading and error states
- [ ] The shortest and longest content, and zero and many
- [ ] Each breakpoint, including the smallest supported and 200% zoom
- [ ] Tokens used, no raw values that drifted
- [ ] Focus order, accessible names and headings
- [ ] Contrast of each pairing in the built theme
- [ ] Every acceptance criterion, marked pass or fail

File each difference as a defect against a criterion, or as a spec gap. Update the spec when the gap was real, so the next screen does not repeat it.

## Common handoff defects

- **The invisible state.** Empty, loading or error left undecided, so the engineer invents it.
- **The unhandled extreme.** A long name truncates with no design for the full value.
- **The single breakpoint.** Only one width specified, so the reflow is invented.
- **The raw value.** A hex or a magic number instead of a token, which drifts the system.
- **The untestable criterion.** "Matches the mock" cannot be marked pass or fail.
- **The deferred audit.** Accessibility left to a later pass, to be retrofitted into a built screen.
- **The verbal answer.** A question answered in the walk but never written into the spec.
- **The abandoned handoff.** No review after the first screen, so the build diverges silently.
