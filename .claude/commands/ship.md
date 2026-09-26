---
description: Run a change to this repository through the three-stage loop — explorer surveys what already exists, implementer writes it and runs the gates, reviewer judges the result before anything is committed.
argument-hint: '[what to change, for example "add a skill for reading flamegraphs"]'
allowed-tools: Agent(explorer), Agent(implementer), Agent(reviewer), Read, Grep, Glob, Bash(make:*), Bash(git status:*), Bash(git diff:*)
---

Take this change through the loop: $ARGUMENTS

Run the three stages in order, and do not collapse them. Each one exists because the
stage before it is the wrong context to do that work in.

Read [`docs/review-lessons.md`](../../docs/review-lessons.md) before deciding the shape
in stage 2 — it is the record of what review here has already caught, and a decision
that avoids a known class needs no fixing later.

## Handoff protocol

Each stage passes forward the previous stage's `Handoff` section, not a paraphrase of the
whole report — that section exists precisely so the next stage can start from three lines
instead of re-reading everything. `implementer` is the one exception: it receives the
brief from stage 2 verbatim, because that brief is what it needs to start cold, not a
summary of how it was reached.

The verdict word decides where the result goes next: `RED` from `implementer` or `FIX`
from `reviewer` goes back to `implementer` with the blocking findings only, never the
whole report re-sent; `STOP` from `reviewer` returns to this conversation for a decision
only a person can make; `GREEN` from `implementer` moves to stage 3, and `SHIP` from
`reviewer` ends the loop. There is no round limit on `FIX`, but the same finding coming
back a second time means the first attempt fixed a symptom — stop and address the root
cause before sending it back a third time. A report with no `Verdict:` line is a
question, and comes back to this conversation.

## 1. Survey

Delegate to `explorer`. Give it the change in one or two sentences and ask what already
covers it, where the affected files are, and which existing descriptions its trigger
surface would overlap.

Route on its verdict. `FOUND` means the repository already covers this: stop here and
report back, or take the change to stage 2 as an extension of what exists rather than a
new file — a skill that duplicates a sibling costs context on every session for whoever
installs the plugin and steals queries from the one that was already working, which is
worse than not writing it. `NOT FOUND` means nothing here covers it: go to stage 2 to
decide the shape of the new thing. `PARTIAL` means the answer turns on a judgement rather
than on anything further to find: decide it here, in this conversation, before going on.

## 2. Decide, then write

Settle the shape yourself from what `explorer` returned — which plugin owns it, what
already-existing thing it must not collide with, what goes in the body and what goes in
`references/` — and check it against `docs/review-lessons.md`. This is the part that
needs the conversation, so it does not get delegated.

Write the decision down as a brief with `implementer`'s five input fields before handing
it off, not as a paragraph it has to parse for them:

- **Goal** — the change, in one or two sentences.
- **Files or paths** — disjoint from anything else being written at the same time.
- **The settled decision** — what you just decided, above.
- **Constraints** — what not to touch, beyond `AGENTS.md`'s own boundaries.
- **Done-when** — `make validate`, `make catalogue` and `make test`, unless the change
  needs more.

Delegate to `implementer` with that brief verbatim, plus `explorer`'s `Handoff` line. It
writes the files and runs the named gates before returning `GREEN` or `RED`. On `RED`,
send the failure back to `implementer` rather than fixing the files here — it has the
context for the change and you do not.

## 3. Judge

Delegate to `reviewer` with the finished tree, its base, the change's intent in one
paragraph, and this loop's name (`/ship`). It runs the gates again itself rather than
trusting the report, checks the change against `AGENTS.md` and `docs/review-lessons.md`,
and executes every command the change prints.

`SHIP`: the loop is done, move to Finish. `FIX`: take its `Handoff` line — the blocking
findings only — back to `implementer`, and repeat from here. `STOP`: bring it to the user
with a recommendation rather than applying anything yourself; the split is what keeps the
reviewer's verdict independent of the hand that wrote the change.

## Finish

Report to the user: what changed as a list of paths, the validator's counts line and the
test summary quoted, the reviewer's verdict, and anything left unresolved. Then stop.

Do not commit and do not push. The loop ends with a green tree and a verdict; what to do
with it is the user's call.
