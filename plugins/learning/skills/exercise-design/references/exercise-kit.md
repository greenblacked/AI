# Exercise kit

## Contents

- Directory layout
- Check-script skeleton
- Error-message checklist
- Common-mistake list format
- Cold-run log

## Directory layout

```text
exercise-name/
  README.md          the one thing, the task, the setup and check commands, stated time
  starter/           compiles and runs; the check fails here for the intended reason
  check.sh           or tests/ ; the learner-facing signal
  hints/
    1-nudge.md
    2-approach.md
    3-near-solution.md
  solution/
    code and EXPLANATION.md
  COMMON-MISTAKES.md
  reset.sh           for operations labs
```

## Check-script skeleton

A shell sketch for an operations lab: the learner rebases `feature` onto `main`. Replace the probes with the real condition. A check that tests only one fact, such as the current branch, is passed by a shortcut (merging instead, resetting to the base, or never starting), so test the state the task is meant to produce, and make each wrong move that satisfies one test fail another.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

branch="feature"
base="main"
feature_commits=3   # the number of commits the lab starts with on the branch

if ! git_dir="$(git rev-parse --git-dir 2>/dev/null)"; then
  echo "FAIL: this directory is not a Git repository. Change into the lab directory and run the check again."
  exit 1
fi

# Test the rebase-in-progress state first: mid-rebase, HEAD is detached and
# the branch name reads 'HEAD', which would give a confusing message below.
if [[ -d "$git_dir/rebase-merge" || -d "$git_dir/rebase-apply" ]]; then
  echo "FAIL: a rebase is still in progress."
  echo "Hint: resolve the conflicts and continue the rebase, then run this check again."
  exit 1
fi

actual="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$actual" != "$branch" ]]; then
  echo "FAIL: expected to be on branch '$branch' but found '$actual'."
  echo "Hint: switch back to '$branch', then run this check again."
  exit 1
fi

if ! git merge-base --is-ancestor "$base" HEAD; then
  echo "FAIL: '$branch' does not contain the latest '$base'; the rebase has not happened."
  echo "Hint: rebase '$branch' onto '$base'."
  exit 1
fi

# A merge satisfies the ancestor test too, so reject merge commits.
if [[ -n "$(git rev-list --merges "$base"..HEAD)" ]]; then
  echo "FAIL: '$branch' contains a merge commit; a rebase gives a linear history."
  echo "Hint: undo the merge and rebase '$branch' onto '$base' instead."
  exit 1
fi

# A hard reset to the base also satisfies the ancestor test, so require the work to survive.
count="$(git rev-list --count "$base"..HEAD)"
if (( count < feature_commits )); then
  echo "FAIL: expected at least $feature_commits commits on '$branch' beyond '$base' but found $count."
  echo "Hint: the rebase must keep your commits; see the lab's reset script to start again."
  exit 1
fi

# Conflict markers left in tracked files mean the resolution was not finished.
if git grep -qE '^(<<<<<<<|>>>>>>>) ' -- . 2>/dev/null; then
  echo "FAIL: conflict markers are still present in the tracked files."
  echo "Hint: run 'git grep -n \"^<<<<<<<\"' to find them."
  exit 1
fi

echo "PASS: '$branch' is rebased onto '$base' with its commits intact and no rebase in progress."
```

Properties to keep when adapting it: it names what was expected and what was found, says what to do next, exits non-zero on failure, and runs in a few seconds. For programming exercises, use the language's test runner with one assertion per behaviour and a message on each assertion.

## Error-message checklist

Make each likely mistake on purpose and read what comes out. For each message ask:

- Does it say what was expected and what was found?
- Does it name the file or line the learner should look at?
- Does it say what to do next, or point to the hint?
- Would a newcomer understand every word without searching?
- Is the real cause visible, or buried under a long stack trace? If buried, catch it and print a short message.

A raw tool error the learner cannot read is not necessarily yours to rewrite, but the exercise should say in COMMON-MISTAKES what that error means.

## Common-mistake list format

| Symptom the learner sees | Cause | What to do | Fixed in the exercise, or left as a normal wrong turn |
| --- | --- | --- | --- |

Source every row from the cold run first, then from the author's own deliberate mistakes. A list written from imagination misses the real ones.

## Cold-run log

| Time | Where they were | What they did | Stalled for | Hint opened | Cause | Change made |
| --- | --- | --- | --- | --- | --- | --- |

Total time, minus any setup time, is the number to double or adjust for the stated time. Setup that took longer than ten minutes is a defect in the setup, not in the learner.
