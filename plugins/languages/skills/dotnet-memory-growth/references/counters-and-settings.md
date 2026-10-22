# Counters and settings

Read this at step 1 for how to interpret the counters, and at step 5 for the settings.

## Counters from System.Runtime

| Counter | Reading it |
| --- | --- |
| `gc-heap-size` | Managed heap in MB; take the minimum after Gen2 collections |
| `gen-0-gc-count`, `gen-1-gc-count`, `gen-2-gc-count` | Collections per interval; a Gen2 count that climbs steadily means frequent full collections |
| `loh-size` | Large object heap size; growth with flat `gc-heap-size` elsewhere points at big arrays |
| `alloc-rate` | Bytes allocated per second; high rate drives Gen0 frequency |
| `working-set` | Process physical memory; compare against `gc-heap-size` |
| `gc-fragmentation` | Fragmentation share on newer runtimes; high with a large LOH suggests fragmentation |

Counter names differ slightly across runtime versions; run `dotnet-counters list` to see what your runtime exposes.

## Reading together

`gc-heap-size` includes the LOH, so read the small-object heap as `gc-heap-size` minus `loh-size`, or use the per-generation size counters.

| Small-object heap low point | loh-size | working-set | Next |
| --- | --- | --- | --- |
| Rising | Flat | Rising | Managed leak: dump diff |
| Any | Rising | Rising | Large buffers: pool or stream |
| Flat | Flat | Rising | Native memory or GC retention |
| Flat | Flat | Flat | No leak; check sizing |

## Settings

Environment variables use the `DOTNET_` prefix (older `COMPlus_`). Values for numeric GC settings in environment variables are hexadecimal, with an optional `0x`; `runtimeconfig.json` values are decimal. A 70 percent limit is `DOTNET_GCHeapHardLimitPercent=0x46` or `"System.GC.HeapHardLimitPercent": 70`.

| Setting | Effect |
| --- | --- |
| `DOTNET_GCHeapHardLimit` | Absolute heap limit in bytes |
| `DOTNET_GCHeapHardLimitPercent` | Heap limit as a percentage of the physical or container limit |
| `DOTNET_gcServer` | 1 for Server GC, 0 for Workstation |
| `DOTNET_gcConcurrent` | Background (concurrent) collection on or off |
| `DOTNET_GCConserveMemory` | 0 to 9; higher values compact more to lower memory use at some CPU cost |

The same options can be set in `runtimeconfig.json` as `System.GC.Server`, `System.GC.Concurrent`, `System.GC.HeapHardLimit`, `System.GC.HeapHardLimitPercent` and `System.GC.ConserveMemory`. The environment variable wins over the file.

## Taking a dump safely

`dotnet-gcdump collect` pauses the process while it walks the heap; on a large heap do it on one instance taken out of rotation. Check disk space on the destination first.
