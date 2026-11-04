---
name: game-bug-triage
description: "Write game bugs down so they can be reproduced, and rank them so a release decision can be made. Gives every bug one record of build id, platform and hardware, save file or its hash, RNG seed, input log or replay, and measured repro rate — then assigns a severity from a fixed S1 to S4 scale (S1 is a crash, progress loss, soft-lock or save corruption on a progression path, or a certification failure) and applies the release gate: no open S1, and every open S2 has a named owner and a written decision. Turns a playtest note or a bot failure into a record. Use when a tester says the game broke, a bug list needs ranking before ship, or someone asks whether a bug blocks release. Not for playtest findings that are design problems rather than bugs (game-playtest), grouping crash signatures from live telemetry (crash-triage in client-apps), or the save format itself (game-save-system)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Game Bug Triage

Every open bug has one record that lets a stranger reproduce it, one severity that follows from a written scale, and a release gate that reads the severities rather than the mood of the room.

Game bugs are hard to triage for reasons a web service does not share. The state that causes the failure is a save file, a random seed and forty minutes of input, none of which a tester thinks to keep. The same crash is a shrug on a sandbox level and a blocker on the only route to the ending. And the severity argument happens in the last week, when everyone is tired, so a scale invented in that week is shaped by the deadline. This skill fixes the record before the bug is filed and the scale before the argument starts.

## Scope

Use for: the bug record, the severity scale, the release gate, turning a playtest finding or an automated-playthrough failure into a record, estimating repro rate, and deciding whether an open bug blocks a milestone or ship.

Do not use for: grouping and ranking crash signatures from shipped builds by affected users, symbolication and crash-free rate — that is `crash-triage` in the client-apps plugin. Designing or running a playtest session is `game-playtest`, which hands this skill the findings that are bugs. Save versioning, migration and atomic writes are `game-save-system`; this skill only records which save reproduces a bug. Building the unattended bot is `automated-playthrough`; this skill is what happens to its failures. Certification requirements themselves are `game-certification`.

## Workflow

### 1. Fix the record before filing anything

A bug without the inputs to reproduce it is a rumour. Each field below exists because its absence has cost somebody a day:

| Field | What goes in it | Why it is not optional |
| --- | --- | --- |
| Build id | The exact build, as printed by the game itself (changelist, commit or build number), not the branch name | Branch names move; the bug is in one binary |
| Platform and hardware | Platform, console model or GPU and driver, CPU, RAM, OS version, storage type, input device | Many game bugs are timing, memory or driver bugs and vanish on the developer's machine |
| Save | The save file attached, or its hash plus where the archived copy lives | The state at the moment of failure is usually in the save; a description of it is not |
| Seed | The RNG seed for the run or encounter, or "not applicable" stated | Without it a procedural or random-driven bug is a lottery |
| Input log or replay | The recorded inputs, replay file or video with the input overlay | Steps written from memory skip the step that mattered |
| Repro rate | `k` of `n` attempts from the same save, not "sometimes" | Decides who can fix it and how to know it is fixed |
| Expected and actual | One line each | Separates a bug from a design disagreement |
| Progression path | Whether the failing content is on the route to the ending or a required unlock | Severity depends on it (step 2) |

Read `references/bug-record.md` for the record as a template, with the capture hooks worth building so a tester gets these fields without typing them.

### 2. Assign severity from the scale, not from feelings

Severity is what the bug does to the player, judged together with whether they can avoid it. Priority is when it gets fixed; keep the two separate, because a rare S1 and a common S4 are both real and the gate reads severity only.

| Severity | Definition | Examples |
| --- | --- | --- |
| S1 | Crash, hang, progress loss, soft-lock or save corruption on a progression path; or any certification failure | Crash entering the third dungeon; a quest flag that never sets so the door never opens; a save that fails to load after the autosave; a suspend and resume that hangs on a console |
| S2 | Major feature broken or progress blocked, with a workaround the player can find; or an S1-class failure off the progression path | A crash in an optional side area; a required item that can be dropped and re-picked up to unstick the quest; a currency duplication that is not yet exploited; audio gone after the first cutscene until restart |
| S3 | Wrong behaviour that does not block or lose anything | A weapon that does the wrong damage type; a localisation string overflowing a button; a minor animation pop; a collision gap that can be walked round |
| S4 | Cosmetic or polish: the player would not notice or would not mind | A texture seam; a misspelt tooltip in a rarely seen menu; a particle clipping |

Two rules keep the scale honest. First, a soft-lock is S1 on the progression path however rare: judge the cost of one occurrence, which is a player who cannot finish the game, rather than the frequency. Frequency decides priority within a severity, not the severity. Second, raise severity when the player cannot recover without losing time: a crash that autosave wraps to ten seconds before is lower than one that loses an hour.

If you cannot decide between two levels, ask what the player does next. If they cannot continue or lose saved progress, it is S1. If they can continue after finding a workaround, S2. If they continue unaffected, S3 or S4.

Read `references/severity-calls.md` for the hard cases: exploits and duplication, performance regressions, accessibility failures, bugs only on one platform, and bugs in content few players reach.

### 3. Measure the repro rate

"Sometimes" cannot be scheduled or verified. From the attached save, run the recorded input `n` times and write `k/n`. Twenty attempts is the floor for anything you intend to call fixed. The rule of three is useful: if a fix survives `n` clean runs with no failures, the failure rate could still be as high as about `3/n` at 95 per cent confidence, so 10 clean runs shows only that it is below roughly 30 per cent, and 100 clean runs below roughly 3 per cent. A bug that fires one run in fifty needs several hundred runs to be declared gone, which is a job for an unattended loop, not a tester.

When the rate is low, record what narrows it before rewriting the title: does it need a cold start, a particular save, a platform, a frame-rate cap, a second controller? A rate that rises under one condition has told you the cause's neighbourhood. If it never reproduces from the save, say so, and keep the bug open at its severity with the evidence, rather than closing it as unreproducible after one attempt.

### 4. Turn a failure into a record

From a playtest. A note such as "game froze in the market" becomes a record in four moves: ask which build the tester had and which device, fetch the save and any session recording from the playtest's capture folder, replay from that save to estimate `k/n`, then write expected and actual. Keep the tester's wording as a quote in the record; it is the symptom as the player experienced it. Do not file a tester's guess at the cause as a fact. Findings from the session that are not bugs (comprehension, difficulty) go back to `game-playtest`'s ranked change list.

From an automated playthrough. The run's failure artefacts already hold most of the record: build id, seed, final state, the last log lines and a screenshot. Add platform and hardware of the runner, attach the replay, and re-run it from the seed to get `k/n`. Deduplicate before filing: runs that die at the same place with the same last log lines are one bug with a count, not a hundred. A run that hit a timeout with no progress is a candidate soft-lock; treat it as S1 until the position is checked against the progression path. Read `references/failure-to-record.md` for worked examples of both, and for a short script that fills the mechanical fields from a failure folder.

### 5. Apply the release gate

At a milestone or ship decision, read the list as it stands:

- No open S1. Not "S1 with a fix in review": the gate reads the status of the bug, which is closed only when the fix is verified on the candidate build with the repro rate from step 3.
- Every open S2 has a named owner, who is a person, and a written decision: fix before release, ship with a known issue and a stated workaround, or defer to a named patch. An S2 with no owner or no decision blocks.
- S3 and S4 do not gate. Review the S3 count by area; a cluster in one system is a signal the area is not ready.

Waiving an S1 is not a triage decision. It is a release decision that belongs to whoever owns the release, written in the record with the reason, the player impact and the patch plan. If the S1 is a certification failure, it cannot be waived by the studio at all: the platform holder decides, so the choices are to fix or to move the date.

Check the gate against the candidate build, not the previous one. A bug marked fixed against a build that is not the release candidate is still open for this purpose.

### 6. Keep the list honest

Re-triage after every build that changes the progression path, since a route change can promote a bug from S2 to S1. Close duplicates by linking, not deleting. Record severity changes with the reason. Count open bugs by severity per build and plot the S1 and S2 counts: a rising S2 count in the last weeks means the gate will be argued, so start those decisions early.

## Anti-patterns

**The title that is the whole record.** "Crash in forest" gives the next person nothing to run. A record without a save and an input log is not ready to be assigned.

**Severity by loudness.** The bug the director saw on the stage demo outranks a silent save corruption. The scale is there so that the quiet one wins.

**Averaging frequency into severity.** A one-in-a-thousand soft-lock on the only route to the ending is still S1, because the player it hits cannot finish. Use frequency for priority.

**Closing on one clean run.** A bug at one in ten passes a single attempt nine times in ten. Close on the run count from step 3.

**The unowned S2.** An S2 with no name attached is the bug that ships by default. Naming an owner is cheap, and the decision is what the gate checks.

**Waiving at triage.** Downgrading an S1 to S2 to make the gate pass is the same defect as editing a check so it passes. Change the severity only when the facts change.

## References

- `references/bug-record.md` — read at step 1: the record as a template, and capture hooks that fill the fields automatically.
- `references/severity-calls.md` — read at step 2: hard cases for exploits, performance, accessibility, single-platform bugs and rarely reached content.
- `references/failure-to-record.md` — read at step 4: worked examples from a playtest note and an automated-playthrough failure, with a script that fills the mechanical fields.
