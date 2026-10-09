---
name: team-workflow
description: "Run FAMILY across a whole team: all six stages with a named owner, a handoff contract between each, and a cadence that runs Yield on a schedule. Covers the owner table, what each stage hands on, the artifacts that make a stall visible, and how the chosen profile stays visible. Use this skill whenever a team is setting up or fixing its development process. Triggers include a team workflow, roles and ownership, handoffs between design and engineering, a team retro cadence, or \"who owns each stage\" — including phrasings like \"our handoffs keep dropping\" or \"set up a process for the team\". Do not use it for the stage definitions themselves (family-workflow), a solo developer (solo-development), one developer's own loop (developer-workflow), or a QA role (qa-workflow)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*)
---

# Team workflow

A team's run of FAMILY is finished when each stage has a named owner, each handoff has a contract, the artifacts move rather than the meetings, and Yield happens on a cadence rather than when something hurts.

The failure of a team process is ownership without a handoff: each stage has a name next to it, but nothing says what moves between them, so work stalls between two people who each think the other has it. The second failure is the opposite — a process so heavy that the artifacts stop being read and the stages become meetings. FAMILY fixes the first by making the handoff a document with an owner, and avoids the second by keeping each artifact to what the next stage needs and nothing more.

## Scope

Use for: a team setting up or repairing its development process; naming who owns each stage; writing the handoff contract between stages; setting a cadence for Yield; making a stall visible before it becomes a slip.

Do not use for: the stage definitions themselves, which are `family-workflow`; a solo developer, which is `solo-development`; one developer's own loop, which is `developer-workflow`; or the QA role, which is `qa-workflow`.

## The owner table

| Stage | Owner | Hands to | Artifact |
| --- | --- | --- | --- |
| Frame | product or lead | Architect | The frame: problem, users, success criterion, slice |
| Architect | tech lead or senior engineer | Make | The design note and the ADR |
| Make | the developer | Inspect | The ordered change plan and the diff |
| Inspect | reviewer and QA | Launch | Findings by severity, and the go/no-go |
| Launch | release or ops owner | Yield | The launch plan: path, signal, rollback |
| Yield | the whole team, on a cadence | Frame | The retro |

"The team" owns nothing. A person owns each gate, and the name is written down. Read `references/team-cadence.md` for the handoff contract, the cadence, and how to run the process without it becoming meetings.

## Workflow

### 1. Name an owner for every stage

One person per stage, even if that person also owns another. The owner of a stage is accountable for its gate, not for doing all the work.

### 2. Write the handoff contract

For each edge in the owner table, state what moves: the artifact, the one question the next stage must answer first, and who owns it next. A handoff with no owner is where the work stalls.

### 3. Make artifacts, not meetings

The frame, the design note, the change plan, the findings, the launch plan and the retro are each a document. A stage that stalls is then visible as a missing artifact rather than a missed meeting, and the process keeps working across time zones and calendars.

### 4. Run Yield on a cadence

Schedule the retro; do not wait for something to hurt. `delivery-review` and `postmortem` feed it, and `status-update` shares its outcome. A team that yields only after an incident learns only from failure.

### 5. Keep the profile visible

Say which depth the team is running — solo, developer, QA or team — for the slice. A team running solo depth on a large slice is a decision; making it visible is what lets someone challenge it.

### 6. Fix the stage, not the person

When a handoff drops, the question is which stage's gate was unclear, not who missed it. A process that blames the person repeats the stall with a new person.

## Anti-patterns

**Ownership without a handoff.** A name next to each stage and nothing saying what moves between them, so work stalls between two owners.

**The process as meetings.** A stage that exists only as a meeting produces no artifact, so nothing moves when the meeting is skipped.

**"The team" owns it.** No individual accountable for a gate, so every gate is everyone's and therefore no one's.

**Yield only after incidents.** A retro called only when something breaks, so the team learns from failure and not from success.

**Invisible profile.** Running a light process on a heavy slice without saying so, so nobody can tell whether the shortcut was deliberate.

**Blaming the person.** A dropped handoff treated as a personal failure, so the stage's unclear gate is never fixed and the stall recurs.

## References

- `references/team-cadence.md`: read for the handoff contract format, the cadence that keeps Yield scheduled, the artifacts each stage owes, and how to make a stall visible.
