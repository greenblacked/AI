# The solo loop

## Contents

- A day in the loop
- Which gates are safe to waive
- Recording a waiver
- Replacing the missing reviewer
- Signals and rollback for a solo launch
- The five-minute retro

## A day in the loop

1. Pick one slice from the frame. If the frame has no slice small enough, split it.
2. Spend five minutes on the one hard-to-reverse decision, if this slice has one.
3. Build in small commits, each with a test or a check.
4. When the slice is demonstrable, hand the diff to `inspector` and the change to `code-review`.
5. Fix what they find, then plan the launch signal and rollback in one line.
6. Ship, watch the signal, and write the five-minute retro before the next slice.

The loop is a week for a small slice and an afternoon for a tiny one. The stages do not shrink to nothing; they shrink to one line each.

## Which gates are safe to waive

- **Frame** — never. It is a paragraph, and skipping it is how solo work builds the wrong thing.
- **Architect** — safe when the slice has no hard-to-reverse decision. Say so.
- **Make** — never waived, but the plan can be in your head for a one-file change.
- **Inspect** — never waived; it is the whole point of the profile. Delegate it.
- **Launch** — safe when there are no users and the rollback is the previous commit. Say so.
- **Yield** — never waived, but it can be three sentences.

## Recording a waiver

One line, in the issue or the commit, with the reason and the risk:

```text
Waiving Architect: renames a private function; no hard-to-reverse decision. Risk: none.
Waiving Launch: internal tool, no users; rollback is the previous commit. Risk: none.
```

A waiver recorded is a decision a future you can review. A waiver unrecorded is indistinguishable from a stage you forgot.

## Replacing the missing reviewer

A solo developer cannot give themselves an independent review, so the review is delegated:

- **`inspector`** — runs the tests and reads the diff against the frame. The first pass.
- **`code-review`** — the review a teammate would have written, for the change as a change.
- **`security-review`** — when the slice touches input, secrets, permissions or dependencies.
- **`accessibility-audit`** — when the slice is user-facing.
- **`decision-record`** — when the hard-to-reverse decision needs a second reader.

Treat their findings as the review, not as suggestions to skim. The value of the profile is that the second opinion happens at all.

## Signals and rollback for a solo launch

- **Signal:** the smallest thing that shows it worked — a log line, a metric, the page loading, the test in production. Name it before shipping.
- **Rollback:** for a small change, `git revert`; for a schema or data change, the down migration; for a hosted deploy, the previous release. Write which one it is.
- **Owner:** you. Decide in advance what would make you roll back, so the decision is not made at 1 a.m. under pressure.

## The five-minute retro

Three sentences, in the issue or a note:

1. Did the success criterion hold, and against what?
2. What would you do differently next time?
3. What is the next slice?

Anything longer does not get written. Anything shorter is not a retro.
