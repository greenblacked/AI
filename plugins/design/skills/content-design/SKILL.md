---
name: content-design
description: "Write and review the words in an interface — button and link labels, error and empty-state messages, confirmation and loading copy, and the tone that holds across a flow. Covers plain language, the action named in the label, error messages that say what happened and what to do, and a voice that stays consistent while the tone shifts by moment. Use this skill whenever someone is writing or reviewing UI copy. Triggers include writing microcopy, fixing a confusing label or an unhelpful error, naming a button, rewriting an empty state, setting a tone of voice, or a UX writing pass over a flow — including phrasings like \"the button just says Submit\", \"our error messages are useless\", or \"how should we word this\". Do not use it for product documentation and guides (technical-docs), a whole-screen usability review (ui-ux-review), a WCAG audit (accessibility-audit), or marketing and brand copy."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Content Design

Interface copy is finished when every label names the action the user is taking, every error says what happened and what to do next, every empty state says how to fill it, and the whole flow sounds like one writer who knows what the user is trying to do.

The job is hard because the words are written last, by whoever has the screen open, with no time and no owner. So the button says "Submit" because that is the word in the code, the error says "Error 422" because that is what the API returned, and the empty state says "No data" because nobody imagined a user meeting it on day one. Each of those is invisible to the person who wrote it and obvious to the person stuck at it. Copy is also where blame leaks in: "You entered an invalid date" tells the user they are wrong when the field accepted what they typed, and the tone that works for a success message reads as flippant on a payment failure. This skill fixes the unit of work — one string, at one moment, doing one job — and the pass that makes a flow read as a whole.

## Scope

Use for: writing or rewriting any string a user reads in the product — buttons, links, field labels and help text, error and validation messages, empty, loading and success states, confirmations, notifications, and onboarding steps; setting a voice and a tone that scale across a flow; a UX writing pass over a screen or journey; reviewing copy a designer or engineer wrote.

Do not use for: product documentation, help centres and guides, which is `technical-docs`; a whole-screen usability review where the layout or interaction is the problem, which is `ui-ux-review`; a conformance audit of names, labels and error associations, which is `accessibility-audit`; or marketing, brand and campaign copy, which is out of scope here.

## Workflow

### 1. Name the moment and the job the words do

For each string, write down where the user is and what they are trying to finish. A label on a first-run screen does a different job from the same label mid-task. Copy written without the moment drifts to explaining the feature instead of moving the user.

### 2. Label the action, not the mechanism

A control is named for what happens when it is used, in the user's verb. "Submit" names the form's behaviour; "Place order" names what the user is doing. "Delete 3 files" is better than "OK" and far better than "Yes". Match the label to the result the user gets, and use the same verb through the flow so the confirmation repeats the button's word.

| Weak | Why | Better |
| --- | --- | --- |
| Submit | Names the transport, not the outcome | Create account |
| OK / Yes | Forces the user to re-read the question | Discard draft |
| Manage | Names a vague area, not an action | Edit billing details |
| Learn more | Says nothing about the destination | How refunds work |

### 3. Write errors as what happened, then what to do

An error has three jobs: say what went wrong, in plain terms; say why, if the user can act on it; and say the next step. Blame the system or the data, never the person, and never show a code as the message. Put the message next to the field it belongs to, and make the first word the problem, not the word "Error".

```text
What happened:  Your card was declined.
Why (if useful): Your bank declined the charge — this often means the billing address did not match.
What to do:     Check the address and try again, or use a different card.
```

Field-level validation says the rule and the fix: "Enter a date in the past" beats "Invalid date". If the message could appear on any field, it is too generic to help.

### 4. Design the empty, loading and success states

- **Empty** — say why it is empty and the one action that fills it. A first-run empty state teaches; a filtered empty state offers to clear the filter. "No results" alone is a dead end.
- **Loading** — say what is happening and roughly how long when it is long enough to worry about, and never leave a spinner with no end.
- **Success** — confirm what happened in the same verb as the button, and say what happens next if anything does.

### 5. Hold the voice, shift the tone

Voice is the constant; tone moves with the moment. Decide three or four voice principles with a do/don't example each, so a new writer can apply them without asking. Then shift tone by context: warm and brief on a win, plain and steady on an error, careful and specific when money or data is at stake, neutral on anything a user reads often. Humour belongs nowhere near a failure, a payment or a deletion.

### 6. Run the plain-language pass

Read every string once for meaning, not style. Replace jargon with the user's word, cut the sentence to its verb and object, prefer the active voice, drop "please" and "simply" (both imply the user's failure), and spell out anything a screen reader will read as a symbol. Aim for the reading level of the audience, not the team.

### 7. Keep one term for one thing

Build a short termbase — the words this product uses for its objects and actions — and use it in the interface, the errors and the help. A user who reads "workspace", "project" and "team" for the same thing concludes they are three things. Where a term already exists in the help centre or the API, prefer it unless it is wrong for users, and note the decision.

### 8. Review the copy in the interface, not the doc

Read the strings in place, at the smallest supported width, with real data and the longest realistic value. Check truncation, wrapping, plural and gender forms, dates and numbers, and the order words land in after translation. A copy deck read on its own hides every one of these.

## Output format

```markdown
## Copy — [screen or flow], [moment]

| Element | Current | Proposed | Why |
| --- | --- | --- | --- |
| Primary button | Submit | Place order | Names the outcome in the user's verb |
| Field error | Invalid input | Enter a date in the past | States the rule and the fix |
| Empty state | No data | No invoices yet. Create one to get started. | Says why and the next action |

## Voice
[Three or four principles, each with a do and a don't example.]

## Terms
[The product's words for its objects and actions, and any changed.]

## Not changed, and why
[Strings that look wrong but are load-bearing, or that need a decision above this pass.]
```

## Anti-patterns

**The button that names the code path.** "Submit", "Process", "Execute" name what the system does and leave the user guessing at the result. Name the outcome.

**The error that shows the exception.** "Error 422: unprocessable entity" tells the user nothing and blames them for a message they cannot read. Translate it into what happened and what to do.

**Blame in the message.** "You entered an invalid date", "You must", "You failed to" turn a system limitation into a user fault. Rewrite it around the fix.

**Tone that ignores the moment.** A cheerful "Oops!" on a failed payment, or a formal "Your request has been received" on a friend's birthday reminder. Voice constant, tone by context.

**One term per team, not per product.** Three names for the same object, because three squads shipped them. Keep a termbase and use one.

**Copy written in a document and never seen in the screen.** Truncation, wrapping, translation order and the longest real value are invisible until the string sits in the interface.

**Filler that reads as care.** "Please note that", "simply", "just" — each adds words and subtracts clarity. Cut them.

## References

- `references/microcopy-patterns.md`: read when writing a specific element — the patterns and worked examples for buttons, links, field labels and help, error and validation messages, empty, loading, success and confirmation states, notifications and destructive actions.
- `references/voice-and-tone.md`: read when setting or reviewing voice — how to define voice principles, the tone spectrum by moment, the plain-language rules with before-and-after examples, the termbase practice, and a copy-review checklist.
