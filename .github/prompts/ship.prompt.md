---
description: Run a change to this repository from survey to merge, with two research agents in parallel, implementer writing it and running the gates, reviewer judging it, then one pull request merged only once reviewer, ci and security pass.
argument-hint: what to change, for example "add a skill for reading flamegraphs"
agent: agent
---
<!-- source: .claude/commands/ship.md sha256: 32f89cf4a27bbc6a97b489ad0556bb72866db5bfff1a1d711afb3bed4fad37d0 -->

Take this change through the loop: ${input:change:what to change}

Run the stages in order, and do not collapse them. Each exists because the stage before it is the
wrong context to do that work in. The stages hand work to the custom agents `explorer`,
`investigator`, `implementer` and `reviewer` (`.github/agents/`). Where custom agents are not
available, run each stage as its own fresh chat with that agent's file as the instructions.

Read `docs/review-lessons.md` before deciding the shape in stage 2. It is the record of what
review here has already caught.

Never edit a file yourself, nits included. Writing is `implementer`'s job, on a fresh
delegation, so the change stays attributable to the stage the contract assigns it. An
improvement noticed along the way becomes a separate change, never a same-PR edit.

Base branch: the commands below name `origin/main`, as the source command does. Where
`.github/copilot-instructions.md` says to branch from and open pull requests into another branch,
use that one.

## Handoff protocol

Each stage passes forward the previous stage's `Handoff` section, not a paraphrase of the whole
report. `implementer` is the exception: it receives the brief from stage 2 verbatim.

The verdict word decides where the result goes next. `RED` from `implementer` or `FIX` from
`reviewer` goes back to `implementer` with the blocking findings only. `STOP` from `reviewer`
returns to the person for a decision. `GREEN` from `implementer` moves through the rest of stage 3
to stage 4, and `SHIP` from `reviewer` moves to stage 5. There is no round limit on `FIX`, but the
same finding coming back a second time means the first attempt fixed a symptom: address the root
cause before sending it back a third time. A report with no `Verdict:` line is a question, and
comes back to the person.

## 0. Branch or worktree

Run `git fetch origin main`. Then `git status --porcelain` has to be empty before switching this
checkout onto a new branch, or an uncommitted change rides along onto it. If it is not empty, stop
and ask, or use a worktree instead. Once it is empty:
`git switch --no-track -c <type>/<kebab> origin/main` (`--no-track` so the branch does not inherit
`origin/main` as its upstream; stage 5's `git push -u origin <type>/<kebab>` sets the right one).

Use a worktree only when parallel work needs it: `git worktree add <path> -b <type>/<kebab>
origin/main --no-track`. Then name that path on every command (`git -C <path> ...`,
`make -C <path> ...`), never a bare `cd`. Record which mode you used and the path, because the
stage 2 brief needs it.

Plan before delegating, in this conversation and never inside an agent, whenever `AGENTS.md`'s
Triggers table calls for it. Agree the approach with the person before any file is changed.

## 1. Survey

Delegate to `explorer`. Give it the change in one or two sentences and ask what already covers it,
where the affected files are, and which existing descriptions its trigger surface would overlap.
In worktree mode, name the path and ask it to run every command as `git -C <path> ...` and
`make -C <path> ...`.

When the change rests on one outside claim (how a flag behaves, what an API permits, whether a
cited figure is real), run `investigator` beside `explorer` in parallel on that one claim.
Otherwise a second `explorer` run on a disjoint question fills the slot. Each answers only the
question it was given.

Route on `explorer`'s verdict. `FOUND`: stop and report, or take the change to stage 2 as an
extension of what exists, because a skill that duplicates a sibling costs context on every
session and steals queries from the one that already worked. `NOT FOUND`: go to stage 2 to decide
the shape of the new thing. `PARTIAL`: decide it here, before going on, folding in whatever the
other agent returned.

## 2. Decide

Settle the shape yourself from what stage 1 returned: which plugin owns it, what it must not
collide with, what goes in the body and what goes in `references/`. Check it against
`docs/review-lessons.md`. This part needs the conversation, so it is not delegated.

Also settle the live check as its own decision, never delegated to `implementer`. It is one of:

- A pre-merge run: for anything a `GITHUB_TOKEN` is not required to exercise, such as an API call
  made with a real token or a script run in a scratch directory. Make it after stage 3 and before
  stage 4, and keep the output.
- The pull request's own CI run: for a change to a `pull_request`-triggered workflow whose
  touched job actually runs on that PR rather than being skipped by its own `if:`. Name it here;
  stage 4 passes it to `reviewer` as named, not yet quoted; once the PR opens in stage 5, watch
  the run and quote its outcome.
- A named post-merge run: for a trigger that can only run after merge, such as `workflow_run`,
  `schedule` or `pull_request_target` (`AGENTS.md`'s Triggers table), a push trigger filtered to
  `main`, or a tag trigger such as `release.yml`'s.
- "None, because ...": when nothing touches a workflow `permissions:` grant, a new API write in a
  shipped script, or one of those three triggers.

Write the decision as a brief with `implementer`'s six fields, not a paragraph: Goal; Branch and
checkout path (none by default, the worktree path otherwise); Files or paths, disjoint from
anything else being written; The settled decision; Constraints; Done-when (`make validate`,
`make catalogue` and `make test`, unless the change needs more). The live check stays out of the
brief.

## 3. Write

Delegate to `implementer` with that brief verbatim, plus stage 1's `Handoff` line. It writes the
files and runs the named gates before returning `GREEN` or `RED`. On `RED`, send the failure back
to `implementer` rather than fixing files here.

Then check its Evidence yourself: the `git status --porcelain` paths it quotes are a subset of the
brief's files, and the branch matches what stage 0 created. A path outside the brief, a branch
that does not match, or evidence that mixes plain commands and `-C <path>` is a finding here, even
if the gates were green. When stage 2 settled on a pre-merge run, make it now and keep its output.

## 4. Judge

Delegate to a fresh `reviewer` with the finished tree, its base, the change's intent in one
paragraph, this loop's name (`ship`), the checkout path in worktree mode, and the live check from
stage 2. It runs the gates itself, checks the change against `AGENTS.md` and
`docs/review-lessons.md`, and executes every command the change prints. Every round gets a fresh
`reviewer`; never resume the one that judged an earlier round.

`SHIP`: move to stage 5. `FIX`: take its `Handoff` line back to `implementer` and repeat from stage
3. `STOP`: bring it to the person with a recommendation rather than applying anything yourself.

## 5. Land

Once `reviewer` returns `SHIP`, in worktree mode name the path on every git command.

- Commit under the owner's own authorship with no tool attribution, and never `--amend`.
- Push the branch, setting the upstream: `git push -u origin <type>/<kebab>`.
- Open the pull request from `.github/pull_request_template.md`, with the body stating the live
  check settled in stage 2: the pre-merge run's output, a note that this PR's own CI run is the
  live check, the named post-merge run still to come, or "none, because ...".
- When the PR's own CI run is the live check, watch it complete and quote its outcome in the PR
  before stage 7.
- Re-read every body and comment a tool wrote back, and strip any footer it appended as soon as you
  see it. `scripts/check_attribution.py` checks commits, the branch name, and the PR title and
  body, never a comment.

## 6. Wait

Wait for `ci`, `security` and the automated PR review. A blocking finding from any of them goes to
`implementer` with that finding alone. When the live check is a pre-merge run, re-make it and get
the new quote before the fix goes to a fresh `reviewer`. Once it returns `SHIP`, the fix lands as
a new commit on the same branch, never a rewrite of one already pushed. Push it and wait for `ci`,
`security` and the automated review again. When the live check is the PR's own CI run, the push
triggers it: wait, quote the new outcome, and put it in front of a fresh `reviewer`.

## 7. Merge

Merge only once the latest `reviewer` verdict is `SHIP`, `ci` and `security` are green on the
commit that verdict judged, and no blocking finding from any reviewer, human or automated, is left
unaddressed. When the live check is a pre-merge run or the PR's own CI run, that `SHIP` has to come
from a round that saw and quoted the outcome for the commit being merged. Squash the merge, passing
the reviewed head SHA, and in worktree mode remove it with `git worktree remove <path>` from the
main checkout. Merging also needs the owner's go-ahead, per `.github/copilot-instructions.md`.

## 8. Prove

Run the named post-merge check stage 2 settled on, against the real merged state, and quote its
outcome in the PR as `AGENTS.md`'s Triggers row asks. If stage 2 settled on anything else, there is
nothing further to run; say so and stop. A failure in the post-merge run is not a reason to reopen
the same PR: open a fix PR, and add the defect to `docs/review-lessons.md` with its own benchmark
case.

## Finish

Report: what changed as a list of paths, the validator's counts line and the test summary quoted,
the reviewer's verdict, the PR and merge outcome, the live check's result, and anything left
unresolved. Then stop.

Full prompt: `.claude/commands/ship.md`.
