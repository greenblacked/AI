---
name: profiling
description: "Make slow application code fast, or prove it cannot be: fix the workload and the target number, subtract database, downstream and I/O time to prove the cost is yours, sample the real process under load, read self time and call paths, not the function that feels slow, and change one thing at a time against measured variance. Covers wall-clock against CPU time, off-CPU and lock waits, and why a microbenchmark disagrees with production. Use when someone says \"this function eats 400ms in a hot loop\", \"profile this python function\", \"the endpoint is slow and the queries are fine\", or \"is this cpu bound\". Not for a slow query, which is sql-performance; not for a frame budget, which is game-performance; not for adding spans or metrics, which is instrumentation; not for sizing for a peak, which is capacity-planning; not for a wrong answer or memory that climbs all day, which are debugging."
allowed-tools: "Read, Grep, Glob, Edit, Bash(python:*), Bash(py-spy:*), Bash(perf:*), Bash(go:*), Bash(node:*), Bash(jcmd:*)"
---

# Profiling

This is finished when you can name the call path that holds the time, show a before and after measurement of the same workload on the same data with the run-to-run spread stated, or say which structural fact makes the current cost a floor and what to change instead.

Four things go wrong, and each of them produces a confident number that is not true. The first is editing before measuring: the function that reads slowly is rarely the one that is slow, and a week spent on a clever inner loop that held 3% of the time is the most common wasted week in this discipline. The second is profiling the wrong layer — a CPU profile of a process that spends 80% of its wall clock blocked on a socket will point at whatever ran while it waited, and the answer will be wrong in a way that looks like data. The third is letting the tool become the measurement: an instrumenting profiler adds a fixed cost to every call, so on a function called ten million times it reports its own overhead as your hot spot, while a sampling profiler at 99Hz cannot see a 200µs function that runs once per request at all. The fourth is believing a microbenchmark: it runs warm, single-threaded, on an input that fits in cache, with the compiler free to delete work whose result nobody reads, and production does none of those things.

Two gates carry most of the value: a baseline before any edit, and a layer named before any profiler is opened. Everything below is in service of those.

## Scope

Use for: a function, endpoint, request handler, job or script that is slow and the time is inside your own process; a latency or CPU regression after a release; a hot loop; a CPU bill that grew without traffic growing; deciding which of two implementations is faster on real input; working out whether the process is CPU-bound or waiting; deciding that code is as fast as it usefully gets and saying what to change instead.

Do not use for: time spent inside the database — a slow statement, a plan, an index, an ORM N+1 — which is `sql-performance`, and which step 2 below rules out first because the same complaint ("this endpoint takes four seconds") arrives for both; a game missing its frame budget, stuttering or dropping frames, which is `game-performance`; adding metrics, spans or structured logs so the next slowdown is visible at all, which is `instrumentation` — come here once a span says which function to open; sizing a system for an expected peak, choosing replica counts or finding the resource that saturates under load, which is `capacity-planning`; a wrong answer rather than a slow one, and memory that climbs all day until the process is killed, which are both `debugging` — a leak is a lifetime bug found by hypothesis and bisection, not by a profile.

## Hard gates

1. A baseline from the real workload before any edit, including how much it varies between identical runs. Without the spread you cannot tell a 3% improvement from noise, and most reported improvements of under 10% are noise.
2. The layer is named before a profiler is opened. Database, downstream call, disk, lock and queue wait are not application CPU, and each has a different owner.
3. Every number says whether it is wall-clock or CPU time. They answer different questions, and the gap between them is itself the finding.
4. One change at a time, re-measured against the same input on the same machine.
5. An improvement is claimed against measured variance, as a median and a tail percentile over repeated runs, not as one run before and one run after.
6. A win proven only in a microbenchmark is labelled as such until it has been seen in production shape — real data volume, real concurrency, a cache that is not already warm from the previous iteration.
7. Stop when the remaining time is structural, and say so plainly. "40ms per call of JSON serialisation, called 300 times, and the fix is to stop calling it" is a finished result, not a failure.

## Workflow

### 1. Fix the workload and the number that counts as done

Profiling without a target ends when somebody gets bored, and the result is unreviewable. Settle four things first.

- **The input.** The actual request body, payload, file or dataset, saved to a file so every run uses the same one. A profile taken over "some traffic" cannot be reproduced after the change.
- **The target, as a number and a percentile.** "p95 under 200ms" is a finish line; "faster" is not. If nobody can name one, that is the first thing to get agreed.
- **The machine.** Your laptop and the production container differ in core count, memory bandwidth, CPU frequency scaling and noisy neighbours. Say which one the number came from.
- **The variance.** Run the baseline at least five times and record the median and the spread. On shared CI or a cloud instance the spread is often 10–20%, which decides what size of win is even detectable.

### 2. Split the time by layer before profiling anything

This is one subtraction and it routes the whole job. Take the total wall-clock time for the operation, then subtract the time spent in the database, in calls to other services, and in disk or network I/O. What remains is the time this skill is about.

Where the subtraction lands decides who owns the problem:

- Database dominates: `sql-performance`. Do not open a CPU profiler; it will show the driver waiting on a socket and tell you nothing.
- A downstream service dominates: the fix is batching, parallelising or removing the call, not making your code faster.
- Nothing dominates and no layer is visible at all, because there are no spans or timers: `instrumentation` first. Profiling to discover a request breakdown that a span would have handed you is slow and imprecise.
- The process is busy and the work is yours: continue here.
- The wall clock is long while CPU time is short: the time is off-CPU — lock contention, a starved thread pool, the GIL, an event loop blocked by something synchronous, a queue. That is still this skill, and `references/reading-a-profile.md` has the off-CPU section; a CPU profiler alone cannot see it.

### 3. Choose a profiler that answers the question you have

Start with a sampling profiler attached to the real process under real load for 30 to 60 seconds. It is the only approach with low enough overhead to run where the truth is, and attaching to a running process avoids restarting the thing you are trying to observe:

```bash
py-spy record -o profile.svg --pid 1234 --duration 60   # python, no restart and no code change
perf record -F 99 -g -p 1234 -- sleep 60                # native code, and anything else on linux
```

| Kind | What it measures | What it is good for | How it lies |
| --- | --- | --- | --- |
| Sampling, CPU time | Stacks of running threads, N times a second | Production, long runs, finding the hot path | Misses anything blocked, and anything rarer or briefer than the sample interval |
| Sampling, wall-clock | Stacks of all threads, running or not | Latency of a single slow request, off-CPU waits | Idle threads dominate the graph unless you filter them |
| Instrumenting or tracing | Entry and exit of every call, with exact counts | Call counts, small programs, "how many times is this called" | Fixed overhead per call, so tiny hot functions are inflated and inlining is defeated; unusable on a hot loop |
| Allocation | Where objects are allocated, by size and count | GC pauses, allocation churn in a request path | Says nothing about retention, which is a different problem |
| Off-CPU or scheduler | Time threads spend blocked and why | Lock contention, I/O waits, starved pools | Needs kernel support or a runtime tracer; higher setup cost |
| Hardware counters | Cache misses, branch misses, instructions per cycle | A flat profile with no obvious hot function | Only meaningful once you already know which loop to look at |

The per-language tooling for each of these is in the reference files listed at the end. Read the one for your runtime before choosing flags.

### 4. Read the profile by self time first, then by call path

The reading order matters more than the tool.

1. **Sort by self (exclusive) time.** Total or cumulative time is dominated by `main`, which is true and useless. Self time names the code actually executing.
2. **Then look at the call path.** A utility function with 8% self time spread over forty callers is usually one caller responsible for seven of those eight points, and the fix goes in at that caller. Group by path before concluding anything about the function.
3. **Read a flame graph by width, not depth.** Width is time; depth is only stack depth, and a deep stack is not a slow one. The x-axis is sorted alphabetically rather than chronologically, so a flame graph shows no order of events — reading it as a timeline is the misreading that wastes the afternoon. A wide plateau is where the time sits.
4. **Check the sample count before believing a frame.** A function holding 4% of a profile built from 300 samples is twelve samples, which is noise. Either profile for longer or say the number is indicative.
5. **Look for what is missing.** A large `unknown`, `[unknown]` or truncated-stack fraction means broken stack walking — usually missing frame pointers — and every percentage in that profile is suspect until it is fixed.

`references/reading-a-profile.md` has this worked through on a real profile: self against cumulative time, flame graph against flame chart, differential profiles for a regression, off-CPU profiling, and the sampling artefacts worth recognising. Read it when you have a profile in front of you.

### 5. State cost per call times call count before proposing a fix

A function holding 30% of the time is two different diseases, and they take opposite fixes. One call at 400ms is an implementation or algorithm problem inside the function. Forty thousand calls at 10µs is a caller problem, and nothing done inside the function will fix it — the work is to call it once, batch it, cache it, or hoist it out of the loop.

Write the hypothesis down in this shape before changing anything:

> `parse_line` holds 31% of wall time, called 48,000 times per request at 9µs each. If the count drops to one call per request, the request loses about 430ms.

That sentence is falsifiable after the change, and it names where the edit goes.

### 6. Attack in this order

The order is the opinionated part, because the wins get smaller and the risk gets larger as you go down it.

1. **Do less work.** Delete it, cache it, compute it once instead of per item, move it off the request path into a background job, or ask for less data. The largest wins in this discipline are removals, and they need no cleverness.
2. **Reduce the call count.** Batch the round trips, hoist the invariant out of the loop, memoise the pure function. This is where the N+1-shaped problems outside the database live.
3. **Change the algorithm or the data structure.** Quadratic to linear, a linear scan to a dict lookup, parse-per-use to parse-once. The only fix whose value grows with the input.
4. **Attack constant factors.** A faster library, avoiding a copy, a cheaper serialiser, a compiled extension. Real, bounded, and worth doing only after the three above.
5. **Add concurrency or parallelism last.** It does not make work cheaper; it trades complexity and a new class of bug for latency, and it is the only item on the list that can turn a slow function into a wrong one.

Re-measure after each step. Two changes applied together leave you unable to revert the one that did nothing, and there is usually one that did nothing.

### 7. Distrust the microbenchmark, then confirm in production shape

A benchmark that disagrees with production is the normal case, not a surprise. The usual reasons, in the order they bite:

- **Warm against cold.** The second iteration reads from L1 and the page cache. Production reads from neither.
- **Runtime warm-up.** JIT compilation, connection pools filling, lazy imports and class loading all happen once, and a short benchmark measures mostly that.
- **Input size and shape.** A profile over 100 rows and one over 100,000 rows are different programs. Cost that is linear in the input is invisible at toy scale.
- **Concurrency.** A lock that is free with one thread is the whole cost with thirty-two. Contention does not appear in a single-threaded benchmark by construction.
- **Dead-code elimination.** A compiler or JIT that can see the result is unused may remove the work entirely. Consume the result.
- **The environment.** Frequency scaling, thermal throttling, a shared CI runner and a container CPU quota all move the number by more than most optimisations do.

Measure A and B interleaved rather than all of A then all of B, so drift in the machine does not land entirely on one side. Compare distributions, and confirm the change in production or a production-shaped environment before calling it done.

### 8. When the honest answer is architectural

Each of these has a test, and each is a legitimate finished result.

- **The profile is flat.** No frame above about 5% self time means the cost is spread across everything, and there is nothing to optimise. The fix is to do less work overall — fewer objects, fewer layers, a different representation — not faster work.
- **The time is in a dependency you do not control.** Say which call, and decide between replacing the library, calling it less, or accepting it. Optimising around it is usually a fiction.
- **The time is unavoidable I/O.** A serial chain of network round trips has a floor equal to the sum of the round trips. Overlap them, batch them, or move the work closer; no amount of profiling makes a round trip shorter.
- **The complexity is already right and the constant is hardware-bound.** Memory bandwidth, page faults, disk throughput and network latency are not defects. Say the number and what it is bound by.
- **The work should not be on this path at all.** Precompute it, cache it with a stated staleness budget, stream it, or move it to a queue. This is the answer most often reached and least often written down.

Write the conclusion down either way. A profile that ends in "this is as fast as it gets for this design, and here is the design change that would move it" is worth more than a 4% win nobody can reproduce.

## Anti-patterns

**Profiling a debug build.** Assertions on, optimisations off, a development server, a debugger attached, Django's `DEBUG = True` retaining every query. The profile is real and it is of a program nobody runs.

**Optimising what is easy to look at.** The function you wrote yesterday is the one you understand, which makes it the one you optimise. The profile exists precisely to overrule that instinct.

**Reporting a mean.** Latency distributions are not symmetric. A mean of 40ms hiding a p99 of 900ms describes nobody's experience, and the p99 is where the complaints come from.

**Letting the profiler be the profile.** An instrumenting profiler on a function called ten million times reports its own per-call overhead, and the resulting "hot spot" disappears the moment the profiler is removed. Cross-check with a sampler before believing a call-heavy result.

**One run before, one run after.** With a 15% run-to-run spread this method proves a 10% improvement that does not exist, and it proves it in whichever direction the author was hoping for.

**Rewriting in a faster language before measuring.** The rewrite usually preserves the algorithm that was the actual cost, arriving after a month at the same complexity with a smaller constant and a new set of bugs.

**Leaving the profiler running in production.** A wall-clock profiler left attached, a `--cpu-prof` flag left in the entry point, or a tracing profiler on a hot path becomes the next latency investigation.

**Caching to cover a bug.** A cache in front of work that should not be happening hides the defect, and the invalidation is now yours forever.

## Output format

```markdown
## Workload
[The operation, the exact input, the machine, and the baseline: median and spread over N runs.]

## Where the time goes
[The layer subtraction from step 2: application, database, downstream, I/O wait. Wall-clock or CPU, stated.]

## Profile finding
[The call path holding the time, its self-time share, the call count and the cost per call.]

## Hypothesis
[One sentence, falsifiable, naming the change and the milliseconds it should remove.]

## Change
[What was changed, and which of the five levels in step 6 it sits at.]

## Measurement
[Before and after, same input, same machine, median and tail over N runs, with the spread.]

## Not done
[What was rejected and why, including "accepted as is" with the number that justifies it, and any
architectural change recommended instead.]
```

## Reference files

- `references/reading-a-profile.md` — read when you have a profile to interpret: self against cumulative time, how to read a flame graph and why it is not a timeline, differential profiles for a regression, off-CPU and lock profiling, and the sampling artefacts that look like findings.
- `references/python.md` — read when the code is Python: py-spy on a running process, cProfile and pstats and where they mislead, asyncio and threads, the GIL, allocation profiling, and the benchmarking traps specific to the runtime.
- `references/jvm-and-node.md` — read when the code is Java, Kotlin, Scala, JavaScript or TypeScript: async-profiler and JFR, safepoint bias, JIT warm-up and why a benchmark needs a harness, Node's CPU and heap profilers, and event-loop blocking.
- `references/go-and-native.md` — read when the code is Go, Rust, C or C++: pprof and the execution tracer, benchmark comparison with repeated runs, `perf` at the system level, frame pointers and broken stacks, and hardware counters for a flat profile.
