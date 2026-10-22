# Observing the Go collector

Read this at step 1 when you have gctrace output or need to export runtime metrics.

## Reading a gctrace line

A line looks like:

```text
gc 12 @4.210s 2%: 0.020+1.4+0.003 ms clock, 0.16+0.5/2.6/1.1+0.024 ms cpu, 38->39->20 MB, 40 MB goal, 0 MB stacks, 0 MB globals, 8 P
```

- `gc 12`: cycle number.
- `@4.210s 2%`: time since start and the share of CPU the collector has used since the program began (a cumulative figure, so it smooths over spikes).
- The three clock numbers: stop-the-world sweep termination, concurrent mark, and stop-the-world mark termination. The pauses are the first and third.
- `38->39->20 MB`: heap at the start of the cycle, at the end, and live after marking. The last is the live heap that `GOGC` is relative to.
- `40 MB goal`: the heap goal for this cycle; collection starts somewhat below it.
- `8 P`: processors in use.

The exact field set varies between Go versions; check the runtime documentation for the version you run.

## What to extract

| Question | From |
| --- | --- |
| How often does it run? | Spacing between `@` timestamps |
| How large is the live heap? | Third number in the heap triple |
| How long are the pauses? | First and third clock figures |
| Is the limit biting? | Goal pinned at the limit with cycles back to back |

## runtime/metrics

Read the set with `metrics.All()` to see which names your Go version supports, and sample with `metrics.Read`. Useful names:

- `/gc/heap/live:bytes`, `/gc/cycles/total:gc-cycles`, `/cpu/classes/gc/total:cpu-seconds`
- `/memory/classes/total:bytes`: all memory mapped by the runtime
- `/gc/heap/goal:bytes`: the current heap goal
- `/sched/pauses/total/gc:seconds`: histogram of GC stop-the-world pauses (newer versions)

Derive the GC CPU share as the rate of `/cpu/classes/gc/total:cpu-seconds` divided by the rate of `/cpu/classes/total:cpu-seconds`.

## RSS versus runtime memory

Compare container RSS (`VmRSS` from `/proc/<pid>/status` or `anon` in the cgroup `memory.stat`; `memory.current` includes page cache) with `/memory/classes/total:bytes`. `/memory/classes/total:bytes` includes released heap memory, so compare RSS with that total minus `/memory/classes/heap/released:bytes`. A consistent gap is memory the runtime does not account for: cgo, mapped files, or the binary's own mappings. Size `GOMEMLIMIT` with that gap subtracted.
