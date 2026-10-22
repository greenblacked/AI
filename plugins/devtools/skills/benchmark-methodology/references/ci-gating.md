# CI performance gates

## Contents

- Choose the metric
- Derive the threshold from A/A runs
- Compare against history
- Bootstrap interval sketch
- Handling a failure
- Checklist

## Choose the metric

| Metric | Stable on shared runners | Notes |
| --- | --- | --- |
| Wall-clock time | No | Neighbour load, frequency changes and cache state move it |
| CPU time | Somewhat | Still affected by frequency and cache contention |
| Instructions retired (`perf stat -e instructions`) | Yes | Needs access to hardware counters, often unavailable in virtualised runners |
| Simulated instruction and cache counts (cachegrind) | Yes | Slow, deterministic, ignores real cache and branch behaviour |
| Allocation count and bytes | Yes | Framework counters in Go benchmarks (`-benchmem`) and most allocator hooks |

Instruction counts do not capture a change that reduces cache misses without changing instructions; keep a wall-clock check on a quiet machine for that class, and be clear the CI gate does not see it. If hardware counters are unavailable in your runners, use the simulator or allocation counts.

## Derive the threshold from A/A runs

1. On the CI runners, run the unchanged main commit through the benchmark at least twenty times, on different runner instances where it can happen.
2. Record the metric for each run. For deterministic metrics the spread may be near zero; for others take the spread.
3. Set the failure threshold above the spread by a margin you can defend, for example the 99th percentile of the A/A relative deviation plus a margin, rounded up. Write the number and its derivation in the configuration comment.
4. Re-derive when the runner image, compiler or benchmark changes.

A threshold of "5 percent" taken from nowhere is either too tight (flakes) or too loose (misses regressions that matter). The derivation is the part a reviewer should read.

## Compare against history

Store each main-branch result with the commit. For a pull request, compare against the median of the last N main results (N around 10 to 20) rather than only its merge base run. Then:

- A step change appears as a result outside the rolling interval.
- Slow creep appears as a trend across the stored series; run a periodic check on the series (a changepoint or simple slope check) so a one percent per commit drift is caught.
- A single noisy baseline run cannot fail an unrelated pull request.

## Bootstrap interval sketch

```python
import random, statistics


def ratio_ci(a, b, n=5000, alpha=0.05, seed=1):
    rng = random.Random(seed)
    ratios = []
    for _ in range(n):
        ra = statistics.median(rng.choices(a, k=len(a)))
        rb = statistics.median(rng.choices(b, k=len(b)))
        ratios.append(rb / ra)
    ratios.sort()
    return ratios[int(n * alpha / 2)], ratios[int(n * (1 - alpha / 2)) - 1]
```

Feed it per-run timings from separate processes. Run it on an A/A pair too; the interval should straddle 1.0 and its width is the noise floor.

## Handling a failure

1. Rerun the failing job once on the same commit. If the metric is stable, a rerun giving a pass means the gate is flaky and its threshold needs the derivation above.
2. Bisect over commits with the same script when the failure is real and the culprit unclear.
3. If the regression is accepted, update the baseline in a commit that says why, so the history records the decision.

## Checklist

- Question and decision written down.
- Same compiler and flags for A and B.
- A/A run done and noise floor recorded.
- Separate processes, warm-up, interleaved order.
- Result reported as median ratio with interval and run count.
- Raw data and script committed.
- CI gate on a stable metric with a derived threshold and a history comparison.
