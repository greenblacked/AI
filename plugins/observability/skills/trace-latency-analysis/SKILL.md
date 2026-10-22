---
name: trace-latency-analysis
description: "Use traces to explain where a slow request or percentile spent its time: compare cohorts rather than reading one trace (slowest 1% against the median, split by version, region, tenant tier, payload size or cache hit), then budget one slow trace by hop - self time is parent duration minus the union of child intervals, gaps mean queueing or pool starvation, identical short siblings mean an N+1, fan-out tail compounds as 1-(1-p)^N, children before the parent mean clock skew - and end with a table of hop, share and next measurement. Use for \"why is p99 checkout 4 seconds\", \"read this trace and tell me where the time went\". Not for CPU time in one process (profiling), slow queries (sql-performance) or raw bundles (telemetry-reader)."
allowed-tools: Read, Glob, Grep
---

# Trace Latency Analysis

This skill is done when you can name the hop, or the attribute value, that accounts for the extra time in the slow requests, with numbers from traces, and the next measurement that would confirm the cause is written down.

The usual failure is reading one trace. The slowest trace in the window is chosen because it is the slowest, and it contains the explanation for that request only: a garbage collection pause, a cold cache, a retry. The slow percentile is a population, and the useful question is what the slow members have in common that the median ones lack. Compare cohorts first; open a single trace only to work out the mechanism once the cohort has told you where to look.

## Scope

Use for: a slow percentile on a route, a request that sometimes takes far longer than usual, a trace with a large gap or a wide span, a regression after a release, tail latency in a fan-out.

Do not use for: CPU time inside one process (`profiling`), a slow database statement once the trace has pointed at it (`sql-performance`), reading a large raw trace bundle, which `telemetry-reader` does.

## Workflow

### 1. Compare cohorts

Fix the route and the time window. Take two samples from the same window: the slowest 1% by duration and the median band (for example, the 45th to 55th percentile). Group both by each span or resource attribute you have: service version, region or zone, tenant tier, payload size bucket, cache hit or miss, feature flag, instance. The attribute whose share differs most between the cohorts is the lead. A version that makes up 5% of the median band and 70% of the slow tail is a regression; a region at 90% of the tail is a placement or dependency problem; a payload bucket is a size effect.

If no attribute separates them, the cause is probably random per request (a retry, a pause, a lock), which the hop budget in Step 3 will show. If the traces have too few attributes to group by, say that, and name the attributes to add before the next round.

Check that the sample is large enough. Fifty slow traces support a ranking; five support a hypothesis.

### 2. Check the trace is trustworthy

Before arithmetic, confirm the structure. A child that starts before its parent, or ends after it, is clock skew between hosts; durations measured within one host are still valid, offsets between hosts are not. Missing parents or a trace that stops early mean lost context (`broken-trace-hunt`). Sampling bias matters too: if the store keeps slow traces preferentially, the share of slow traces in it is not the rate in production.

### 3. Build the hop budget for one slow trace

Choose a trace from the slow cohort that shows the lead attribute. Follow the critical path, the chain of spans that determined the end time, from the root down.

- Self time of a span is its duration minus the union of its children's intervals, not the sum. Overlapping children (parallel calls) must be merged first, otherwise self time goes negative or is understated.
- A gap between a parent's start and its first child, or between sequential children, is time not attributed to any span: queueing, connection pool wait, thread pool starvation, a garbage collection pause, a lock, or work that is not instrumented. Name it a gap; do not assign it to the callee.
- Many identical short sibling spans (the same query or call repeated tens of times) are an N+1 pattern. Count them and multiply by the typical duration.
- Sequential spans of the same operation with the same arguments, often with a growing delay, are hidden retries or a retry wrapper around a slow call.
- Fan-out latency is the maximum of the parallel children, not the mean. If each of N parallel calls exceeds its p99 with probability p, the chance that at least one does is 1-(1-p)^N; with p of 1% and N of 100, that is about 63%, which is why a fan-out service's median request already sees its dependencies' tail.
- Report each hop as a share of the critical path, not of the sum of all spans, since parallel work is counted once.

### 4. Close with the table

End with a table: hop, time on the critical path, share, what it is (work, wait, gap, retry, skew), and the next measurement. Examples of next measurements: add a span around the uninstrumented gap, log the pool wait time, break down the payload size histogram, rerun the cohort comparison after a version rollback. A latency finding without a next measurement is a story, not a result.

### 5. Hand bulky data to the reader

When the evidence is a large bundle of exported traces, give it to the `telemetry-reader` subagent and ask it for the critical path of the slowest and median traces and the attributes on each. This skill owns the cohort comparison and the arithmetic on what comes back.

## Hand back

The separating attribute with the cohort shares, the hop table for a representative slow trace, any structural caveat (skew, sampling, missing context), and the next measurement.

## Anti-patterns

**Reading the single worst trace.** It explains one request, not the percentile.

**Summing child durations.** Parallel children overlap; the sum overstates and the self time goes wrong.

**Blaming the callee for a gap.** Time before a child starts belongs to the caller side until proved otherwise.

Read `references/worked-example.md` for a cohort comparison and hop budget with numbers.
