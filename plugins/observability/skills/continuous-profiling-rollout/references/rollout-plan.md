# Continuous profiling rollout reference

Contents: collection decision table, per-runtime verification, A/B protocol, label scheme, diff recipe.

## Collection decision table

| Runtime | Prefer | eBPF caveat |
| --- | --- | --- |
| Go | Language-level: pprof endpoints scraped by the profiler, or the Go SDK | Frame pointers are on by default on common platforms, so eBPF works well |
| JVM | Language-level agent (async-profiler based) | eBPF needs the agent to resolve Java frames; JIT code without a perf map shows as unknown |
| Python, Ruby, Node | Language-level agent where available | eBPF only if the agent resolves interpreter frames to source functions |
| C, C++, Rust | eBPF | Needs frame pointers or unwind tables; builds with frame pointers omitted may give broken stacks |
| Containers of mixed runtimes | eBPF per node as the catch-all | Verify per runtime on a sample before widening |

Name the specific agent and version you adopt in the rollout record; capabilities differ between Pyroscope's agents, Grafana Alloy's profiling components, Parca Agent and the OpenTelemetry eBPF profiler, and change between releases.

## Verification on a sample process

1. Profile one known process for a few minutes under load.
2. Open the flame graph. Do you see your own function names at the top of the hot path?
3. Check that kernel, native library and interpreter frames are named, not hex addresses.
4. Compare the top function against a one-off profile taken the usual way (for example a pprof capture). They should agree on the heaviest frames.
5. If not, record the runtime as unsupported by that method and pick another.

## A/B protocol

| Item | Value |
| --- | --- |
| Pods | Matched replicas of one deployment, same version, same node pool |
| Duration | One week, so weekday and weekend load appear |
| Measures | CPU, memory, p50 and p99 latency, error rate, restart count |
| Decision | Within budget (one to two percent CPU) and no p99 regression beyond noise |

## Label scheme

| Label | Keep | Reason |
| --- | --- | --- |
| service | yes | Primary grouping |
| version | yes | Needed for deploy diffs |
| region | yes | Regional differences |
| environment | yes | Separates staging |
| pod, container id | no | Multiplies series, blocks version comparison |
| request id, user id, trace id | no | Unbounded cardinality; use span profiles for sampled traces instead |

## Deploy diff recipe

1. Pick two versions of one service and the same weekday window for each.
2. Use the profiler's comparison view or diff flame graph with the earlier version as baseline.
3. Normalise for traffic if request volume differed.
4. Record the top three frames that grew and the top three that shrank, with their change in share of total samples.
5. State whether this matches the intent of the change.
