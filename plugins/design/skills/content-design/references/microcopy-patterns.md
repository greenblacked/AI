# Microcopy patterns

## Contents

- Buttons and actions
- Links
- Field labels and help text
- Error and validation messages
- Empty states
- Loading states
- Success and confirmation
- Notifications
- Destructive actions
- Numbers, dates and plurals

## Buttons and actions

Name the outcome in the user's verb. The button and the confirmation that follows use the same word, so the user knows the two are the same act.

| Context | Avoid | Use |
| --- | --- | --- |
| Create | Submit, Save | Create account, Save changes |
| Confirm | OK, Yes | Delete project, Send invite |
| Cancel | No, Back | Keep editing, Discard |
| Navigate | Click here | View invoice |

- Sentence case, no full stop unless it is a sentence.
- One primary action per screen. If two are equally weighted, the screen has no primary action.
- A disabled primary action needs a reason nearby, or it should stay enabled and validate on press.

## Links

A link is read out of context — by a screen reader, in a list, in search. It must name its destination on its own.

- Avoid: "click here", "read more", "learn more", "this page".
- Use: "How refunds work", "Download the Q3 report", "Manage notification settings".
- Link text is part of the copy; it is not a place to hide a keyword.

## Field labels and help text

- Every field has a visible label. A placeholder is not a label: it disappears on focus and is read inconsistently.
- The label names the value, not the format: "Date of birth", not "DD/MM/YYYY". Put the format in help text.
- Help text sits before the field when the user needs it to answer, and is short enough to read in one glance.
- Mark optional fields, not required ones, when most fields are required; do the reverse when most are optional. Be consistent across the form.
- Never ask for a value the system already knows or can infer.

## Error and validation messages

Three jobs: what happened, why, what to do. One line if possible.

```text
Field:    Enter a date in the past.
Format:   Enter a phone number like 555 0100.
Server:   We could not save your changes. Check your connection and try again.
Permission: You need an admin role to invite people. Ask an admin or your workspace owner.
Payment:  Your card was declined. Check the billing address and try again.
```

- Put the message next to the field, associated with it for assistive tech.
- Lead with the problem, not the word "Error".
- No codes as the message. If a support reference is needed, add it after the human sentence, small.
- Never say "You entered an invalid value". Say what is valid.
- Do not clear the user's input on error.

## Empty states

An empty state is a screen, not a gap. Say why it is empty and the one action that fills it.

- **First run:** "No projects yet. Create your first project to start." + primary action.
- **Filtered:** "No invoices match these filters. Clear filters or try a wider date range." + clear action.
- **Error-emptied:** "We could not load your files. Refresh to try again." + retry.
- **Cleared:** "Inbox zero. Nothing needs you right now." — say when empty is good.

Never ship "No data", "Nothing here" or a bare illustration.

## Loading states

- Under about a second, no copy is needed.
- Longer, say what is happening: "Loading your dashboard…", "Saving…", "Checking availability…".
- Past a few seconds, give a sense of progress or a way out, and never let a spinner run with no end.
- A skeleton screen replaces the layout it is loading, not a spinner in the middle of it.

## Success and confirmation

- Repeat the button's verb: the user pressed "Place order", so the message says "Order placed".
- Say what happens next if anything does: "Order placed. We will email a receipt."
- For an irreversible action, confirmation is a screen; for a reversible one, a toast with undo is enough.

## Notifications

- A notification says the thing that happened and, if it needs the user, the action.
- Lead with the subject, not the product: "Payment failed", not "Acme update".
- One notification per event. Do not stack three toasts for one save.
- Respect the channel: an email can carry more than a toast.

## Destructive actions

- Name what is destroyed and how much: "Delete 3 files", not "Delete".
- Offer undo for anything reversible; require typed confirmation only for the irreversible and the large.
- Do not use a destructive colour as the only signal. The verb carries the meaning.

## Numbers, dates and plurals

- Use the user's locale and the format their device expects.
- Write counts as words in prose and digits in data: "three files" vs "3 files".
- Handle plural, zero and gender forms explicitly. "1 item", "2 items", "No items" are three strings, not one with an "s".
- Avoid relative dates for anything a user will read later: "Due 3 March", not "Due in 2 days".
- Do not abbreviate units or months a machine will translate.
