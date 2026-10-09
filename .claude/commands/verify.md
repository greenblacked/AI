---
description: Run a claim a change rests on through the verification loop — investigator settles it against primary sources and labels what it could not verify, reviewer judges whether the finding supports the change.
argument-hint: '[the claim to check, for example "kubectl drain --force skips the grace period"]'
allowed-tools: Agent(investigator), Agent(reviewer), Read, Grep, Glob, Bash(git status:*), Bash(git diff:*)
disable-model-invocation: true
---

Check this claim: $ARGUMENTS

Run the two stages in order, and do not collapse them. The second exists because the
first is the wrong context — and in this loop, the wrong kind of evidence — to do that
work in.

## Handoff protocol

Each stage passes forward the previous stage's `Handoff` section, not a paraphrase of the
whole report. `investigator` receives the claim and what it rests on as a short brief,
the same way `implementer` does in [`/ship`](ship.md) — settle both in this conversation
before delegating, because that judgement travels badly through a cold prompt.

From `investigator`: `DOES NOT HOLD`, `NARROWER` or `UNVERIFIED` means the change needs
editing. For a change this session wrote, take the finding to the files or to
`implementer` rather than investigating again, then go to stage 2 with the edit. For a
contributor change, send the finding to the owner or the contributor and never to
`implementer`, because the build loop is owner-only; stage 2 waits for their edit.
`HOLDS` goes to stage 2 directly. `UNVERIFIED` is
a real result: report it as such, do not retry it. From `reviewer`: `FIX` on a change
this session wrote returns the named findings to the files or to `implementer`. `FIX` on
a contributor change goes back to the owner or the contributor, with the findings and any
gates for them to run, only in a disposable sandbox with no credentials and no network, as the reviewer's Not assessed list states, and never to `implementer`, because the build loop is owner-only.
A `FIX` that only waits on gates names the gates for the owner and never loops; a `FIX` whose only open items are the owner-must-run ones (no blocking finding, and the candidate based on the current base) is cleared once the owner has completed every owner-must-run item, including the live check where the change needs one, and recorded the results on the PR, which counts as the passing review `AGENTS.md` requires for that head on that base tip only (a new push voids it, as does a base advance; immediately before accepting the checklist, and again before merge, the owner re-fetches both refs with the same quoted fetch command, then compares `git rev-parse --verify 'refs/remotes/origin/<base-branch>^{commit}'` with the pinned `<base>` and `git rev-parse --verify 'refs/review/<n>^{commit}'` with the reviewed candidate SHA; any difference voids the clearance (rebase or re-review); a post-merge live check is recorded as named but not yet run; a blocking finding or the rebase `FIX` still needs a fix and a fresh review), and the reviewer never returns `SHIP` there itself. `STOP`
comes to the user for a decision; `SHIP` ends the loop. There is no round limit, but the
same finding recurring means the edit fixed a symptom rather than the premise — stop and
address that before trying a third time. A report with no `Verdict:` line is a question, and comes back to this
conversation.

A contributor change is judged from a clean worktree at the pinned base SHA
(`git worktree add --detach '<dir>' '<base>'`, or the owner's clone of the base branch checked out exactly there), never the
contributor's: Claude Code loads agents, settings, hooks and `CLAUDE.md` from the
session's working directory, so a modified `reviewer.md` or hook would run before any
Author guard. This command has no `git fetch`, so the owner, after checking that `<base-branch>` is `dev`, `stage` or `main` and that `<n>` is all digits, fetches the current base and the contributor's
head as a ref only (`git fetch origin '+refs/heads/<base-branch>:refs/remotes/origin/<base-branch>' '+pull/<n>/head:refs/review/<n>'`), and both agents
get `<base-branch>`, the pinned `<base>` and that candidate ref to read with `git diff '<base>'...refs/review/<n>`,
where `<base-branch>` must be `dev`, `stage` or `main` and match `^[A-Za-z0-9][A-Za-z0-9._/-]*$` as a whole name (any other base is `STOP`: retarget the PR), and `<base>` is the SHA from `base_sha=$(git rev-parse --verify 'refs/remotes/origin/<base-branch>^{commit}')` run right after the fetch,
not a checked-out tree. The reviewer first validates `<base-branch>`, `<base>` and `<n>` before running any command (`STOP` on any mismatch), then requires the candidate to be based on the current base (`FIX` asking for a rebase otherwise), decides inert-only from `git diff -z --raw`, then
creates and removes its own gate worktree (the base plus the candidate merged) outside the project, reading files only with
`git show` on a canonical, single-quoted path. If this session was opened inside a
contributor checkout, or `git rev-parse --verify 'HEAD^{commit}'` is not `<base>`, return `STOP` and tell the owner to restart from a clean worktree at the pinned SHA.

## 1. Decide, then investigate

Pick the claim that matters yourself. A change usually rests on several checkable things
and only one of them holds it up; which one that is depends on what the change argues,
which lives in this conversation and travels badly through a cold prompt. This is the
same split [`/ship`](ship.md) makes when it keeps the shape of a change out of
`implementer`.

Then delegate to `investigator` with one claim and what rests on it, and with the
Author: "repository owner" for a change this session wrote, otherwise the contributor's
name (contributor-authored content keeps the contributor's name through every fix
round). It finds the source and reads it, prefers refuting to confirming, labels each
finding primary, consensus or inference, and reports what it could not verify.

Send one claim. Three gets you a finding about none of them.

## 2. Judge

Delegate to `reviewer` on the change with the finding attached and the same Author line
(for a contributor change the loop stays `/verify`, with `<base-branch>`, the pinned
`<base>` and the candidate ref passed in). The question here is no longer whether the claim is true, because `investigator`
settled that. It is whether the change is now consistent with what was found: whether
the sentence that cited the claim says something the evidence actually supports, whether
the paragraph built on it still stands once the premise narrowed, whether a figure
softened to "roughly a third" is still doing the work the precise number was doing.

That cannot be folded back into stage two. An agent that has just spent its context
establishing a fact is the worst-placed reader of the prose around it, because it knows
what the sentence was meant to say and reads that in. `reviewer` arrives cold, with the
contract in `AGENTS.md` and no stake in the finding.

## Finish

Report to the user: the claim as checked, the verdict with its label, what could not be
verified, and the specific edit the finding implies. Quote the evidence rather than
summarising it — a summary of a source is a new claim, and it starts the loop again.

If the verdict is unverified, say so plainly rather than as a hedge attached to a claim
you are keeping. An unverified number is worse than no number, because the figure carries
an authority its provenance does not.

Do not commit and do not push. The loop ends with a finding and a recommended edit; what
to do with it is the user's call.
