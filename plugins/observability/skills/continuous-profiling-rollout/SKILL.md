---
name: continuous-profiling-rollout
description: "Introduce always-on production profiling with bounded overhead and a way to use it. Choose collection per runtime: language-level agents where offered, eBPF whole-host profiling only where stack unwinding works (frame pointers or unwind tables, interpreter frames resolved). Budget one to two percent CPU and prove it with a week-long A/B on matched pods before widening, starting with one service then the top CPU spenders. Label by service, version and region, never pod or request; link spans to profiles only for sampled traces; retain enough to diff two versions. The first deliverable is a before-and-after diff of the last deploy. Use for 'set up continuous profiling', 'Pyroscope or Parca rollout', 'flame graphs from production', 'eBPF profiler for the fleet'. Not for speeding up one code path (profiling), telemetry setup (instrumentation) or sizing (capacity-planning)."
allowed-tools: Read, Glob, Grep
---

# Continuous Profiling Rollout

This skill is done when a chosen set of services profiles continuously within a measured overhead budget, engineers can open a flame graph for any service and version, and the team has used it to produce a before-and-after diff of a real deploy.

The usual failure is installing a profiler fleet-wide because it is cheap, then discovering that stacks are garbage for half the runtimes, that labelling by pod made the storage bill explode, and that nobody opens it because a single flame graph answers no question anyone had. Roll out per runtime, measure the cost, and ship a use before shipping coverage.

## Scope

Use for: introducing or standardising always-on profiling (Pyroscope, Parca, Grafana Alloy profiling components, the OpenTelemetry eBPF profiler, or a vendor's continuous profiler) across production services.

Do not use for: making one slow function faster once you have its profile (`profiling`), adding metrics, logs and traces (`instrumentation`), or sizing hardware from profile data (`capacity-planning`).

## Workflow

### 1. Inventory runtimes and pick the collection method per runtime

List the services by runtime, language version, deployment shape and CPU spend. For each runtime choose between:

- **Language-level agent or SDK.** Pull mode (the backend scrapes a profiling endpoint the runtime exposes, such as Go's pprof handlers) or push mode (an in-process agent sends profiles). Use this wherever the runtime offers one: it resolves symbols and interpreter frames correctly and its cost is bounded by the sampling rate.
- **eBPF whole-host profiling.** One agent per node, no code change, covers every process. Use it only where stack unwinding works for the workload: native binaries compiled with frame pointers or carrying unwind tables, and interpreters (Python, Ruby, Node, JVM) that the agent resolves into their source-level frames. Verify on a sample process before trusting it: an eBPF flame graph full of hex addresses or a single opaque interpreter frame means it is not working for that runtime.

A mixed fleet usually ends up with both: language agents for the JVM and Go services that matter, eBPF as the catch-all for the rest. Read `references/rollout-plan.md` for the decision table and the per-runtime verification.

### 2. Set the overhead budget before installing anything

Agree a budget of one to two percent CPU per profiled process, plus a bounded memory and network cost, and the action when it is exceeded (lower the sampling rate, disable on that service). Without a number, the first complaint about latency ends the rollout.

### 3. Pilot one service and prove the budget

Choose one service with steady traffic and several identical replicas. Enable profiling on half of them and compare matched pods for a week: CPU, memory, latency percentiles and error rate, with the same deploy version and the same load balancer weighting. Look at tail latency, not only mean CPU; sampling costs can show up in p99 first. If the difference sits within the budget and within the noise, continue; if not, lower the sampling frequency or choose a different collection method and repeat.

### 4. Define labels before ingesting at scale

Profiles are indexed by their labels, and every distinct label combination is a separate stored series. Label by `service`, `version` and `region` (plus environment). Never label by pod name, container ID, request ID, user or trace ID: they multiply storage and make a version-to-version comparison impossible, because the series you want to diff are scattered across pods. Version must be set on every profile, since the diff in step 6 depends on it.

Link spans to profiles only for sampled traces: span profiles tie a trace span to the profile samples taken during it, which is useful for the traces you keep and wasted cost for those you drop. Use the profiler's documented span-profile integration for your tracing library, and only on services where traces are sampled in.

### 5. Widen deliberately

Order: the pilot service, then the top CPU spenders (your cost review or capacity data names them), then the rest. Re-check the overhead at each step, since a hot service amplifies a small per-process cost. Stop at the point where the next service would profile something nobody would ever look at.

Set retention to keep enough history to compare two versions across a release: long enough to hold the previous and current deploys at normal traffic. Storage is cheap relative to the cost of not having the "before" profile; shorten high-resolution retention first, not the whole window.

### 6. Make the first deliverable a diff

Take the most recent deploy of the pilot service and produce a before-and-after comparison: the diff flame graph between the version before and the version after, restricted to the same hours of the week. Write down what grew, what shrank, and whether it matches what the change was supposed to do. If the comparison is not possible (missing version label, too-short retention, symbols missing), fix that now. A diff that answers a question someone asked is what turns the tool from a curiosity into a habit.

## Hand back

The runtime inventory and collection method per runtime; the overhead budget and the A/B result with numbers; the label scheme; the services profiled in each wave; retention settings; the span-profile decision; and the before-and-after diff of a real deploy with its finding.

## Anti-patterns

**Installing eBPF everywhere and trusting the output.** Unreadable stacks look like data until someone tries to use them.

**Pod name as a label.** It guarantees the version comparison you wanted cannot be made.

**Measuring overhead on a staging cluster.** Production traffic shape and core counts differ.

**Rolling out coverage before a use.** Without the deploy diff, nobody opens it.
