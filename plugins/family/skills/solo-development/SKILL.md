---
name: solo-development
description: "Run the FAMILY workflow as one person: all six stages, lightly, with the stage agents as the independent checkers a solo developer otherwise lacks. Covers the smallest useful version of each stage's gate, when a solo run may waive a gate in writing, and how to keep Make and Inspect honest when you are both. Use this skill whenever someone is building alone and wants a process that fits. Triggers include a solo or one-person project, an indie or side project, a freelancer's workflow, or \"I have no team, how should I work\" — including phrasings like \"just me on this codebase\" or \"I'm the only developer\". Do not use it for the stage definitions themselves (family-workflow), a developer on a team (developer-workflow), a QA role (qa-workflow), or a whole team's process (team-workflow)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*)
---

# Solo development

Running FAMILY alone is finished when all six stages happened at the depth one person can carry, each gate was passed or waived in writing, and the one part a solo developer cannot do — review their own work — was delegated to an agent rather than skipped.

The failure of a solo process is not ceremony; it is the missing second opinion. One person frames, builds and reviews the same idea, so the frame is never challenged, the design is whatever came to mind, and the review finds only what the author already believes. The other failure is the opposite: a solo developer copies a team's ceremony — standups, handoff meetings, a retro nobody attends — and abandons the process within a week because it costs more than it returns. This skill keeps the stages and drops the ceremony, and it replaces the missing reviewer with the stage agents.

## Scope

Use for: a one-person project, an indie or side project, a freelancer's client work, a solo maintainer of an open-source repository, or anyone who is both the developer and the reviewer.

Do not use for: the stage definitions themselves, which are `family-workflow`; a developer working inside a team, which is `developer-workflow`; the QA role on a team, which is `qa-workflow`; or a whole team's process, which is `team-workflow`.

## The stages at solo depth

| Stage | Solo depth | Artifact |
| --- | --- | --- |
| Frame | A paragraph in the issue: problem, user, done, slice | The issue |
| Architect | The hard-to-reverse decision only, in a short note | A paragraph and, when it counts, an ADR |
| Make | Small commits, each with its test | The commits |
| Inspect | Delegate to `inspector` and `code-review`; do not self-review | Findings, then fixes |
| Launch | All three: a path, a signal, a way back | A note, even if the rollback is "revert" |
| Yield | Five minutes: what worked, what did not, the next slice | A note in the issue |

Read `references/solo-loop.md` for the day-to-day loop, which gates are safe to waive and how to record the waiver, and the self-review workarounds.

## Workflow

### 1. Keep a running frame, not a document

The frame is a paragraph at the top of the issue that you update as you learn. It is the only stage that is cheap to skip and expensive to skip, so make it the one thing you always write.

### 2. Decide the one hard-to-reverse thing before building

Most solo work has one decision that is expensive to undo: a schema, a file format, a public interface. Write that one down with the alternative that lost. The rest of the design can live in your head and in the commits.

### 3. Build in small, revertible commits

One purpose per commit, a test or a check per commit, so a wrong turn costs one revert rather than an afternoon. This is also the proof the reviewer will read.

### 4. Delegate the review you cannot give yourself

This is the stage solo work gets wrong. Hand the diff to `inspector`, and the change to `code-review`, and treat their findings as the review a teammate would have given. Do not read your own diff and call it reviewed.

### 5. Still plan the launch

A solo launch is a push, but it still needs a signal and a way back. "I would revert the commit" is a valid rollback when written down; an unstated one is not.

### 6. Yield in five minutes

Before starting the next slice, write what worked, what did not, and what is next. A solo developer's only institutional memory is the notes they leave themselves.

## Gate waivers

A solo run may waive a gate, and should say so in one line with the risk. The pattern:

```text
Waiving Architect: the change is a copy edit; no hard-to-reverse decision. Risk: none.
Waiving Launch: internal tool, no users; rollback is the previous commit. Risk: none.
```

A waiver is a decision. An unrecorded skip is how a solo project ends up with no frame, no tests and no way back.

## Anti-patterns

**Self-review.** Reading your own diff and calling it inspected. The agents exist so this is not the only review you get.

**Team ceremony for one person.** Standups, handoff meetings, a retro nobody attends. Keep the stages, drop the meetings.

**The frame in your head.** A problem statement you never wrote down, which drifts as you build and is never checked against the result.

**One giant commit.** A weekend of work in a single commit, unreviewable and unrevertible.

**No Yield.** Finishing a slice and starting the next, so the same mistake repeats because nothing was written down.

## References

- `references/solo-loop.md`: read for the day-to-day loop, the gate-waiver format, which gates are safe to waive, and the self-review workarounds that replace a teammate.
