# Plan and checkpoints

The plan is the file the work is measured against. It is written once, approved, then updated in place as tasks finish and as the work drifts. Keep it beside the spec so the two are read together.

## The task shape

Each task has five lines:

- **Task** — one change, described by its outcome ("the export endpoint returns the header row"), not by its activity ("work on export").
- **Check** — a command with an expected result, or an observable step with an expected outcome. It has to be runnable by someone who did not write the task. If writing the check is hard, the task is too large or too vague.
- **Depends on** — the earlier tasks that must have passed, or `none`.
- **Covers** — the acceptance criteria numbers it moves toward, so every criterion is reached by some task and no task exists for nothing.
- **Status** — `pending`, `passed`, `failed` or `dropped`, with the date and the command output reference when it is not pending.

Size a task so that its check can fail for one reason. A task whose check can fail in three unrelated ways will be debugged as three tasks at once. A task you would not want to review as a single change is also too large.

## Finding the riskiest assumption

Before ordering anything, list what the approach assumes without having verified: that a library handles the volume, that a third-party endpoint returns what its documentation says, that two systems agree on an identifier, that a migration finishes in the available window. Rank by two questions: how likely is it to be false, and how much of the plan is wasted if it is. The one that is both likely and costly goes first, as the smallest task that exercises it against the real thing. A thin end-to-end path through every layer is a good first task when the unknown is how the pieces fit.

If the riskiest assumption turns out false, the plan after it is probably invalid. Say so in the plan: mark the task as a gate, and note that the remaining tasks are to be re-planned if it fails. Do not detail the late tasks beyond what is known; a precise plan for work that may not happen is false confidence.

## Ordering the rest

After the risky first task, order by dependency, then by what makes the next check easiest. Put cheap tasks with obvious checks between expensive ones so progress is visible. Leave interface polish and documentation to the end; they depend on everything and rarely invalidate anything.

## The plan file

```markdown
# Plan: <feature>

Spec: <path>   Status: draft | approved   Approved: <date, by whom>

## Tasks

### 1. <outcome>   [gate]
Check: <command or step> -> <expected result>
Depends on: none
Covers: AC1
Status: pending

### 2. <outcome>
...

## Drift log

(empty until the first checkpoint)
```

## The checkpoint routine

A checkpoint happens after every task that passes, and also whenever the work pauses or changes hands. At each one:

1. Run the task's check and record the result in `Status`. A failed check is recorded as failed, with what was observed, before anything is changed.
2. Reopen the spec and the plan from disk. Do not rely on what the session remembers of them.
3. List what has been built so far. `git status` and `git diff --stat` show it; compare the changed files with those the plan implies.
4. Compare, and write each difference into the drift log. Differences to look for: a change in a file or area the plan does not mention; a task done differently from how it was written; a new dependency; a criterion that is now unreachable or has changed meaning; work done that no task or criterion asked for; an assumption from the spec that has been found false.
5. Decide whether the drift is small or large (see below), and act accordingly.
6. State the next task and its check before starting it.

## The drift log

One entry per difference, appended and never edited:

```markdown
- <date>, after task 3: task 4 split in two because the serializer needed a
  separate fix first. Reason: the existing serializer drops null columns.
  Affects: tasks 4a, 4b. Class: small. Spec unchanged.
```

Fields: when and after which task; what differs; the reason; what it affects (tasks, criteria, non-goals); the class.

**Small** drift stays inside the approved spec and approach: a task split, a reordering, a check made more precise, an extra helper the task needed. Record it and continue.

**Large** drift changes what the requester approved: a criterion dropped or reworded, a non-goal now needed, the chosen approach abandoned, a constraint found to be wrong, the gate task failing. Stop, state the change and the reason, and ask for approval to amend the spec or plan before doing more work. Then update the file, mark it with the new approval, and keep the old entry in the log.

Work that no task asked for is large drift unless it is removed. If it is valuable, propose it as a new task or a follow-up and keep the current plan clean.

## Closing

At the end every task is `passed`, `failed` with an accepted reason, or `dropped` with a log entry. Run each acceptance check and report per criterion. The drift log is part of the report: a reader who sees a clean log and a different outcome from the spec should suspect the log.
