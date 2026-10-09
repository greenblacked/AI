---
description: Run a change to this repository from survey to merge — two research agents in parallel, implementer writes it and runs the gates, reviewer judges it, then one pull request merged only once reviewer, ci and security pass.
argument-hint: '[what to change, for example "add a skill for reading flamegraphs"]'
allowed-tools: Agent(explorer), Agent(investigator), Agent(implementer), Agent(reviewer), Read, Grep, Glob, Bash(make:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git fetch:*), Bash(git switch:*), Bash(git worktree:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*)
disable-model-invocation: true
---

Take this change through the loop: $ARGUMENTS

Run the stages in order, and do not collapse them. Each one exists because the stage
before it is the wrong context to do that work in.

Read [`docs/review-lessons.md`](../../docs/review-lessons.md) before deciding the shape
in stage 2 — it is the record of what review here has already caught, and a decision
that avoids a known class needs no fixing later.

This loop is owner-only: it runs the gates and the change's own commands on the
owner's own work. Before stage 0, check whether the checkout holds any
contributor-authored content, meaning contributor commits or changes the owner has not
yet adopted (not on the base branch, `origin/dev` or the repository's default branch;
content already merged counts as adopted), and if it does, do not start. Return `STOP`
and say that a contributor change goes through the review loop only: a fresh `reviewer`
delegation with Author set to the contributor and the loop "contributor review", plus an
`investigator` only when the change rests on an outside claim ([`/verify`](verify.md)
takes that one claim, not the whole change). A fix the owner wants on top of a
contributor change happens only after the owner has adopted it: review the contributor
diff with the review loop first, then make the change as their own.

That review never runs from the contributor's checkout. Claude Code loads project
agents, settings, hooks, `CLAUDE.md`, `AGENTS.md` and rules from the session's working
directory, so a changed `reviewer.md` or hook would run before any Author guard does.
Run the session, and every agent it delegates, in a checkout of the base branch that
holds no contributor content: the owner's normal clone, or `git worktree add <dir>
origin/dev`. Fetch the current base and the contributor's head as a ref only, `git
fetch origin +refs/heads/<base-branch>:refs/remotes/origin/<base-branch> +pull/<n>/head:refs/review/<n>`, and pass the reviewer a base
ref and that candidate ref to read as data with `git diff <base>...refs/review/<n>`, never a checked-out tree. Here `<base>` is `origin/<base-branch>`, the remote-tracking ref that fetch updated, never a local branch, which may be stale. The
reviewer first requires the candidate to be based on the current base (`FIX` asking for a rebase otherwise), decides inert-only from `git diff -z --raw`, then creates and removes its own gate
worktree (the base plus the candidate merged) outside the project and reads file
contents only with `git show` on a canonical, single-quoted path; this session creates no worktree for it. If this session was itself opened inside a contributor
checkout, its settings and hooks have already loaded: return `STOP` and tell the owner
to restart from a trusted checkout. A `FIX` whose only open items are the owner-must-run ones (no blocking finding, and the candidate based on the current base) is cleared once the owner completes every owner-must-run item, including the live check where the change needs one, and records the results on the PR; for that head on that base tip only, that checklist counts as the passing review `AGENTS.md` requires, and a new push voids it, as does a base advance. A post-merge live check is recorded as named but not yet run, and a blocking finding or the rebase `FIX` still needs a fix and a fresh review. The reviewer never returns `SHIP` on such a change itself.

Never edit a file yourself, nits included — that is `implementer`'s job, on a fresh
delegation, so the change stays attributable to the stage the contract assigns it. An
improvement you or a reviewer notices along the way becomes a separate change, never a
same-PR edit.

## Handoff protocol

Each stage passes forward the previous stage's `Handoff` section, not a paraphrase of the
whole report — that section exists precisely so the next stage can start from three lines
instead of re-reading everything. `implementer` is the one exception: it receives the
brief from stage 2 verbatim, because that brief is what it needs to start cold, not a
summary of how it was reached.

The verdict word decides where the result goes next: `RED` from `implementer` or `FIX`
from `reviewer` goes back to `implementer` with the blocking findings only, never the
whole report re-sent; `STOP` from `reviewer` returns to this conversation for a decision
only a person can make; `STOP` from `explorer` or `implementer` ends the build loop, for one of two reasons.
If the Author line names a contributor, the change goes to a fresh `reviewer` delegation
from this trusted session, with Author set to the contributor, the loop "contributor
review" and a base ref plus candidate ref. If the checkout holds unadopted content, this
session is not trusted: return `STOP` and tell the owner to restart from a trusted
base-branch checkout. Only the second requires a restart. `GREEN` from `implementer` moves
through the rest of stage 3 — the Evidence check and, when stage 2 settled on one, the
pre-merge run — to stage 4, and `SHIP` from `reviewer` moves to stage 5. There is no
round limit on `FIX`, but the same finding coming back a second time means the first
attempt fixed a symptom — stop and address the root cause before sending it back a third
time. A report with no `Verdict:` line is a question, and comes back to this
conversation.

## 0. Branch or worktree

Fetch `origin/main` first: `git fetch origin main`. Then check `git status --porcelain`:
it has to be empty before switching this checkout onto a new branch, because a plain
branch reuses the session's own working tree, and an uncommitted change already sitting
in it would ride along onto the new branch rather than staying where it was. A non-empty
result means stop and ask, or use worktree mode instead, which leaves this checkout
untouched. Once it is empty, switch the session's own checkout onto the new branch:
`git switch --no-track -c <type>/<kebab> origin/main` — `--no-track` so the branch does
not inherit `origin/main` as its upstream.
With that upstream set, a plain `git push` either fails on the name mismatch under
`push.default=simple`, or pushes to `main` itself under `push.default=upstream`. Stage
5's `git push -u origin <type>/<kebab>` is what sets the correct upstream.
Every agent and every command below already runs in the right tree once this is done,
with no path to track or name.

Make a worktree instead only when parallel work needs it — two `/ship` runs at once, or
keeping the session's own checkout on `main` for something else meanwhile: `git worktree
add <path> -b <type>/<kebab> origin/main --no-track`. Once you do, name that path
explicitly on every command from here on — `git -C <path> …`, `make -C <path> …` — never
a bare `cd`: a worktree lives outside the project directory, and a Bash `cd` there resets
back to the project directory on the next call; naming the path explicitly removes the
dependency on whatever cwd you or a subagent inherited rather than the one you meant.
Record which mode you used and, for a worktree, the path — stage 2's brief needs it.

Enter plan mode here, in this conversation, before delegating — never inside a subagent —
whenever `AGENTS.md`'s Triggers table calls for it; a subagent working from a settled
brief never needs it, because the decision it would plan is already made.

## 1. Survey

Delegate to `explorer`. Give it "Author: repository owner", the change in one or two sentences and ask what already
covers it, where the affected files are, and which existing descriptions its trigger
surface would overlap. In worktree mode, name the worktree path in the prompt and ask it
to run every command as `git -C <path> …` / `make -C <path> …`, since `explorer` is
otherwise given no checkout path and would survey the session's own checkout, which may
not match `origin/main`.

When the change rests on one outside claim — how a flag behaves, what an API permits,
whether a cited figure is real — run `investigator` beside `explorer` in parallel on that
one claim, disjoint from `explorer`'s question, and pass it "Author: repository owner".
When it does not, a second `explorer` run on a disjoint question fills the same slot
instead. Either way the two run in parallel, not in sequence, and each answers only the
question it was given.

Route on `explorer`'s verdict. `FOUND` means the repository already covers this: stop
here and report back, or take the change to stage 2 as an extension of what exists rather
than a new file — a skill that duplicates a sibling costs context on every session for
whoever installs the plugin and steals queries from the one that was already working,
which is worse than not writing it. `NOT FOUND` means nothing here covers it: go to stage
2 to decide the shape of the new thing. `PARTIAL` means the answer turns on a judgement
rather than on anything further to find: decide it here, in this conversation, before
going on. Fold whichever agent ran beside it into the same decision.

## 2. Decide

Settle the shape yourself from what stage 1 returned — which plugin owns it, what
already-existing thing it must not collide with, what goes in the body and what goes in
`references/` — and check it against `docs/review-lessons.md`. This is the part that
needs the conversation, so it does not get delegated.

Also settle the live check here, as its own decision, never delegated to `implementer`:
it is one of four things.

- A **pre-merge run** — for anything a `GITHUB_TOKEN` is not required to exercise: an API
  call made with a real token, or a script run in a scratch directory. This conversation
  makes it after stage 3 and before stage 4, and keeps the output.
- **The PR's own CI run** — for a change to a workflow triggered by `pull_request`,
  provided the job the change touches actually runs on that PR rather than being skipped
  by its own `if:` — a skip does not read as a failure, so treat it instead as a named
  post-merge run, or make it a pre-merge run. A `GITHUB_TOKEN` grant exists only once
  Actions runs it, so nothing this conversation runs outside Actions can exercise it
  before the PR does. Name it here; stage 4 passes it to `reviewer` as named, not yet
  quoted, because the PR does not exist yet; once the PR opens in stage 5, watch that
  run and quote its outcome.
- A **named post-merge run** — for a trigger that can only run after merge: a
  default-branch-only trigger such as `workflow_run`, `schedule` or `pull_request_target`
  (`AGENTS.md`'s Triggers table), a push trigger filtered to `main`, or a tag trigger such
  as `release.yml`'s. Nothing before merge, PR included, could exercise any of them.
- **"None, because …"** — when nothing in the change touches a workflow `permissions:`
  grant, a new API write in a shipped script, or one of the three triggers `AGENTS.md`'s
  Triggers table names: `workflow_run`, `schedule` or `pull_request_target`.

Write the decision down as a brief with `implementer`'s six input fields before handing it
off, not as a paragraph it has to parse for them. The live check stays out of this brief —
it is this conversation's to run or to wait on, not `implementer`'s to write:

- **Goal** — the change, in one or two sentences.
- **Branch and checkout path** — the `<type>/<kebab>` branch stage 0 created. By default,
  pass no checkout path: `implementer` runs in this conversation's own checkout, already
  switched onto the branch, which is its current directory. For a worktree, pass the path
  stage 0 made instead.
- **Files or paths** — disjoint from anything else being written at the same time.
- **The settled decision** — what you just decided, above.
- **Constraints** — what not to touch, beyond `AGENTS.md`'s own boundaries, and the
  line "Author: repository owner" (a line inside this field, so the brief stays six fields).
- **Done-when** — `make validate`, `make catalogue` and `make test`, unless the change
  needs more.

Leave plan mode before delegating to `implementer` in stage 3, once the brief above is
settled. A subagent inherits the main conversation's permission mode, so one started while
this conversation is still in plan mode cannot write anything.

## 3. Write

Delegate to `implementer` with that brief verbatim, plus stage 1's `Handoff` line. It
writes the files and runs the named gates before returning `GREEN` or `RED`. On `RED`,
send the failure back to `implementer` rather than fixing the files here — it has the
context for the change and you do not.

After it returns, check its Evidence yourself: the `git status --porcelain` paths it
quotes are a subset of the brief's files, and the branch it quotes matches what stage 0
created. In the default case its Evidence has to show plain commands, with no `-C` and no
`cd`; for a worktree, `-C <path>` on every command instead, never a bare `cd`. A path
outside the brief, a branch that does not match, evidence that mixes the two forms, or
evidence that does not name the worktree's path when one exists, is a finding here, not
something to wave through because the gates were green.

When stage 2 settled on a pre-merge run, make it now, before stage 4, in a scratch
directory, and keep its output — this is what stage 4 hands to `reviewer`.

## 4. Judge

Delegate to a fresh `reviewer` with the finished tree, its base, the change's intent in
one paragraph, this loop's name (`/ship`), "Author: repository owner", and the live
check stage 2 settled: the pre-merge run's quoted output, the PR's own CI run (named, since it has not run yet), the
named post-merge run, or "none, because …". For a worktree, name its checkout path too —
`reviewer` defaults to the current directory otherwise, which is correct only because
stage 0 already switched this conversation's own checkout onto the branch by default; a
worktree lives outside the project directory, where a `cd` resets, so its path has to be
said outright rather than assumed. It runs the gates again itself rather than
trusting the report, checks the change against `AGENTS.md` and `docs/review-lessons.md`,
and checks every command the change prints, running one only under the conditions in
its point 4. Every round gets a fresh `reviewer`; the
one that judged an earlier round is never resumed, because a resumed reviewer is judging
its own prior verdict as much as the diff.

`SHIP`: move to stage 5. `FIX`: take its `Handoff` line — the blocking findings only —
back to `implementer`, and repeat from stage 3 (keep the "Author: repository owner" line in the Constraints of that brief). `STOP`: bring it to the user with a
recommendation rather than applying anything yourself; the split is what keeps the
reviewer's verdict independent of the hand that wrote the change.

## 5. Land

Once `reviewer` returns `SHIP`: in the default case, this conversation's own checkout is
already on the branch, so the commands below run as plain `git` commands. For a worktree,
name the path on every one instead — `git -C <path> add`, `git -C <path> commit`, `git -C
<path> push` — never a bare `cd`, for the reason stage 0 gave. A `-C`-qualified command
does not start with `git add`, `git commit` or `git push`, so it falls outside what
`Bash(git add:*)`, `Bash(git commit:*)` and `Bash(git push:*)` in `allowed-tools` cover
and prompts for approval each time — that is fine, and is not a reason to add a
`Bash(git -C:*)` entry to widen it.

- commit under the owner's own authorship, with no tool attribution, and never
  `--amend`;
- push the branch, setting the upstream since stage 0 checked it out with
  `--no-track`: `git push -u origin <type>/<kebab>`, or `git -C <path> push -u origin
  <type>/<kebab>` for a worktree;
- open the pull request from `.github/pull_request_template.md`, using whatever GitHub
  access this session has, with the PR body stating the live check settled in stage 2 —
  the pre-merge run's output, a note that this PR's own CI run is the live check (with
  which permission or write path it covers), the named post-merge run still to come, or
  "none, because …";
- once the PR's own CI run is the live check, watch it complete and quote its outcome in
  the PR before stage 7 — this is what turns "named" into "observed", and stage 7 cannot
  proceed without it;
- re-read every body and comment a tool wrote back to you before moving on, and strip any
  footer it appended by itself as soon as you see it. `check_attribution.py` checks
  commits, the branch name, and the PR's own title and body, and fails the build on a
  footer left in any of those — it never reads a comment, so a footer left in one is
  caught by nothing at all, which is exactly why this strips it the moment it appears
  rather than trusting a gate to catch it.

## 6. Wait

Wait for `ci`, `security` and the automated PR review. A blocking finding from any of
them goes to `implementer` with that finding alone (keep the "Author: repository owner" line in the Constraints of that brief). When the live check is a pre-merge
run, the fix changes the code it describes, so re-make it and get the new quote before
the fix goes to `reviewer` — one fresh round has to see the current quote, not a stale
one, so re-quoting after that round would only buy a second round for no reason. Then
send the fix to a fresh `reviewer` (again with "Author: repository owner"); once it returns `SHIP`, the fix lands as a new commit
on the same branch — never a rewrite of the one already pushed. Push it, and wait for
`ci`, `security` and the automated review again; a fix is not proven until the same three
have run on the commit that made it. When the live check is the PR's own CI run instead,
that push is what triggers it: wait for the run, quote the new outcome, and get it in
front of a fresh `reviewer` (again with "Author: repository owner") — the same as the first time, and for the same reason — the
earlier quote describes code that is no longer on the branch.

## 7. Merge

Merge only once the latest `reviewer` verdict is `SHIP`, `ci` and `security` are both
green on the commit that verdict actually judged, and no blocking finding from any
reviewer — human or automated — is left unaddressed. When the live check is a pre-merge
run or the PR's own CI run, that `SHIP` has to come from a round that saw and quoted the
outcome for the commit actually being merged: a `SHIP` given against an earlier quote, or
while the PR's own run was still only named, before the PR existed to run it, does not
satisfy this — get a fresh `reviewer` round (again with "Author: repository owner") on the current quoted outcome first. Squash
the merge, passing the reviewed head SHA to whatever merge call accepts one, and, when
stage 0 made a worktree, remove it with `git worktree remove <path>` — run from the main
checkout, not from inside the worktree itself.

## 8. Prove

Run the named post-merge check stage 2 settled on, against the real, merged state — not
a repeat of anything offline — and quote its outcome in the PR, the way `AGENTS.md`'s
Triggers row asks. When stage 2 instead settled on a pre-merge run, the PR's own CI run,
or "none, because …", there is nothing further to run here; say so and stop, since each
of those was already made and quoted before merge. A failure in the post-merge run is not
a reason to reopen the same PR: open a fix PR instead, and add the defect to
`docs/review-lessons.md` with its own benchmark case, the way every other entry there was
added.

## Finish

Report to the user: what changed as a list of paths, the validator's counts line and the
test summary quoted, the reviewer's verdict, the PR and merge outcome, the live check's
result, and anything left unresolved. Then stop.
