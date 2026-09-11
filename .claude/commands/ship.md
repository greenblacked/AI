---
description: Run a change to this repository through the three-stage loop — explorer surveys what already exists, implementer writes it and runs the gates, reviewer judges the result before anything is committed.
argument-hint: [what to change, for example "add a skill for reading flamegraphs"]
allowed-tools: Agent(explorer), Agent(implementer), Agent(reviewer), Read, Grep, Glob, Bash(make:*), Bash(git status:*), Bash(git diff:*)
---

Take this change through the loop: $ARGUMENTS

Run the three stages in order, and do not collapse them. Each one exists because the
stage before it is the wrong context to do that work in.

## 1. Survey

Delegate to `explorer`. Give it the change in one or two sentences and ask what already
covers it, where the affected files are, and which existing descriptions its trigger
surface would overlap.

Stop here and report back if the answer is that the repository already covers this. A
skill that duplicates a sibling costs context on every session for whoever installs the
plugin and steals queries from the one that was already working — which is worse than
not writing it.

## 2. Decide, then write

Settle the shape yourself from what `explorer` returned: which plugin owns it, what
already-existing thing it must not collide with, what goes in the body and what goes in
`references/`. This is the part that needs the conversation, so it does not get
delegated.

Then delegate to `implementer` with that decision, the paths, and anything from the
survey it would otherwise rediscover. It writes the files and runs `make validate`,
`make catalogue` and `make test` before returning. If it comes back with a red gate, send it the failure
rather than fixing the files here — it has the context for the change and you do not.

## 3. Judge

Delegate to `reviewer` on the finished tree. It runs the gates again itself rather than
trusting the report, checks the change against `AGENTS.md`, and executes every command
the change prints.

Take its blocking findings back to `implementer`. Take its non-blocking ones to the user
with a recommendation. Do not apply findings yourself: the split is what keeps the
reviewer's verdict independent of the hand that wrote the change.

## Finish

Report to the user: what changed as a list of paths, the validator's counts line and the
test summary quoted, the reviewer's verdict, and anything left unresolved. Then stop.

Do not commit and do not push. The loop ends with a green tree and a verdict; what to do
with it is the user's call.
