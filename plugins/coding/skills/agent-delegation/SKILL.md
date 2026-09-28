---
name: agent-delegation
description: "Brief one coding agent on one bounded task so the result can be judged without re-deriving context: set the done-check first as a runnable command whose exit code decides finished, supply a failing test or reproduction when one exists, name the paths the agent may not touch — tests, CI config, lint and coverage thresholds, lockfiles — and the conditions under which it must stop and ask rather than improvise. Use when someone says have Claude do this, write a prompt for the agent, brief this ticket for an AI coding tool, or the agent keeps rewriting things nobody asked for. Not for coordinating several live agents on one task (agent-orchestration), checkpointing unfinished work (agent-handoff), or judging the returned diff (code-review)."
allowed-tools: Read, Write, Glob, Grep
---

# Agent Delegation

A brief is finished when a reader with no memory of writing it could tell, from the brief alone, exactly what "done" means and exactly what the agent was and was not allowed to touch.

The job is hard because a coding agent optimises for the instruction it was actually given, not the intention behind it. Told to "make the tests pass" with no other constraint, the cheapest way there is often to edit or delete the failing test, and an agent under that pressure will find it — not out of malice, but because the done-check said nothing about how it had to get there. The same gap produces the rewritten file nobody asked for, the new dependency nobody approved, and the "done" report with no evidence behind it. Every one of these is a brief that skipped a step this skill exists to make mandatory, not a flaw specific to any one agent or model.

## Scope

Use for: writing the task brief that hands one bounded piece of work to one coding agent — the done-check, the evidence to give it, the scope fence, the stop conditions, and what the report back has to contain.

Do not use for: coordinating several live agents on one outcome, which needs a dependency graph and shared ownership rules this skill does not cover — that is `agent-orchestration`. Preserving an unfinished task so a later session can resume it, which is `agent-handoff` — this skill is for starting new work, not checkpointing work already in progress. Judging the diff that comes back, which is `code-review` — this skill sets up the brief the diff is judged against, it does not judge the result itself.

## Hard gates

1. A brief with no done-check does not go out. "Make the tests pass" alone is refused until it is paired with the excluded-paths list in step 3 — a test file is the cheapest edit to reach green, and a done-check with no fence around it invites exactly that.
2. Evidence in the returned report is a command and its output, never a sentence describing the outcome. "Done" with nothing behind it is not evidence.
3. The task is sized to one reviewable diff. A brief that cannot be described as one bounded change is split into a sequence of briefs, or handed to `agent-orchestration` instead.

## Workflow

### 1. State the done-check before anything else

Write one runnable command whose exit code decides "done" — a specific test, a build, a named assertion — into the brief verbatim. If that command does not exist yet, write it first, even as a currently-failing test, before drafting anything else in the brief. A brief written before its own done-check exists is a brief nobody can verify without re-deriving what "done" was supposed to mean.

### 2. Supply the failing evidence, not a description of it

Paste or link the failing test's actual output, the reproduction steps, or the bug report itself. The agent starts cold, with no memory of any conversation that led here — "the bug we discussed" or an unexplained internal name is dead weight it cannot act on. If there is no existing evidence because the task is new work rather than a fix, say so plainly rather than leaving the gap implicit.

### 3. Fence the scope explicitly

List every path the agent may edit, and, separately, every path it may not: tests, CI configuration, lint and coverage-threshold configuration, and lockfiles are the four that most often hide a shortcut to a green done-check rather than an actual fix. This list is what makes step 1's done-check trustworthy — without it, the agent has every incentive to edit the test the done-check runs rather than the code the test is checking.

### 4. Name the stop conditions

State the conditions under which the agent must stop and ask rather than improvise: discovering a need for a new dependency, a schema change, a change to a public interface, or touching more files than a stated number. Size the task so the expected result is one diff of roughly 400 changed lines or fewer — the size a reviewer can actually read in one pass, and the reason `code-review` treats a much larger diff as a sign the change should have been split before it reached review.

### 5. Require evidence in the report

State explicitly what the returned report must contain: the exact command that was run and its output, and the list of changed files. Refuse a report that only asserts completion — the entire reason the done-check is a command rather than a description is so its exit code decides, not the agent's own account of what it did.

### 6. Judge the result on a fresh context

Once the diff comes back, hand it to `code-review` for the correctness and merge decision, on a context that has not seen the agent's own account of what it did. Never accept the authoring agent's own summary of its diff as the verdict — the agent that wrote the change is the one party least able to notice what it got wrong. `/agent-diff-audit` can run the mechanical checks — shrunk test counts, newly silenced checks, invented dependencies — first, so `code-review` starts from a flagged list rather than a blank diff.

## Anti-patterns

**"Make the tests pass" with no excluded-paths list.** The cheapest way to reach a green done-check is to edit or delete the failing test, and an agent given a done-check with no fence around it will find that path — not because it is dishonest, but because nothing in the brief said it could not.

**Pasting "the approach we discussed" into the brief.** The agent starts cold. An unexplained internal name, or a reference to a conversation it was not part of, is not context it can act on — it is a gap the agent has to guess across.

**Accepting "done" with no command output.** A claim is not evidence. The entire point of a runnable done-check is that its exit code decides, not the agent's own report of what happened.

**Sizing the task to whatever fits in one message instead of to one reviewable diff.** A vague, large brief produces a diff nobody can review in one pass, and the failure surfaces at review time — expensively — rather than at brief time, when splitting the task would have been cheap.

## Output format

The brief itself, as a short document with these sections:

```markdown
## Done-check
[The exact runnable command whose exit code decides "done".]

## Evidence
[The failing test's output, the reproduction, or the bug report — pasted or linked, not summarised.]

## Scope
May edit: [paths]
May not edit: [paths — tests, CI config, lint and coverage thresholds, lockfiles, named explicitly]

## Stop conditions
[What forces the agent to stop and ask rather than proceed.]

## Report format required back
[The exact command and its output, and the list of changed files.]
```

## Reference files

- `references/brief-template.md` — read when writing the actual brief text: the fixed section template above, filled in for two worked examples — a one-field addition and a one-function bug fix.
- `references/sizing.md` — read when deciding whether a task is small enough for one brief or needs handing to `agent-orchestration` instead: the roughly-400-line heuristic, why it matches `code-review`'s own threshold, and how to split a larger task into a sequence of briefs rather than one oversized one.
