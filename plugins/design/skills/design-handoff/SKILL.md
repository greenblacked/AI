---
name: design-handoff
description: "Produce the spec that takes a design from approved to built: the states and edge cases, responsive and content extremes, the token and component mapping, accessibility annotations, and acceptance criteria an engineer can check against. Covers redlines, the handoff pack, and a review that catches what the mock left out. Use this skill whenever someone is handing a design to engineering. Triggers include writing a design spec, redlining, annotating a Figma file for build, preparing a handoff, writing acceptance criteria from a design, or a build that does not match the mock — including phrasings like \"the dev didn't build it right\", \"what do I need to give the engineers\", or \"spec this screen for build\". Do not use it for defining tokens or component rules (design-system), writing the code (code-scaffold), building a site (website-builder), or the words in the interface (content-design)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Design Handoff

A handoff is finished when an engineer can build the screen without asking what happens in the empty, loading, error, long-content and small-screen cases, when the design names the tokens and components it uses, and when the build can be checked against criteria that were written down before it started.

The mock is a picture of one state with ideal data. The build is every state with real data on every screen size, and the gap between them is where handoff fails. The engineer fills the empty state with a guess, the error with a default, and the long name with a truncation nobody designed, and the designer sees the result and says it is wrong without having said what right was. The other failure is the spec that only redraws the mock — spacing and colour at one width — so the parts that were actually decided stay in the designer's head, and the parts that were never decided get invented at build time. This skill enumerates what the mock omits, maps the design to the system, writes criteria, and stays for the build review.

## Scope

Use for: turning an approved design into a buildable spec — a screen, a component or a flow; states and edge cases; responsive behaviour; content extremes; token and component mapping; accessibility annotations; acceptance criteria; a redline or annotated handoff; reviewing a build against the spec; the handoff pack a designer gives engineering.

Do not use for: defining the tokens, themes or component state rules themselves, which is `design-system`; writing the front-end code, which is `code-scaffold`; building or redesigning a whole site, which is `website-builder`; the words in the interface, which is `content-design`; a usability review of a screen, which is `ui-ux-review`; or a WCAG audit, which is `accessibility-audit`.

## Workflow

### 1. Confirm the design is decided

Handoff starts when the design is approved, not while it is still moving. List any open question — a layout, a behaviour, a piece of copy — and either resolve it or mark it as a decision the build must not make. A spec with open questions in it produces a build with invented answers.

### 2. Enumerate every state

The mock shows one. Write the others for each element and each screen: default, hover, focus, active, disabled, loading, empty, error, success, partial data, and first-run versus returning. Use the state matrix in `references/handoff-checklist.md`. The states are most of the spec, because they are most of what the mock leaves out.

### 3. Push the content to its extremes

- Shortest and longest realistic string in every text slot, with the real data.
- Zero, one, many and too many to count for every list and counter.
- Missing optional data, and a value that is present but very large.
- Translated strings, which run longer than English, and right-to-left layout if it ships.
- An image that fails to load, and a user avatar that does not exist.

Design the wrapping, truncation and overflow for each, rather than leaving the default.

### 4. Define responsive behaviour

For each breakpoint in the system, say what reflows, what hides, what stacks, and what the priority order is when something must go. Name the breakpoints from the design system rather than inventing new ones. Check the smallest supported width and the largest, and the zoomed and large-text cases. A spec that only covers one width has not decided the responsive design; the engineer will.

### 5. Map to tokens and components

Every colour, space, radius, shadow, type style and duration names a token from `design-system`, not a raw value. Every element either uses an existing component or is called out as new, with its variants and states. Raw hex values and magic numbers in a spec are how a system drifts; if a value is missing, that is a token request, not a one-off.

### 6. Annotate accessibility

State the semantic role of each interactive element, its accessible name, the focus order, where focus goes on open and close, the heading structure, the contrast of each text and UI pairing, and the target sizes. These are design decisions, not a later audit. Where the design cannot meet a requirement, record the decision and its consequence rather than leaving it to the build.

### 7. Write acceptance criteria

Each criterion is checkable by someone who did not design it: a state, an input, an expected result. Write them per screen and per component, and cover the states from step 2 and the extremes from step 3. A criterion a tester cannot mark pass or fail is not one.

```text
Given no invoices,
When the user opens Billing,
Then the empty state shows the heading, the one-line explanation and the "Create invoice" button,
And no table or pagination is rendered.

Given an invoice description longer than the column,
When the list renders at 360px,
Then the text truncates to one line with an ellipsis and the full value is available on focus.
```

### 8. Assemble and walk the pack

Collect the annotated designs, the state and edge-case set, the responsive notes, the token and component map, the accessibility annotations, the copy, and the acceptance criteria. Walk it with the engineer who will build it, and fix what they cannot follow. The measure of the pack is the questions it prevents, not its completeness.

### 9. Review the build against the spec

Compare the built screen to the spec state by state, at each breakpoint, with the long and short content. File each difference as a defect against a criterion or as a spec gap, and update the spec when the gap was real. Handoff does not end at the first commit.

## Output format

```markdown
## Screen or component
[What it is, and the design it came from.]

## States
[A row per element: default, hover, focus, active, disabled, loading, empty, error, success.]

## Content extremes
[Shortest, longest, zero, many, missing, translated.]

## Responsive
[Per breakpoint: what reflows, hides, stacks, and the priority order.]

## Tokens and components
[Element -> component -> tokens. New components called out.]

## Accessibility
[Role, accessible name, focus order, headings, contrast, target sizes.]

## Acceptance criteria
[Given/When/Then, one per checkable behaviour.]

## Open decisions
[What the build must not decide on its own.]
```

## Anti-patterns

**Specifying the mock.** Redrawing the resting state with ideal data and calling it a handoff. The states and the extremes are the spec.

**Raw values instead of tokens.** Hex colours and magic pixel numbers that drift from the system. Name a token, or file a token request.

**One width.** A spec that covers a single breakpoint leaves the responsive design to the engineer. Decide the reflow.

**Accessibility as a later pass.** Roles, names, focus order and contrast are design decisions; deferring them means retrofitting them into a built screen.

**Acceptance criteria nobody can test.** "Looks good", "feels fast", "matches the mock" cannot be marked pass or fail. Write the state, the input and the expected result.

**The silent handoff.** A pack dropped in a tool with no walkthrough, so the engineer guesses and the designer finds out at review. Walk it.

**Ending at the first commit.** The build diverges after the first screen. Review the states and breakpoints as they land.

## References

- `references/spec-format.md`: read at steps 2, 3, 4 and 5 for how to lay out a spec — the state matrix, the content-extremes set, responsive notes, the token and component map, and worked examples.
- `references/handoff-checklist.md`: read at steps 6, 7, 8 and 9 for the accessibility annotations, the acceptance-criteria patterns, the handoff pack contents and the build-review checklist.
