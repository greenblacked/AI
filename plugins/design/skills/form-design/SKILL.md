---
name: form-design
description: "Design or redesign a form people can complete: label every field, order the questions the way the user thinks, validate inline and only after input, put errors next to the field and say how to fix them, and make the primary action obvious and the whole thing keyboard-operable. Use when designing or changing a form. Casual asks include \"design a signup form\", \"how should I validate\", \"where do error messages go\", \"the form asks for too many fields\" or \"should this be one page or many\". Not for diagnosing why an existing screen or form loses people (ui-ux-review), WCAG conformance (accessibility-audit), visual hierarchy (visual-design), a responsive layout (responsive-design), or building the page (website-builder)."
allowed-tools: Read, Grep, Glob
---

# Form design

A form is finished when every field is labelled and justified, the order matches how the user thinks, errors appear next to the field and say how to fix it, and the primary action is reachable by keyboard alone.

Forms lose people for reasons that are almost never the fields themselves. A label that disappears on focus leaves the user unsure what to type. Validation that fires on every keystroke turns a normal entry into a wall of red before the user has finished. An error that says "invalid input" and appears at the top of the page makes the user hunt for what is wrong. A required field marked only after submit wastes the whole form. Each of these is a small decision made in isolation; this skill makes them together, field by field, and keeps the form honest about what it needs and why.

## Scope

Use for: designing a new form; fixing a form with a high abandonment rate; deciding validation timing and where errors go; choosing between one page and several steps; writing labels, hints and error messages; checking that a form is keyboard-operable.

Do not use for: a WCAG conformance audit, which is `accessibility-audit`; the visual hierarchy, type and spacing, which is `visual-design`; a usability review of the surrounding flow, which is `ui-ux-review`; making the form responsive, which is `responsive-design`; building the page, which is `website-builder`.

## Workflow

### 1. Cut the fields

List every field and ask what breaks if it is removed. Most forms ask for more than they use. Every field removed is a completion-rate gain and one less thing to validate, store and protect.

### 2. Order by the user's thinking

Put the fields in the order the person would answer them, which is rarely the order the database stores them. Group related fields and give each group a short heading. Ask for the hard or committing field — a credit card, a phone number — as late as the task allows.

### 3. Label every field

A visible label above the field, always. A placeholder is not a label: it disappears on input and leaves nothing to check against. Add a hint only where the format is not obvious, and put it in the label or just below, not as a placeholder.

### 4. Mark optional, not required

If most fields are required, mark the optional ones. A form of asterisks trains the eye to ignore them. State up front how many steps or how long it takes if it is long.

### 5. Validate at the right time

- On submit for the whole form.
- On blur for a single field, after the user has left it.
- Never on every keystroke, which flags a half-typed email as wrong.
- Re-validate on submit and move focus once: to the error summary if there is one, otherwise to the first field with an error, scrolled into view.

### 6. Put the error next to the field, and say how to fix it

The message sits with the field, in text, not colour alone, and names the fix: "Enter a date in DD/MM/YYYY", not "invalid date". Keep what the user typed so they can correct it. For a form-level failure, summarise at the top with links to each field.

### 7. Make the primary action obvious and the form operable

One primary submit button, labelled with the outcome — "Create account", not "Submit". A secondary cancel. The whole form reachable and completable by keyboard, with a visible focus order that follows the reading order. Hand the reflow to `responsive-design` and the contrast to `accessibility-audit`.

## Anti-patterns

**Placeholder as label.** The field has no label once the user types, so they cannot check what they entered.

**Validation on every keystroke.** Errors appear while the user is still typing, turning a normal form into an obstacle course.

**Error at the top only.** A summary with no field-level message, so the user hunts for the offending field.

**"Invalid input".** A message that names neither the problem nor the fix.

**Clearing on error.** Wiping the field on a failed submit, so the user re-types what was almost right.

**Required not marked until submit.** The user completes the form and only then learns which fields were mandatory.

**"Submit".** A button that names the mechanism rather than the outcome.

## References

- `references/form-patterns.md`: read for the field-cutting questions, the label and hint patterns, the validation timing rules, the error-message format, and the single-page versus multi-step decision.
