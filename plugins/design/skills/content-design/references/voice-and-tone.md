# Voice and tone

## Contents

- Voice is constant, tone moves
- Defining voice principles
- The tone spectrum by moment
- Plain language rules
- The termbase
- Reviewing copy
- Checklist

## Voice is constant, tone moves

Voice is the product's personality — the same on every screen, in every channel. Tone is how that voice sounds in a given moment: brighter on a win, steadier on a failure. A team that writes without this distinction either sounds the same everywhere, which reads as cold on an error and flat on a celebration, or reinvents the personality per screen, which reads as several products.

## Defining voice principles

Write three or four principles, each with a do and a don't. They should be specific enough that two writers reach the same string.

```text
Clear before clever.        Do: "Your card was declined."   Don't: "Card says no."
Human, not chummy.          Do: "Something went wrong."      Don't: "Whoopsie!"
Direct, never blunt.        Do: "Enter a date in the past."  Don't: "Invalid date."
Calm about money.           Do: "We could not process this." Don't: "Uh oh!"
```

Keep them where writers work — a page in the design system, not a slide. Add an example the last time a principle decided a string.

## The tone spectrum by moment

| Moment | Tone | Example |
| --- | --- | --- |
| Success | Warm, brief | "Order placed. We will email a receipt." |
| First run | Encouraging, concrete | "Let's set up your first project." |
| Routine use | Neutral, invisible | "Saved." |
| Waiting | Reassuring, specific | "Checking availability — this takes a few seconds." |
| Error (recoverable) | Plain, steady, no blame | "We could not save that. Try again." |
| Error (money or data) | Careful, specific, factual | "Your card was declined. No charge was made." |
| Danger zone | Serious, explicit | "This deletes 3 files and cannot be undone." |
| Sensitive (health, grief, money) | Quiet, no jokes | "We are sorry. Here is what to do next." |

Never put humour on a failure, a payment, a deletion or anything the user did not choose.

## Plain language rules

- **One idea per sentence.** Split on "and" when the two halves are separate jobs.
- **Active voice.** "We could not save your changes", not "Your changes could not be saved".
- **The user's word, not the team's.** "Sign in", not "authenticate". "Files", not "assets".
- **Cut the hedges.** "Please note that", "simply", "just", "in order to", "at this time".
- **No blame.** "You entered an invalid date" → "Enter a date in the past".
- **No idiom or metaphor.** Both break in translation and for readers who take words literally.
- **Front-load the point.** The first two or three words carry the meaning in a scannable UI.
- **Numbers as digits in data, words in prose.** Dates and units in the user's locale.

Before and after:

```text
Before: Please note that in order to proceed, you will be required to authenticate yourself.
After:  Sign in to continue.

Before: You entered an invalid date of birth.
After:  Enter a date of birth in the past.

Before: Your request could not be processed at this time due to a system error.
After:  We could not process your request. Try again in a moment.
```

## The termbase

A short table of the words this product uses for its objects and actions. One term per thing, used in the interface, the errors and the help.

| Concept | Use | Not |
| --- | --- | --- |
| A unit of work | project | workspace, board, space |
| Adding a person | invite | add, share with |
| Ending a session | sign out | log out, log off |
| The main list | inbox | feed, stream |

- Prefer a term already in the help centre or the public API, unless it is wrong for users.
- When you change a term, note the decision and sweep the interface in one pass; half-changed terminology is worse than the old term.
- Add a row only when the same thing has been named two ways in the product.

## Reviewing copy

- Read it in the interface, at the narrowest supported width, with the longest realistic value.
- Read it aloud. Anything you stumble on, the user will too.
- Check the flow, not just the string: does the confirmation repeat the button's verb?
- Check the states: empty, loading, error, success, and the disabled control.
- Check translation: no concatenated sentences, no embedded symbols a screen reader will read aloud, no idioms.
- Check terms against the termbase, and add the new ones.

## Checklist

- [ ] Every label names the action in the user's verb
- [ ] Every error says what happened and what to do, without blame or a code
- [ ] Every empty state says why and the next action
- [ ] The tone matches the moment; the voice does not move
- [ ] Plain language: active, concrete, no hedges, no idiom
- [ ] One term per thing, across interface, errors and help
- [ ] Read in the interface, at the narrow width, with real data
- [ ] Plural, zero and translated forms covered
