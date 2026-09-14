# Reading a profile

A profile is a sample of stacks, not a recording of what happened. Read this file when you have one in front of you and want to know what it is entitled to tell you.

## Contents

- [Self time against cumulative time](#self-time-against-cumulative-time)
- [Flame graphs, and why they are not timelines](#flame-graphs-and-why-they-are-not-timelines)
- [How many samples is enough](#how-many-samples-is-enough)
- [Broken stacks](#broken-stacks)
- [Differential profiles for a regression](#differential-profiles-for-a-regression)
- [Off-CPU time and lock contention](#off-cpu-time-and-lock-contention)
- [Allocation profiles](#allocation-profiles)
- [Artefacts that look like findings](#artefacts-that-look-like-findings)

## Self time against cumulative time

Every profiler reports two numbers per frame, under varying names.

| Concept | Python `pstats` | Go pprof | async-profiler, perf | What it answers |
| --- | --- | --- | --- | --- |
| Time in this function's own code | `tottime` | flat | self | Which code is executing |
| Time in this function and everything it called | `cumtime` | cum | total | Which subsystem owns the cost |

Sort by self time to find the code to change. Sort by cumulative time to find the boundary to cut: a request handler with 80% cumulative and 0.2% self time is not slow, but everything below it is, and the useful question becomes whether that whole subtree needs to run.

The common misreading is a top-of-list entry with huge cumulative time — `main`, the event loop, the framework dispatcher — treated as a finding. It is the frame every other frame sits under, and it is true of every profile ever taken.

## Flame graphs, and why they are not timelines

In a flame graph the x-axis is the population of samples sorted alphabetically, and the y-axis is stack depth. Nothing about left-to-right means earlier or later.

- **Width is time.** A frame occupying a third of the width held a third of the samples.
- **Depth is only depth.** A tall narrow tower is a deep call chain that cost nothing.
- **The plateau is the answer.** Look for the widest frame that has no equally wide child; that is where the time is being spent rather than delegated.
- **An icicle graph** is the same thing drawn downward, which is the default in several browser tools. It reads identically.
- **A flame chart** is the one that is chronological, x-axis as elapsed time, and the two names are confusingly close. Chrome DevTools and Go's execution tracer produce charts; `perf`, py-spy and async-profiler produce graphs. Check which you have before drawing a conclusion about ordering.

Merge recursion before reading. Recursive frames spread one cost across many rows and a naive reading finds nothing above 2%.

## How many samples is enough

A sampling profiler at 99Hz collects roughly 99 samples per second per running thread. Over 30 seconds of a single busy thread that is about 3,000 samples, so a 1% frame is 30 samples and a 0.1% frame is three, which means nothing.

Rules of thumb worth applying literally:

- Under about 1,000 samples, believe only the top few frames.
- A frame below roughly 2% of a short profile is not a finding; it is the sampling equivalent of rounding error.
- A function that runs for 200µs once per request cannot be seen at 99Hz at all. Either raise the rate for a short window or measure it directly with a timer.
- Odd sampling rates such as 99Hz rather than 100Hz are deliberate: they avoid locking in step with a periodic task running at a round frequency and reporting it as constant load.

## Broken stacks

A profile with a large `[unknown]`, `??`, truncated or single-frame share is not telling you where time goes, and no percentage in it is trustworthy.

The usual causes: frame pointers omitted by the compiler, which is the default at `-O2` on many toolchains — rebuild with `-fno-omit-frame-pointer` or profile with `--call-graph dwarf`; a stripped binary with no symbols; a JIT that has not registered its generated code; a container without the debug symbols the profiler needs. Fix the stacks first. Everything else is guesswork until the stacks are whole.

## Differential profiles for a regression

When something got slower and you have a profile from before, do not read them side by side and try to hold both in your head. Take a differential: subtract the two profiles and render the delta, so frames that grew show up directly. `go tool pprof -base`, `perf diff` and differential flame graphs all do this.

Two cautions. Normalise to the same amount of work — comparing a 30-second profile against a 60-second one shows only that one is longer. And a frame that shrank in percentage terms may not have got faster; it may have kept its cost while something else grew around it. Compare absolute time per unit of work, not shares.

## Off-CPU time and lock contention

A CPU profiler samples threads that are running. A thread blocked on a lock, a socket, a disk read or a condition variable is invisible to it, so a program that spends its wall clock waiting produces a small, tidy, misleading profile.

The symptom is a wall clock much longer than the CPU time consumed. Check with `time` on a command, or the process CPU seconds against elapsed seconds for a service. When the gap is large:

- Use a wall-clock sampler that includes blocked threads: async-profiler `-e wall`, py-spy with idle threads included, or Go's execution tracer.
- Use an off-CPU profiler that records why the thread stopped: `perf sched`, the eBPF `offcputime` tool, Go's block and mutex profiles.
- Suspect the usual four in this order: a lock held across I/O, a connection or thread pool sized below the concurrency, a synchronous call on an event loop or async runtime, and a queue that is the actual bottleneck.

## Allocation profiles

Allocation is cheap per object and expensive in aggregate, and it shows up in a CPU profile as garbage collection or allocator frames rather than at the site responsible. An allocation profile attributes bytes and object counts to the stack that created them, which is what you need.

Read it by count as well as by bytes. A million 48-byte objects and one 48MB buffer are the same total and completely different problems: the first is a GC pressure problem fixed by allocating less in the loop, the second is one large allocation that probably belongs somewhere else.

This is about churn on a hot path. Memory that grows all day and is never released is a lifetime bug rather than a performance one, and it belongs to `debugging` — a retention question is answered by finding what still holds the reference, not by a profile of who allocated it.

## Artefacts that look like findings

- **The idle loop.** A wall-clock profile of a mostly idle service is dominated by the accept loop or the poller. Filter idle threads before reading.
- **`memcpy`, `malloc`, GC frames at the top.** Real, but the fix is at the caller allocating or copying, not in the allocator.
- **Startup cost.** A profile of a short run is mostly imports, class loading and JIT. Profile the steady state separately.
- **A frame that appears only after a tool change.** An instrumenting profiler inflates small, frequently called functions by its own per-call cost. Cross-check with a sampler before acting.
- **The profiler's own frames.** Several tools sample on a timer thread that shows up in the graph. Exclude it rather than explaining it.
