# Sharp-edge search

## Contents

- [Changelog reading](#changelog-reading)
- [Issue searches](#issue-searches)
- [Record format](#record-format)

## Changelog reading

Read twelve months of release notes in one sitting, newest first, and tag each entry:

| Tag | Meaning | Why it matters |
| --- | --- | --- |
| break | A change that needs action on upgrade | Tells you the upgrade cost |
| data | A fix for loss, corruption or wrong results | Shows which behaviours were unsafe until recently |
| perf | A fix for a slow path or a leak | Shows where performance cliffs were |
| deprec | Something scheduled for removal | Do not build on it |

A long run of data fixes in the area your requirement touches is a finding, not trivia. A
project with no changelog is also a finding.

## Issue searches

On GitHub, in the issue search box, with the repository filter:

- `is:issue is:open sort:comments-desc` for the longest open threads.
- `is:issue is:closed sort:comments-desc` for the problems that did get fixed, and the versions that fixed them.
- `is:issue <keyword from your hardest requirement>` such as `rebalance`, `timeout`, `corrupt`, `memory`.
- `is:issue label:bug is:open` where the project labels bugs, to count them against the age of the oldest.

Other trackers have equivalents; use whatever sorts by comment count. Also search the project's
discussion forum for the phrase "in production" and for the name of a larger tool you would run alongside.

## Record format

```text
Edge:     consumer group rebalance pauses all consumers
Evidence: issue link, comment count, versions affected
Affects:  our requirement of no processing gap longer than 5 seconds
Mitigation known? yes, option name, or no
```

A sharp edge without evidence is an opinion. A sharp edge with no stated effect on your
requirement goes at the bottom.
