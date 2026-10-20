# From notes to bugs and a ranked change list

Read this at steps 6 to 8, once the sessions are over and the notes are on the table.

## Contents

- [Sorting: bug or design finding](#sorting-bug-or-design-finding)
- [Severity and reproducibility](#severity-and-reproducibility)
- [Filing a bug](#filing-a-bug)
- [Counting design findings](#counting-design-findings)
- [The ranked change list](#the-ranked-change-list)
- [Choosing the metric](#choosing-the-metric)
- [Closing the round](#closing-the-round)

## Sorting: bug or design finding

Go through every line of the record sheets and ask one thing: did the build do what its author intended? Answer from the design, not from how the line reads.

| Observation | Intended behaviour | Sorted as |
| --- | --- | --- |
| Door did not open though the player had the key | Opens | Bug |
| Door opened; the player walked past it three times | Opens; player expected to see it | Design finding |
| Boss killed the player in a way the damage table does not allow | Damage table | Bug |
| Boss killed the player ten times and they did not understand the attack | As designed | Design finding |
| Player fell through the floor | Floor holds | Bug |
| Player quit after the second death with no way to see what hit them | As designed | Design finding |
| Tutorial prompt appeared late and was missed | Appears on time | Bug, with the missed prompt as a finding |

Edge cases, in order:

1. A bug that exposes a design weakness is filed as a bug and linked from the finding. Fixing the bug will not fix the weakness.
2. When it is unclear what the author intended, ask the author. If nobody knows, treat it as a design finding, because an unspecified behaviour is a design gap.
3. A blocker bug during a session makes that session partial for the question it affected. Keep its other lines, and exclude its timings from the group.
4. Feature requests are neither. Keep the complaint behind them, as a design finding, and drop the proposed solution.

## Severity and reproducibility

Two scales, kept separate, because one number for both hides the case that matters: a bug that is severe and rare.

**Severity, by what the player loses:**

| Level | The player | Examples |
| --- | --- | --- |
| Blocker | Cannot continue, or loses progress or data | Crash, soft-lock, corrupted or lost save, no way to leave a room |
| Major | Can continue only by a workaround, or a main feature does not work | Objective does not register until a restart, a core ability fails |
| Minor | Notices, and is not stopped | Wrong animation, mis-sorted inventory, stuck UI element that clears itself |
| Cosmetic | Notices only if looking | Texture seam, typo |

**Reproducibility, by what you have seen:**

| Level | Meaning | What to do |
| --- | --- | --- |
| Always | Every attempt with the steps | File with steps |
| Sometimes | Some attempts; state the count, for instance 3 of 5 | File with the count and what differed between attempts |
| Once | Seen once, not retried | File as unconfirmed with the recording timestamp; do not drop it |
| Unknown | Not enough information | Ask the tester after the session, then reclassify |

The triage rule: severity decides priority, reproducibility decides how much work is needed before a fix can begin. A blocker seen once outranks a cosmetic fault seen always, and goes to the front of the queue as something to investigate rather than something to fix. A crash, soft-lock or lost save is filed regardless of reproducibility. Do not ask a tester to reproduce a bug during the session; it changes the session, and the recording usually holds what you need.

## Filing a bug

One bug per ticket, title in the form "what happens, where", filed the same day. Search for a duplicate first; if there is one, add the new evidence and the new build id to it rather than opening another.

```text
Title:           <what happens>, <where>
Build id:        <exact build>
Platform:        <device, OS, input device, display>
Start state:     <profile, save, or the point in the game>
Steps:           1. ...
                 2. ...
Expected:        <what should happen, from the design>
Actual:          <what happened>
Frequency:       <x of y attempts, or "seen once, not retried">
Severity:        <blocker | major | minor | cosmetic>
Evidence:        <recording file and timestamp, log, screenshot>
Found in:        playtest <date>, tester <number, not a name>
```

Refer to testers by number. Their names do not belong in a tracker the whole team can search. If the steps cannot be written from the recording, the ticket says so and names the gap; a guessed step is worse than a missing one because someone will follow it.

Close the loop: when a fix ships, the ticket names the build that contains it, and the next round's session block names that build as the one under test.

## Counting design findings

Merge duplicates across the record sheets into one line per finding. For each, count the testers who hit it, out of the group, and record what it cost them: blocked, quit, died repeatedly, hesitated, remarked on it. Leave out percentages; with a handful of testers they claim precision you do not have.

- Several testers hit it: a design problem. Rank it.
- One tester hit it: a person, unless the consequence was catastrophic, in which case rank it and say so.
- Nobody hit it but you expected someone to: nothing found. Do not rank a prediction.

## The ranked change list

A short list, a few lines, one row per change. Longer lists are not read. Rank by three things together: how many testers were affected, how severe the consequence was (a block or a quit outranks a grumble), and how cheap the fix is. When two are close, take the cheaper.

| Rank | Finding | Evidence | Suspected cause | Change | Metric that should move |
| --- | --- | --- | --- | --- | --- |
| 1 | Players do not find the exit | 4 of 5 stuck over a minute, recorded at 12:40, 07:15, 21:03, 15:30 | The exit is lit the same as the walls | Light the exit and add a landmark visible from the entrance | Time to first success, down; testers stuck at the exit, none of five |
| 2 | ... | | | | |

Keep suspected cause and change as separate columns. The tester's report is the finding; the cause is your hypothesis, and the next round is what tests it. A cause confirmed by nothing is still a guess.

## Choosing the metric

The metric comes from the record sheet or the survey, so the next round can measure it the same way. Good ones are what was recorded: time to first success, count of testers stuck, count of deaths at the named point, whether the quit point moved, the survey item tied to the change. State the direction and the threshold now, before the fix ships: "time to first success under two minutes for at least four of five". A threshold written after the next round is written around its result.

If the change cannot be measured by anything on the sheet, either the sheet is missing a line, which you add and note as a change to the script, or the change is a judgement call, which you label as one.

Do not choose a metric a playtest cannot move. Retention over a month, a win rate or a conversion figure needs volume and time that a handful of sessions does not have; those belong to telemetry and `game-balance`.

## Closing the round

- The question from step 1 has an answer in writing: yes, no or unclear, with the evidence and the decision it led to.
- Every bug is in the tracker with a build id, or has been deliberately dropped with a reason.
- The ranked list is short, each row has its metric, and the thresholds are written down.
- The next round's script is identical to this one apart from the build, and the notes say so.
- The three things that surprised you, written the day of each session, are kept with the notes. They are the findings you did not know to look for.
