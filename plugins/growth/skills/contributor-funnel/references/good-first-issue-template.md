# Good first issue template

Read this at step 3, when curating or writing the labelled issues.

## Contents

- Template
- Selection rules
- Keeping the list alive

## Template

```text
Title: one change, in plain words

What and why: two sentences on the behaviour that is wrong or missing.
Where: the file or module to start in, with a link.
Done when: the observable result, and the test that should pass or be added.
How to check: the exact command to run locally.
Not in scope: what to leave alone.
Ask here: the name of a maintainer who answers questions on this thread.
```

## Selection rules

- Small enough to finish in a few hours by someone new to the codebase.
- Needs no design decision; if it does, make the decision first and write it in the issue.
- Touches code covered by tests, so a newcomer gets a clear pass or fail.
- Not urgent. An issue a maintainer needs this week is not a good first issue.
- One person per issue: ask contributors to say they are taking it, and release it after a stated period of silence.

## Keeping the list alive

Review the label monthly. Close what has been fixed elsewhere, relabel what turned out to be hard, and keep roughly five open. When a pull request merges, the author's second task comes from this list or from a slightly larger issue in the same area.
