# Build timing record: <project, date>

<!-- One document per slow-build investigation. Fill it in from the skill's Hand back section. -->

## Machine, toolchain and commit

Machine (cores, memory, disk), toolchain versions, the commit measured, and whether the
working tree was clean.

## Baseline and final timings

Median of three runs each, with the spread across the three.

| Build | Before median | Before spread | After median | After spread |
| --- | --- | --- | --- | --- |
| Clean | | | | |
| Incremental (one file touched) | | | | |
| No-op | | | | |

## Profile evidence

One entry per change: the profiler command and what it showed.

## Changes in order

Each change with its own before and after number.

## Largest remaining cost

What the profile now shows, and the recommendation.

## Not measured

What this investigation did not time, and why.
