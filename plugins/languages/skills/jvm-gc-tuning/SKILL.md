---
name: jvm-gc-tuning
description: "Diagnose and tune JVM garbage collection pauses and heap sizing. Turns on unified GC logging first (-Xlog:gc*,gc+heap=debug) and reads four numbers: pause p99 and max, allocation rate, promotion rate and live set after a full or mixed collection. Sizes the heap from the live set, expresses it with MaxRAMPercentage inside the container, cuts allocation and premature promotion in code before touching the collector, and picks G1 or ZGC from a stated goal without hand-sizing the young generation. Verifies on replayed load, allowing for JIT warm-up. Use for \"long GC pauses\", \"G1 versus ZGC\", \"what Xmx in Kubernetes\", \"full GC every few minutes\", \"latency spikes after a deploy\", \"high allocation rate\". Not for OutOfMemoryError and which region failed (jvm-oom-triage), CPU time hotspots (profiling), fleet sizing (capacity-planning)."
allowed-tools: Read, Grep, Glob
---

# JVM GC Tuning

Done means pause times meet a stated goal under replayed production-shaped load, the heap is sized from a measured live set with the container arithmetic written down, and any collector change traces back to a goal rather than a preference.

The usual failure is changing flags before measuring. A long pause has several different causes: a heap too small for the live set, an allocation rate that forces constant collection, objects promoted too early, humongous allocations, or a collector mismatched to the goal. Each has a different fix, and the flag lists copied from old blog posts address none of them reliably.

## Scope

Use for: pause times, GC CPU share, heap sizing and collector choice on a JVM service.

Do not use for: an `OutOfMemoryError` or a container kill with no Java error (`jvm-oom-triage`); finding the method that burns CPU (`profiling`); how many instances a fleet needs (`capacity-planning`).

## Workflow

### 1. State the goal

Write down one sentence before measuring: for example "p99 request latency under 200 ms with GC contributing less than 20 ms of it", or "maximise throughput; pauses up to a second are fine". The goal decides the collector later. Without it, tuning has no end.

### 2. Measure with unified logging

Add GC logging and leave it on; it is cheap enough for production:

```text
-Xlog:gc*,gc+heap=debug:file=gc.log:time,uptime
```

Put the file on a volume that survives restarts, and rotate it with the `filecount` and `filesize` output options. `references/reading-gc-logs.md` has what to extract. Read four numbers from a representative window:

1. Pause p99 and maximum, split by cause (young, mixed, full, remark, allocation failure).
2. Allocation rate: heap growth between collections divided by the time between them.
3. Promotion rate: bytes surviving into the old generation per second.
4. Live set: occupancy immediately after a full or mixed collection, the floor the heap never drops below.

`jstat -gcutil <pid> 1000` gives a quick live view of occupancy and collection counts when you cannot restart.

### 3. Size the heap from the live set

A heap commonly needs three to four times the live set so the collector has room to work; much less and collections become frequent and eventually full. Check the sizing against the log before changing it: a full collection that frees little means the heap is too small or something retains data (hand that to `jvm-oom-triage`).

In a container, set the heap as a fraction of the limit rather than a fixed `-Xmx` that drifts from it:

```text
-XX:MaxRAMPercentage=70
```

The default is 25, which wastes memory on a dedicated container. Leave room for what is outside the heap: Metaspace, thread stacks, the code cache, direct buffers and GC structures. Seventy is a starting point for a small service, not a rule; a service with many threads or large direct buffers needs more headroom, and `-XX:NativeMemoryTracking=summary` with `jcmd <pid> VM.native_memory summary` shows what it actually uses. Set `-Xms` equal to `-Xmx` only when you want the footprint committed up front.

### 4. Reduce allocation and early promotion in code

Cheaper than any flag: allocate less. Take an allocation profile (see `profiling` for the procedure; Java Flight Recorder's allocation events work) and look for per-request copies, boxing in hot loops, string building, large temporary collections and fetching whole result sets. Premature promotion shows as old-generation growth that falls at the next mixed or full collection; the usual causes are large per-request buffers and caches that hold short-lived entries. In G1, humongous allocations (objects at least half a region) go straight to the old generation, so a log full of humongous allocations means large arrays that should be chunked or pooled.

### 5. Change the collector last, from the goal

| Goal | Collector | Notes |
| --- | --- | --- |
| Throughput, pause goal in the hundreds of milliseconds | G1 (the default on server-class machines) | Set `-XX:MaxGCPauseMillis` as a target, not a guarantee |
| Pauses well under 10 ms on a large heap, with spare memory and CPU | ZGC | Generational mode: `-XX:+UseZGC -XX:+ZGenerational` on JDK 21; it is the default mode from JDK 23 |
| Small heap, single core, batch | Parallel or Serial | Lower overhead, long pauses accepted |

Do not set `-Xmn`, `-XX:NewSize` or `-XX:NewRatio` under G1: fixing the young generation size disables the adaptive sizing that meets the pause target. Change one thing per run and keep the log of each. `references/collector-choice.md` has the trade-offs and the flags worth knowing per collector.

### 6. Verify on the same load

Replay the same load shape before and after, and compare the pause distribution, GC CPU share, throughput and p99 latency, not the average pause. Discard the first minutes after a restart: JIT compilation and class loading distort allocation and latency until the process warms up, and a comparison that includes them favours whichever run was warmer. Keep the change only if the goal from step 1 is met; otherwise revert it and record what was learned.

## Hand back

The goal, the four numbers before and after, the heap sizing arithmetic including non-heap headroom, each flag changed and why, the collector decision tied to the goal, and the load used for verification.

## Anti-patterns

**Copying a flag list.** Flags tuned for another JVM version, heap and workload often disable adaptive behaviour the current collector would have used.

**Tuning the young generation under G1.** It trades the collector's self-correction for a fixed guess.

**Judging by average pause.** Users feel the tail; read p99 and the maximum by cause.

**Comparing a cold run to a warm one.** Warm-up effects look like a collector difference.
