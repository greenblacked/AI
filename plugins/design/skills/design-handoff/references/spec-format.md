# Spec format

## Contents

- What a spec contains
- The state matrix
- Content extremes
- Responsive notes
- Token and component map
- Worked example: a list screen
- Worked example: a form

## What a spec contains

A spec is the design plus everything the mock omitted. Keep it in the same tool as the design where possible, so the annotation sits on the frame it describes, and export the written parts — states, criteria, tokens — somewhere the engineer can read without the design tool.

- The design, annotated in place.
- The state matrix for every interactive element.
- The content extremes.
- The responsive behaviour per breakpoint.
- The token and component map.
- The accessibility annotations.
- The copy, final, not placeholder.
- The acceptance criteria.

## The state matrix

One row per element, one column per state. Blank is not "not applicable" — mark it N/A or fill it.

| Element | Default | Hover | Focus | Active | Disabled | Loading | Empty | Error | Success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Primary button | | | | | | | N/A | | |
| Email field | | | | N/A | | N/A | N/A | | |
| Results list | | N/A | N/A | N/A | N/A | | | | N/A |

For each filled cell, the design shows the state, or the spec says what changes (colour, label, icon, motion) and names the tokens.

## Content extremes

- **Text:** shortest and longest realistic value per slot, at the narrowest width.
- **Counts:** zero, one, two, many, and more than fits.
- **Missing:** optional fields absent, avatar absent, image failed.
- **Large:** a very long name, a large number, a long list.
- **Translated:** the string at its longest translation, and right-to-left if it ships.
- **Zoom and large text:** 200% zoom and the platform's large-text setting.

Say what each does: wraps, truncates, scrolls, hides, or shows a fallback.

## Responsive notes

For each breakpoint named by the design system:

```text
360–599   single column; nav behind a menu button; secondary actions in an overflow menu
600–1023  two columns; sidebar becomes a top bar; table shows 3 of 6 columns
1024+     full layout; sticky sidebar; full table
```

State the priority order for anything that must drop: what goes first, second, last. Decide the reflow rather than leaving the default.

## Token and component map

| Element | Component | Tokens |
| --- | --- | --- |
| Primary action | Button / primary | color-action-default, radius-md, space-3, type-body-strong |
| Card | Card | color-surface, shadow-sm, radius-lg, space-4 |
| Error text | Text / danger | color-danger-text, type-caption |

- Every raw value is either a token or a token request. List the requests.
- New components are called out with their variants and states, so they are built as components rather than one-offs.

## Worked example: a list screen

```text
Screen: Invoices list
States:
  Loading   three skeleton rows matching the row height; no spinner
  Empty     "No invoices yet. Create one to get started." + primary action; no table
  Error     "We could not load your invoices." + Retry; no table
  Partial   rows render as they arrive; a "Loading more" row at the end
Content extremes:
  Zero rows, 1 row, 500 rows (paginate at 50)
  A description 3x the column width -> one line, ellipsis, full value on focus
Responsive:
  360   one column: amount, status, date; description hidden
  1024  full table: description, amount, status, date, actions
Tokens:
  Row -> TableRow -> color-surface, border-subtle, space-3
Accessibility:
  Table role with a caption; each row a link with the invoice number as its name
  Sort buttons expose aria-sort; empty state heading is the page's h2
Acceptance:
  Given no invoices, when Billing opens, then the empty state shows and no table renders.
  Given 500 invoices, when the list loads, then 50 render and a Load more control appears.
```

## Worked example: a form

```text
Screen: Add payment method
States:
  Default   fields empty; submit disabled with a reason, or enabled and validating on submit
  Focus     visible focus ring on every field, token color-focus
  Error     message under the field, associated with it; input not cleared
  Submitting button shows a spinner and a "Adding…" label; fields read-only
  Success   inline confirmation repeating the button's verb; what happens next
Content extremes:
  Longest cardholder name; a postal code from a country with letters; missing apartment line
Responsive:
  360   one column, numeric keyboards for numeric fields
  1024  two columns, card type beside the number
Tokens:
  Field -> Input -> color-border, radius-md, space-2, type-body
Accessibility:
  Each input labelled; errors via aria-describedby; error summary at the top for submit failures
Acceptance:
  Given an invalid expiry, when submit is pressed, then the field shows the fix and keeps the value.
```
