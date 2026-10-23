---
name: exercise-design
description: "Write a programming or operations exercise, lab or kata that teaches one thing and can be done unattended. Built from the end: the working solution first, then failing tests or a check script that gives the learner a clear signal within two minutes, starter code that compiles and runs, and a three-tier hint ladder (nudge, approach, near-solution) kept in separate files. Calibrate by a cold run with someone outside the author's context, plan for twice the author's time, list every mistake from it, test the error messages a learner will see, and ship the solution with its reasoning. Use when someone says \"write exercises for my workshop\", \"design a lab for learning Git rebase\" or \"my tutorial exercises are too hard or too easy\". Not for the whole session (workshop-design), tests for production code (test-design), or a take-home or pairing exercise for interviews (hiring-loop)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Exercise Design

An exercise is finished when someone who did not write it, working alone with no help beyond the hint files, reaches a passing check in about half the time you allowed, and every mistake they made is listed with its fix.

The usual failure is an exercise that works for its author. The author knows which file to open, reads the error message knowing what it means and solves the problem in a third of the time a newcomer needs. The exercise then teaches three things at once, fails with a stack trace the learner cannot read, and leaves them stuck with nobody to ask. This procedure builds the exercise backwards from what the learner must be able to do, and tests it on a person before anyone else sees it.

## Scope

Use for: a single programming or operations exercise, lab or kata that a learner does alone, in a workshop, course or self-study setting.

Do not use for: the structure of the whole session, its timing and staffing (`workshop-design`); tests for production code (`test-design`); or a take-home or pairing exercise set for interviews (`hiring-loop`).

## Workflow

### 1. State the one thing

Write one sentence: "After this, the learner can ___". It names a single concept or skill, such as resolving a rebase conflict, or reading a query plan to find a missing index. If the sentence has an "and", you have two exercises. Everything else in the exercise is scaffolding and should be reduced to the minimum or supplied ready-made, since each extra concept competes for the learner's attention with the one you are teaching.

### 2. Build the solution first

Write the working solution before anything else, and run it. Then remove the part the learner is to supply and leave the rest as the setup. Doing it in this order guarantees the exercise is solvable, shows how long the task really takes, and exposes the points where the learner will need knowledge you did not intend to teach. If the solution needs a trick unrelated to the one thing, change the exercise.

### 3. Write the check

Write failing tests or a check script before the starter code. The check is the learner's only feedback when alone, so it must say clearly whether they are done and, if not, what is wrong. Requirements:

- It gives a signal within two minutes of starting, and ideally within seconds. A learner who cannot tell whether they are on track will stop.
- One failure at a time, in plain words, naming what was expected and what was found.
- It fails on the starter code, passes on the solution, and cannot be passed by an accidental shortcut such as returning a constant.
- It tests the one thing, not incidental behaviour such as output formatting.

Read `references/exercise-kit.md` for a check-script skeleton and the error-message checklist.

### 4. Write the starter code

The starter compiles and runs. A learner should meet the check failing for the intended reason, not a syntax error or a missing dependency. Mark the place to work with a comment. Pin dependency versions and give one command to set up and one to run the check. For operations labs, supply a resettable environment and a command to reset it, because a lab that cannot be reset after a mistake ends at the first mistake.

### 5. Write the hint ladder

Three hints, each in a separate file so the learner chooses to open the next one:

1. Nudge: points to where to look or what to notice, with no method.
2. Approach: names the method or concept to use and why, with no code.
3. Near-solution: the solution with one key piece missing.

Separate files matter because a hint on the same page is read before it is needed. Each hint should be enough to unblock someone who has already tried for several minutes, so write them after the cold run, not before.

### 6. Cold run

Give the exercise to someone outside your context: not the person who reviewed it, and not someone who watched you build it. They work alone and think aloud or are screen-recorded. Time them and plan for twice the author's time as the stated time, because the author's time reflects knowing the answer. Do not help. If they stall, note where and for how long, and let them open hints.

### 7. Record mistakes and fix the exercise

Every wrong step the cold run took goes into the common-mistake list, each with its symptom and what the learner should do. Then decide for each: fix the exercise if the mistake came from unclear instructions, add to the list if it is a normal wrong turn on the concept. Test the error messages a learner will actually see by making those mistakes yourself and reading the output as a newcomer would. Rewrite the ones that do not say what to do next.

### 8. Ship the solution with its reasoning

The solution file includes the code and a short explanation: why this approach, what the common alternatives are and why they fall short, and the concept's one-sentence summary. A learner who passed by luck gets the explanation; a learner who failed gets the answer without having to ask.

## Hand back

The statement of the one thing, instructions, starter code, check script, three hint files, the common-mistake list, the solution with reasoning, the setup and reset commands, the stated time (twice the author's time, adjusted by the cold run) and the cold-run notes.

## Anti-patterns

- **Two lessons in one exercise.** If failure could mean two different misunderstandings, the check cannot tell which.
- **A check that only says FAILED.** Without what was expected and found, the learner guesses.
- **Hints in the instructions.** Opening the exercise reveals the answer. Keep them in separate files.
- **Timing by the author.** Your time is a lower bound. Use the cold run.
- **Starter code that does not run.** The first thing the learner learns is that the exercise is broken.
- **Skipping the solution's reasoning.** Code alone teaches imitation.

## Reference files

- `references/exercise-kit.md` - read at steps 3, 4 and 7: a check-script skeleton, the error-message checklist, the hint-file layout, the common-mistake list format and the cold-run log.
