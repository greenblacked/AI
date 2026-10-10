# The benchmark case

## Contents

- What a case contains
- Seeding the diff
- Honest clean changes
- Scoring a run
- Promotion and pruning

## What a case contains

Three things, kept together in one directory per case:

- **A seeded diff.** The smallest real change that reproduces the defect against the tree as it is today. Not a toy: it should look like something an author would write.
- **The expected verdict.** The word the inspector must return for it, `FIX` for a defect it can evidence, `STOP` for one only a person can weigh, `PASS` for a clean change.
- **What the findings must say.** One or two phrases, or small patterns, that a correct finding contains, so a `FIX` for the wrong reason does not count.

The case also names the lesson it exercises, by the entry's heading, so a lesson with no case is visible as a heading nothing points at. The shape for a case file:

```text
case.json     { "kind": "defect", "intent": "...", "lesson": "<entry heading>",
                "expected_verdict": "FIX", "must_mention": ["retry|attempt", "bound|limit"] }
change.patch  the seeded diff
```

This is one workable layout, not a requirement. What matters is that each lesson has a runnable case and that the expected verdict is written down.

## Seeding the diff

1. Start from the real defect in the slice that produced the lesson.
2. Cut it down to the lines that carry the defect, and apply it to the current tree, not to the tree it was found in.
3. Check the patch applies cleanly. An applicability check proves the case is runnable, not that the inspector detects the defect, so also run the inspector on it.
4. Run the inspector without the new entry first. A catch without the entry means the lesson adds nothing and is not accepted.

## Honest clean changes

Add clean cases beside the defect cases: ordinary changes with an expected `PASS`, ideally near-misses that resemble a lesson's shape without the defect (a retry with a bound, for the unbounded-retry lesson). They are the only way to see an inspector that has learned to flag everything. Keep roughly one clean case for every two or three defect cases.

## Scoring a run

Run every case on a fresh inspector delegation and compute:

- **Catch rate** = defect cases where the verdict matched and the findings contain the required phrases, divided by defect cases.
- **False alarms** = clean cases that returned `FIX` or `STOP`, counted as a number and as a share of clean cases.

Report both on every run, with the model and effort the inspector ran at. A model that is deliberately cheaper or stronger changes both numbers, and the comparison is only fair at a fixed tier. A drop in catch rate after an instruction change is the signal that the change cost something; a rise in false alarms is the signal that the lessons file has become noise.

## Promotion and pruning

- Caught in two separate slices: promote to a mechanical check and keep the entry until the check lands.
- Mechanical check in place: prune the entry and keep the case as a regression test of the check, or retire it with the entry. Say which, in the commit.
