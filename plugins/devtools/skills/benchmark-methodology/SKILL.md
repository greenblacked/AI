---
name: benchmark-methodology
description: "Designs a trustworthy benchmark comparing two implementations, libraries or configurations, and gates CI on it without flaking. States the question and decision, controls the machine (pinned cores, fixed governor), warms up, runs separate processes, consumes results so the compiler cannot delete the work, interleaves A and B, and reports a median with a bootstrap confidence interval, calling a difference only when it clears the noise floor from an A/A run. For shared CI runners it gates on a stable metric such as instruction counts, with a threshold from A/A variance. Use when someone asks \"is this faster than that\", \"benchmark A vs B\", \"my benchmark results are all over the place\", \"how many runs should I do\" or \"our benchmarks flake in CI\". Not for where time goes inside one program (profiling), build time (slow-build-profile), or pipeline structure (ci-pipeline-design)."
allowed-tools: "Read, Grep, Glob, Edit, Bash(go:*), Bash(benchstat:*), Bash(cargo:*), Bash(git:*)"
---

# Benchmark Methodology

Done means the question is answered with an interval rather than a single number, the interval is compared against a measured noise floor, and someone else can rerun the script on the stated machine and get the same answer.

A benchmark fails quietly. It returns a number every time, and the number is stable enough to look like data. The usual failure is a difference of a few percent between two runs of one binary being read as a result about two implementations. Machine state, layout, frequency scaling and run order all move timings by more than most changes are worth, so the method is mostly about removing or measuring those.

## Scope

Use for: comparing two implementations, libraries or settings; deciding whether a change regressed performance; building a benchmark suite; and adding a performance gate to CI that does not flake.

Do not use for: finding where the time goes inside one program (`profiling`), slow compiles (`slow-build-profile`), or how the CI pipeline is staged (`ci-pipeline-design`). A benchmark answers which is faster; a profile answers why.

## Workflow

### 1. State the question and the decision

Write one sentence: "Does B reduce p50 latency of operation X on input Y by at least Z percent, so that we adopt it." The decision fixes the input, the metric and the size of difference worth detecting. A benchmark with no decision attached gets run until it says something.

### 2. Control the machine

Differences you cannot control must at least be constant between A and B.

- Pin to specific cores (`taskset -c 2,3 command` on Linux) and keep other work off them.
- Fix the frequency governor to a constant setting where you have the rights (the `performance` governor), and disable turbo if repeatability matters more than peak speed. On a laptop, plug it in and let it cool.
- Use a quiet host: no browser, no indexer, no other build. On a cloud VM expect noisy neighbours and measure it (step 6).
- Build A and B with the same compiler, flags and optimisation level, from the same commit apart from the change under test.

### 3. Warm up inside each process, then sample many processes

Run enough untimed iterations for caches, the JIT and lazy initialisation to settle, and do it inside every process you sample from. Then take samples from many separate processes (forks), not many iterations inside one: memory layout, address randomisation, JIT compilation decisions and hash seeds vary per process, so a thousand iterations in one process measure that process's luck a thousand times. The opposite mistake is as common: on a JIT runtime a fresh process timed with no warm-up of its own measures cold start, which answers a different question.

Pick the tool by what is being compared:

- **JMH (JVM).** Each fork is a fresh JVM that warms up (`-wi` warm-up iterations) before its measured iterations (`-i`), and `-f` sets how many forks run. This is the right shape for code in a JIT runtime, because the fork gives independent compilation decisions and the warm-up keeps them out of the timings.
- **criterion (Rust).** Warms up (`--warm-up-time`) and samples inside one process, which suits ahead-of-time compiled code once it is warm. It does not vary layout between runs, so run the benchmark binary several times, alternating A and B, when the difference is small.
- **pytest-benchmark (Python).** Rounds run in one process after an optional warm-up (`--benchmark-warmup`). CPython has no JIT by default, but the hash seed varies per process, so repeat the whole run or fix `PYTHONHASHSEED` for both sides.
- **hyperfine (whole-process commands).** Right when the thing you ship is a process invocation (a CLI, a build step, startup time), because each run is a fresh process. `--warmup 3` makes untimed runs first so the file cache is warm; it does not warm a JIT inside the command, so do not use it for steady-state JVM or Node performance.

For hyperfine, `hyperfine --warmup 3 --runs 30 'cmd-a' 'cmd-b'` runs all of A and then all of B and does not interleave, so for the ordering in step 5 loop over single-command hyperfine runs in alternating order. Note that `go test -bench . -count=10` repeats each benchmark inside one test binary process, so it does not give per-process samples; for those, build the binary once with `go test -c` and run it N times in a loop, alternating A and B, then feed the outputs to `benchstat`.

### 4. Keep the work from being optimised away

Consume the result: write it to a sink the compiler cannot remove, return it from the benchmark function, or use the framework's black-box helper (Go's benchmark loop, Rust's `std::hint::black_box`, Google Benchmark's `DoNotOptimize`). A loop that reports 0.3 ns per operation has had its body deleted. Check also that the input is not constant-folded and that A and B do the same total work.

### 5. Interleave A and B

Alternate runs, A B B A A B B A, instead of all of A then all of B. Thermal state, background load and cache temperature drift over minutes, and running A first hands the other the drift. Some tools can randomise order for you, such as Google Benchmark's random interleaving option; otherwise write the loop.

### 6. Measure the noise floor with an A/A run

Run the identical binary as both A and B with the exact procedure above. The spread of the apparent difference is your noise floor on this machine at this time. A real A/B difference smaller than that is not a result, however many digits the output prints.

### 7. Report an interval, not a mean

Report the median of per-run values, with a bootstrap confidence interval for the median or for the ratio B/A (resample the runs with replacement a few thousand times and take percentiles). Means are dragged by outliers from a hiccup; the median is not. Call a difference only when the interval excludes the null (0 for a difference, 1.0 for a ratio B/A) and the effect also clears the A/A noise floor. `benchstat` does this for Go output; elsewhere a short script over exported timings (`hyperfine --export-json`) does. Say how many runs, and what the interval was, in the same sentence as the result.

### 8. Gate CI on a stable metric

Shared CI runners are noisy, so wall-clock time gates flake. Gate instead on a metric that is stable there: instruction counts (`perf stat -e instructions`, or a simulator such as cachegrind under `valgrind --tool=cachegrind`) or allocation counts. They do not move with neighbours' load.

Set the threshold from the A/A variance of that metric, measured on the same runners, not from intuition. Detect shifts across commit history (compare against a rolling baseline of recent main commits) rather than against the previous run only: a slow creep of one percent a commit passes every pairwise check and never trips. Keep wall-clock benchmarks for a quiet dedicated machine and a human reading the interval. `references/ci-gating.md` has the threshold derivation and the history comparison.

### 9. Publish enough to be rerun

Commit the benchmark script, the commands, the machine description (CPU model, cores, governor, OS, compiler version), and the raw timings, not only the summary. A result no one can rerun is an assertion.

## Hand back

The question and decision, the machine and controls, the A/A noise floor, the result as a median ratio with its interval and run count, the verdict against the decision threshold, and the paths of the script and raw data.

## Anti-patterns

**One mean from one run.** It has no spread, so nothing says whether the gap is a result.

**All of A, then all of B.** Drift becomes a difference between implementations.

**Many iterations in one process.** Layout and JIT luck repeat in every iteration.

**Gating CI on wall-clock time on shared runners.** The gate flakes, people learn to rerun it, and the gate stops meaning anything.

## Reference files

- `references/ci-gating.md` — read when setting up a CI performance gate, deriving a threshold from A/A variance, or comparing against commit history.
