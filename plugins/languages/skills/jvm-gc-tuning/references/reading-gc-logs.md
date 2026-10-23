# Reading GC logs

Read this when you have a `gc.log` produced by `-Xlog:gc*,gc+heap=debug:file=gc.log:time,uptime` and need the four numbers from step 2.

## Lines to find

| Want | Look for | How to compute |
| --- | --- | --- |
| Pause p99 and max | Lines ending in a duration such as `Pause Young (Normal) (G1 Evacuation Pause) 612M->98M(1024M) 14.2ms` | Collect the durations by pause type and take the percentiles per type |
| Allocation rate | The "before" occupancy of one pause minus the "after" occupancy of the previous one | Divide by the uptime gap between the two |
| Promotion rate | Old generation occupancy growth across young collections | Divide by elapsed time; compare with what mixed collections reclaim |
| Live set | The "after" occupancy of a full collection or the lowest value after mixed collections | Take the minimum over a long window |

Each pause line reads `before->after(total)`. A steady "after" that creeps up between collections of the same kind is growth, not churn.

## Patterns and what they suggest

| Pattern | Likely cause | First move |
| --- | --- | --- |
| Full collections every few minutes, each freeing little | Live set close to the heap size | Raise the heap or find the retainer |
| Full collections freeing a lot | Old generation filling with short-lived objects (early promotion) | Cut large temporary allocations |
| Many young collections a second | High allocation rate | Allocation profile |
| `Humongous` allocations in a G1 log | Arrays at least half a region | Chunk or pool, or raise the region size with `-XX:G1HeapRegionSize` |
| `to-space exhausted` or `Evacuation Failure`, or a G1 `Pause Full (Allocation Failure)` | Collector fell behind the allocation rate | More headroom, lower the initiating occupancy, cut allocation |
| `Pause Young (Allocation Failure)` under Parallel or Serial | The normal trigger for a young collection, not a problem on its own | Judge by pause length and frequency instead |
| Long pauses with high system time | Swapping or page-fault cost | Check memory limits and swap |
| Long pauses with real time well above user plus sys | CPU throttling, a safepoint or an I/O stall (log device) | Check cgroup CPU throttling, move the log, check `safepoint` log tags |

## Live view without a restart

`jstat -gcutil <pid> 1000` prints occupancy percentages per region and cumulative collection counts and times each second. The ratio of the GC time column growth to wall-clock time is the GC share. `jcmd <pid> GC.heap_info` prints current occupancy by region.

## Caveats

Percentiles over a window containing a deploy or a warm-up are misleading; trim them out. Compare windows with similar request rates.
