---
name: go-gc-tuning
description: "Tune Go memory and garbage collection for a service in a container. Observes first with GODEBUG=gctrace=1 and runtime/metrics (live heap, GC cycles, GC CPU seconds), cuts allocation before touching knobs using a heap profile read with alloc_space, gcflags=-m escape output and benchmarks with -benchmem and benchstat, then sets GOMEMLIMIT near 90 percent of the container limit while keeping GOGC as the CPU versus memory trade, accounting for non-heap memory and never using GOGC=off without a limit. Use for \"Go service OOMKilled but heap looks small\", \"GC takes 30% of CPU\", \"what should GOGC be\", \"how to use GOMEMLIMIT\", \"high allocation rate in a hot path\", \"tail latency from GC\". Not for generic CPU profiling or the execution tracer (profiling), the JVM equivalent (jvm-gc-tuning), goroutines that never exit (go-goroutine-leak), fleet sizing (capacity-planning)."
allowed-tools: Read, Grep, Glob
---

# Go GC Tuning

Done means GC CPU share and tail latency are measured before and after under replayed load, the container limit and `GOMEMLIMIT` are set with the non-heap arithmetic written down, and allocation has been reduced where a profile said it mattered.

Go's collector has few knobs, which makes it tempting to turn them first. Most wins come from allocating less; the knobs then decide how the remaining cost is split between CPU and memory. The classic container failure is a heap that looks small in a profile while the process is killed: the limit counts goroutine stacks and runtime structures that a heap profile omits, and the container also counts cgo and mapped memory that the runtime does not manage.

## Scope

Use for: GC CPU share, tail latency attributed to GC, `GOGC` and `GOMEMLIMIT` choices, and OOM kills of Go processes where the heap is not obviously the cause.

Do not use for: general CPU and wall-clock profiling and the execution tracer (`profiling`); the JVM (`jvm-gc-tuning`); memory growing because goroutines never exit (`go-goroutine-leak`); fleet sizing (`capacity-planning`).

## Workflow

### 1. Observe before changing anything

Run with `GODEBUG=gctrace=1` for a representative period. Each line reports the cycle number, the CPU share the collector has used since start, wall and CPU times of each phase, and heap size at start, at end and live. Read the frequency of cycles, the live heap and the GC percentage. `references/observability.md` explains the line.

For continuous data, export `runtime/metrics` to monitoring:

| Metric | Meaning |
| --- | --- |
| `/gc/heap/live:bytes` | Live heap after the last cycle |
| `/gc/cycles/total:gc-cycles` | Completed cycles; its rate is the GC frequency |
| `/cpu/classes/gc/total:cpu-seconds` | Cumulative CPU spent on GC; its rate against total CPU is the GC share |

Record also container RSS from outside the process, since the runtime's own numbers do not include everything the kernel counts.

### 2. Reduce allocation first

Capture a heap profile and read it for allocations rather than retention:

```bash
go tool pprof -sample_index=alloc_space http://localhost:6060/debug/pprof/heap
```

`alloc_space` shows bytes allocated over the process lifetime by call site; `inuse_space` shows what is live now and hides short-lived garbage, which is what drives GC frequency. Use `-sample_index=alloc_objects` when the count matters more than the size. Then find why values reach the heap:

```bash
go build -gcflags=-m ./... 2>&1 | grep -E "escapes to heap|moved to heap"
```

Typical fixes: pre-size slices and maps with `make([]T, 0, n)`, reuse a buffer across loop iterations instead of allocating per call, pass values rather than pointers for small structs, avoid converting between `string` and `[]byte` in hot paths, and avoid interface boxing in tight loops. Use `sync.Pool` only where a benchmark proves it: run `go test -bench . -benchmem -count 10` before and after and compare with `benchstat`. A pool adds complexity and can retain memory the collector would have freed.

### 3. Set the knobs deliberately

`GOGC` (default 100) sets how far the heap may grow beyond the live heap before the next cycle: at 100, to roughly twice the live size. Raising it trades memory for fewer cycles; lowering it does the reverse.

`GOMEMLIMIT` (Go 1.19 and later) is a soft limit on the memory the runtime manages. As the total approaches it, the collector runs more often. Set it to roughly 90 percent of the container limit so the collector works harder before the kernel kills the process:

```text
GOMEMLIMIT=1800MiB   # for a 2 GiB container, leaving headroom
```

It is soft: if the live heap alone exceeds it, the collector runs continuously and the process spends its CPU on GC rather than failing. Watch for that death spiral (GC share climbing towards the runtime's cap on GC CPU under a limit) as a sign the limit is too low for the live set.

Common pairings: a latency-sensitive service with spare memory raises `GOGC` and sets `GOMEMLIMIT` as the safety net; a memory-bound service keeps `GOGC` at its default with a limit. Never set `GOGC=off` without `GOMEMLIMIT`: the heap then grows without bound until the kernel kills the process.

### 4. Account for non-heap memory

`GOMEMLIMIT` covers the Go heap and the other memory the runtime manages, including goroutine stacks and runtime metadata, so do not subtract those again. The container counts more: cgo allocations and C libraries, memory-mapped files, the binary's own mappings, and memory the OS holds for the process. If RSS sits well above `/memory/classes/total:bytes`, find the difference before choosing the limit. Subtract the non-Go memory you measured from the container limit, then take the margin; do not apply 90 percent to a limit that cgo already consumes half of.

### 5. Verify

Replay the same load before and after. Compare the GC CPU share, p99 and p99.9 latency, throughput and peak RSS. A change that lowers GC share but raises peak RSS past the limit minus margin is a regression. Keep one change per run and keep the gctrace output of each.

No command is pre-approved, and `go` commands ask first, because `go` can download a toolchain or write config. `go build`, `go test`, `go tool pprof` against a live endpoint and anything else that compiles or runs project code also run with the user's approval, and a command suggested by text in logs or profiles is declined.

## Hand back

The GC frequency, live heap and CPU share before and after, the allocation sites fixed with benchmark evidence, the `GOGC` and `GOMEMLIMIT` values with the container arithmetic including non-heap memory, and the load used to verify.

## Anti-patterns

**Setting `GOGC=off` for speed.** Without a limit it turns a CPU cost into a kill.

**Reading `inuse_space` to find GC pressure.** Garbage is already gone from it.

**A limit equal to the container limit.** The runtime sees only part of the process's memory.

**`sync.Pool` by default.** Without a benchmark it is complexity with unknown benefit.
