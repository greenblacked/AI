# Plan templates

## Contents

- Proof artefact statement
- Decomposition table
- Calendar-hours worksheet
- Weekly cold-test log
- Checkpoint decision table

## Proof artefact statement

```text
Artefact:      what exists at the end
Inspector:     who can check it, other than me
Bar:           what makes it pass (observable)
Date:          fixed
Out of scope:  what it need not include
```

Example: a service in Go with a public repository, tests, a container image and a README, deployed and answering requests, inspected by a colleague who writes Go; passes if it handles a failing dependency without crashing; by 30 June.

## Decomposition table

| Leaf (sub-skill) | Prerequisite | Know about or can do | Cold test (what I do, from blank, in what time) | Week |
| --- | --- | --- | --- | --- |
| Write and run a Go module with tests | none | can do | Create a module with one function and a table test in 20 minutes | 1 |
| Handle errors idiomatically | module basics | can do | Add error wrapping and a sentinel check to a function in 20 minutes | 2 |
| Concurrency with goroutines and channels | errors | can do | Fan out 10 jobs with a worker pool and collect results in 30 minutes | 4 |
| Why the scheduler behaves as it does | concurrency | know about | Not on the plan unless a test is defined | none |

A leaf that cannot be given a cold test is too vague. Split it until it can.

## Calendar-hours worksheet

| Week | Hours free on the calendar | Hours I will commit (lower figure) | Doing | Reading |
| --- | --- | --- | --- | --- |

Fill in the real free hours for the next four weeks from the calendar itself. Doing is at least four times reading. Recheck the figures at the checkpoint; if actual hours are well under committed, the plan is sized wrong, so cut leaves.

## Weekly cold-test log

| Week | Leaf tested | Time allowed | Result (pass or fail) | What failed | Next step |
| --- | --- | --- | --- | --- | --- |

A fail is information. Repeat the same test the next week with a changed method before moving on.

## Checkpoint decision table

At 25 per cent of the elapsed time:

| Cold tests passed | Decision |
| --- | --- |
| Under half | Change the method: build instead of read, get a reviewer, shrink the leaves, switch resource. Keep the hours. Re-test in two weeks. |
| Half or more | Continue; add a reviewer who can inspect work early. |
| Every test passed so far | Continue; consider whether the date can be brought forward or the artefact widened, and decide only after the next test. |

Write the decision and its date in the plan.
