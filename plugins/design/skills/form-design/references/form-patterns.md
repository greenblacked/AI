# Form patterns

## Contents

- Cutting fields
- Labels, hints and grouping
- Validation timing
- Error messages
- One page or several steps
- Keyboard and completion

## Cutting fields

For each field, ask:

- What breaks if this is removed?
- Do we already have this, or can we derive it?
- Is this asked at the right moment, or could it be collected later?
- Is it required, or just nice to have?

A field that survives none of these is cut. A field that can be collected later is deferred. The shortest form that completes the task converts best and has the least to protect.

## Labels, hints and grouping

- **Label above the field**, always visible, associated programmatically. Placeholder text is a hint, never a label.
- **Hint below the label** for format that is not obvious: "DD/MM/YYYY", "at least 10 characters". Do not put the hint only in the placeholder.
- **Group** related fields under a short heading — "Contact", "Payment", "Delivery" — so a long form reads as a few short ones.
- **Field width** should hint at the expected length: a short field for a postcode, a wide one for an address line.
- **Autocomplete** attributes so the browser can fill known values; this alone removes a large share of typing on mobile.

## Validation timing

| Trigger | Use for | Never |
| --- | --- | --- |
| On submit | The whole form | — |
| On blur | One field, after the user leaves it | Flagging before they finish |
| On every keystroke | Nothing | A half-typed value reads as wrong |
| On paste | Nothing special; let blur handle it | — |

On a failed submit, focus the first field with an error and scroll it into view. Re-run the whole validation each submit.

## Error messages

- Next to the field, in text, associated with it — not colour alone, not only at the top.
- Name the fix: "Enter a date in DD/MM/YYYY", "This email is already registered — sign in instead".
- Keep what the user typed so they can correct it.
- For a whole-form failure, add a summary at the top with links to each field, and put focus on the summary.
- Do not shout: one message per field, and no exclamation marks.

## One page or several steps

- **One page** when the form is short or the fields are related, so the user sees the whole ask and can complete it in one pass.
- **Several steps** when the form is long, or the steps are genuinely distinct (identity, payment, confirmation), so each screen has one job.
- For multi-step, show progress ("Step 2 of 3"), allow going back without losing data, and do not make the user re-enter anything.
- Never split a form into steps only to hide its length.

## Keyboard and completion

- Tab order follows the reading order; no positive `tabindex` games.
- Visible focus on every field and button.
- Enter submits from a text field; a multiline field does not.
- Do not rely on a mouse for anything required — date pickers, selects and file inputs all need a keyboard path.
- Save progress for a long form, or warn before losing it.
