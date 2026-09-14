# Profiling Go and native code

Read this when the slow code is Go, Rust, C or C++, or when the language-level profiler has run out of answers and the question has become what the machine is doing.

## Contents

- [Go: pprof is built in, so wire it in before you need it](#go-pprof-is-built-in-so-wire-it-in-before-you-need-it)
- [Go: the execution tracer sees what pprof cannot](#go-the-execution-tracer-sees-what-pprof-cannot)
- [Go: benchmarks and comparing them honestly](#go-benchmarks-and-comparing-them-honestly)
- [Go: allocation, escape analysis and the two knobs](#go-allocation-escape-analysis-and-the-two-knobs)
- [perf at the system level](#perf-at-the-system-level)
- [Frame pointers and broken stacks](#frame-pointers-and-broken-stacks)
- [Hardware counters for a flat profile](#hardware-counters-for-a-flat-profile)
- [Rust and C++ specifics](#rust-and-c-specifics)

## Go: pprof is built in, so wire it in before you need it

Importing `net/http/pprof` for its side effect registers the profile handlers on the default mux. Do that on an internal listener, not a public one.

```bash
go tool pprof -http=:8080 "http://localhost:6060/debug/pprof/profile?seconds=30"   # CPU
go tool pprof -http=:8080 "http://localhost:6060/debug/pprof/heap"                 # live heap
go tool pprof -top -cum cpu.out                                                    # text, by cumulative
go tool pprof -list 'ParseLine' cpu.out                                            # per-line cost
```

Quote the URL: the query string contains characters the shell would otherwise interpret.

Five profiles are available and each answers a different question. `profile` is CPU time. `heap` is live objects, and `allocs` is everything ever allocated, which is the one for churn. `goroutine` is a count and a stack dump, which finds a leak of goroutines. `block` and `mutex` are off by default and are the pair that reveals waiting rather than working — enable them with `runtime.SetBlockProfileRate` and `runtime.SetMutexProfileFraction`, sampled rather than always on, because both cost something.

Go's CPU profiler samples at 100Hz, so the same arithmetic as any sampler applies: a 30-second profile of one busy goroutine is about 3,000 samples, and anything below a couple of percent is not a finding.

## Go: the execution tracer sees what pprof cannot

When the CPU profile is small but the latency is large, the answer is scheduling, not code.

```bash
curl -o trace.out "http://localhost:6060/debug/pprof/trace?seconds=5"
go tool trace trace.out
```

The tracer records goroutine creation, blocking, syscalls, GC and scheduler latency on a real timeline. The findings it produces are the ones no profile shows: goroutines runnable but not scheduled because `GOMAXPROCS` is wrong for the container, a chain of goroutines each waiting on the previous, or a garbage collection assist eating the request that triggered it.

`GOMAXPROCS` deserves a specific check. Go reads the machine's core count, not the container's CPU quota, so a pod limited to 1.5 cores on a 64-core node starts 64 Ps, and the resulting scheduling overhead and GC worker count are a real and frequently missed cost. Set it from the quota.

## Go: benchmarks and comparing them honestly

```bash
go test -run '^$' -bench 'ParseLine' -benchmem -count 10 ./... > new.txt
go test -run '^$' -bench 'ParseLine' -benchmem -count 10 -cpuprofile cpu.out ./parser
```

`-run '^$'` stops the unit tests running alongside the benchmark. `-benchmem` adds allocations per operation, which is usually the number that explains the time. `-count 10` produces a distribution instead of a point, and `benchstat old.txt new.txt` compares the two with a confidence interval — a benchstat result reporting no statistically significant difference is a result, and it is the honest answer for most micro-optimisations.

Assign the result to a package-level variable or use `testing.B`'s keep-alive conventions, or the compiler will delete the work being measured and report an implausibly fast number.

## Go: allocation, escape analysis and the two knobs

`go build -gcflags='-m' ./...` prints escape analysis decisions, which is how you find the value that became a heap allocation because it was captured by a closure or passed as an interface. Removing an allocation from a hot loop is worth more than it looks, because it removes GC work as well as the allocation.

Two runtime knobs, and they are not interchangeable. `GOGC` sets the growth ratio that triggers a collection; raising it trades memory for fewer cycles. `GOMEMLIMIT` sets a soft ceiling that makes the collector work harder as you approach it, which is what you want in a container with a hard memory limit. Setting `GOGC=off` with `GOMEMLIMIT` as the sole trigger is a real configuration, and one to state deliberately rather than drift into.

## perf at the system level

`perf` profiles anything on Linux, including code whose runtime has no profiler.

```bash
perf record -F 99 -g -p 1234 -- sleep 30   # sample a running process for 30 seconds
perf record -F 99 -g -- ./my-binary --input big.json
perf report --stdio --sort comm,dso,sym | head -40
perf script > out.perf                     # feed to a flame graph renderer or speedscope
```

It needs `kernel.perf_event_paranoid` low enough to permit sampling, and in a container the `CAP_PERFMON` or `CAP_SYS_ADMIN` capability plus access to the kernel symbol map. Arrange that before the incident rather than during it.

`perf` sees kernel frames as well as user frames, which is its advantage over every language profiler: a program spending its time in `copy_user_enhanced_fast_string` or a page fault handler is doing I/O or touching memory it did not expect to, and no user-space profiler will say so.

## Frame pointers and broken stacks

Optimised builds on many toolchains omit the frame pointer, and a sampling profiler that walks the stack by following frame pointers then produces stacks one frame deep. The symptoms are a flat profile with no call paths, or a large `[unknown]` share.

Three fixes, in order of preference: rebuild with `-fno-omit-frame-pointer`, which costs a register and a small percentage and is worth it on anything you intend to profile; use `perf record --call-graph dwarf`, which unwinds from debug information at a much higher recording cost and larger files; or use `--call-graph lbr` on Intel hardware that supports it, which is cheap and limited in depth. Keep debug symbols in release builds — in Rust, `[profile.release] debug = true` — so the stacks that are collected can be named.

## Hardware counters for a flat profile

When the profile is flat and the loop is already the right algorithm, ask what the CPU is waiting for.

```bash
perf stat -d ./my-binary --input big.json
```

Instructions per cycle below about one, with a high last-level-cache miss rate, means the program is waiting on memory rather than computing, and the fix is layout: contiguous arrays instead of pointer chasing, a smaller working set, fewer indirections per element. A high branch-miss rate on a tight loop points at an unpredictable condition, sometimes removable by sorting the input or making the branch arithmetic. Neither conclusion is reachable from a sampling profile, and both are wasted effort until a profile has already narrowed the work to one loop.

`perf annotate` then shows which instructions in that loop carry the samples, which is the last useful level of zoom before the answer becomes a rewrite.

## Rust and C++ specifics

Profile the release build with debug symbols; a debug build's numbers describe a program you do not ship. For microbenchmarks use a harness that defeats the optimiser — Criterion in Rust, Google Benchmark in C++ — and pass results through the harness's black box, because a compiler that can prove a result is unused will remove the computation entirely and report a nanosecond loop.

For exact call counts rather than time, `valgrind --tool=callgrind` simulates every instruction. The counts are exact and the timings are not, and it runs tens of times slower, so it suits a call-graph question on a small input rather than a latency question on a real one.
