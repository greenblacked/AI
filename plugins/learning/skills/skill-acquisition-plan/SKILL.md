---
name: skill-acquisition-plan
description: "Plan learning a substantial new skill over weeks or months from a stated goal. Start from a proof artefact someone else can inspect, with a date (a deployed service, a passing practical exam, a talk given); decompose backwards by prerequisite and tag every sub-skill \"know about\" or \"can do\", counting only \"can do\"; budget hours from the calendar's real free time at a doing-to-reading ratio of at least 4:1; run a weekly cold test; at 25 per cent of the time change the method, not the hours, if under half pass; write a kill list of what is not being learned. Use when someone says \"I want to get good at distributed systems this year\", \"make me a plan to learn Go for a job switch\" or \"I keep buying courses and not finishing\". Not for making a behaviour stick (habit-change), a fixed exam date (exam-prep-plan), one tool in one week (learn-new-technology), or a weekly review (weekly-review)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Skill Acquisition Plan

A plan is finished when it names a proof artefact with a date, lists every sub-skill as one the learner can do rather than merely know about, fixes the hours from the calendar, and schedules a weekly test that can be failed.

The usual failure is a reading list. Courses and books feel like progress, but the learner can follow an explanation and still be unable to produce the thing, so months pass with nothing demonstrable. The second failure is a plan sized to intention: eight hours a week written down, two actually available. This procedure anchors on an artefact, counts only doing, and corrects the method early when the tests say it is not working.

## Scope

Use for: learning a substantial skill over weeks or months, such as a language for a job switch, distributed systems, a trade or an instrument, where a person can say what they want to be able to do.

Do not use for: making a behaviour stick, such as reading every night (`habit-change`); a fixed exam date and blueprint (`exam-prep-plan`); one tool in about a week (`learn-new-technology`); or a periodic look back at the week (`weekly-review`).

## Workflow

### 1. Pick the proof artefact and the date

Write one thing that exists at the end and that someone else could inspect: a service deployed and running with a public repository, a practical exam passed, a talk given, a pull request merged upstream, a piece performed for an audience. Give it a date. "Get good at" is not an artefact; "a service handling real traffic, with load test results, by 30 June" is. The artefact defines what counts, so it also tells you what you may skip.

### 2. Decompose backwards

Work back from the artefact: what must be true for it to exist, and what must be true before that. Stop when each leaf is a sub-skill small enough to practise in one or two sessions. Order by prerequisite. Tag each leaf honestly:

- Know about: can explain it, recognise it, discuss it.
- Can do: can perform it from a blank page without references, within a time you set.

Only "can do" counts toward progress. A leaf tagged "know about" is either promoted to "can do" with a defined test, or it is not on the plan. Read `references/plan-templates.md` for the decomposition table and example leaves.

### 3. Budget hours from the calendar

Open the calendar and count the hours that are actually free for the next four weeks, after work, sleep, family and existing commitments. Take the lower of that count and what you think you can sustain. A plan of four reliable hours a week beats ten imagined. Multiply by the weeks to the artefact date, and compare with a rough estimate of the effort the leaves need. If it does not fit, move the date, narrow the artefact or reduce the leaves; do not raise the hours on paper.

Fix a doing-to-reading ratio of at least 4:1. For every hour spent on courses, books or talks, spend four building, solving or performing. Doing is where the gaps appear.

### 4. Schedule the weekly cold test

Each week, perform the sub-skill the week targeted, without references, from a blank starting point, in a stated time. Record pass or fail in a table. A pass means the output meets a stated bar, for example "service builds, passes its tests and handles the failure case", not a feeling of confidence. Cold tests keep the plan honest because they cannot be passed by recognising the answer.

### 5. Checkpoint at 25 per cent

At a quarter of the elapsed time, count the cold tests. If fewer than half have passed, change the method, not the hours: switch from reading to building, find a mentor or reviewer, shrink the leaves, or use a different resource. More hours on a method that is not producing passes yields more of the same. If at least half have passed, continue and revisit the date at 50 per cent.

### 6. Write the kill list

List what you are deliberately not learning, for now: adjacent topics, tools, a second language, a course that looks interesting. The kill list is how the plan survives the temptation to widen. Revisit it after the artefact, not before.

### 7. Run it and revise at the checkpoints

Review weekly against the tests, and at each quarter point against the date. Revise the plan in writing so changes are visible. When the artefact is done, ask someone qualified to inspect it and record what they found.

## Hand back

The proof artefact and date; the decomposition table with each leaf tagged "can do" and its test; the hour budget with the calendar evidence; the weekly cold-test log; the 25 per cent checkpoint rule and its date; the kill list; and the first week's tasks. State the hours per week used and the doing-to-reading ratio planned.

## Anti-patterns

- **Course collecting.** Buying a course is a purchase, not a rep. Count it only as reading time.
- **Tagging "know about" as done.** Familiarity is the illusion this plan removes.
- **Hours from willpower.** Take them from the calendar.
- **Adding hours when tests fail.** Change the method first.
- **No external inspection.** An artefact only the learner can judge is a diary.
- **A kill list of one.** If nothing is cut, the plan has no limit.

## Reference files

- `references/plan-templates.md` - read at steps 2 to 5: the decomposition table with example leaves, the calendar-hours worksheet, the weekly cold-test log and the checkpoint decision table.
