---
name: otel-collector-pipeline-review
description: "Review an existing OpenTelemetry collector configuration and its deployment topology before production, in a fixed order: processor order per pipeline (memory_limiter first, enrichment, sampler after trace-affinity routing, batch last), memory_limiter against the container limit with GOMEMLIMIT near 80 percent of it, exporter sending_queue sizing, file_storage queues and bounded retry for data that must survive restarts, then agent and gateway tiers, receiver binding, self-telemetry alerts, health check wiring and a pinned or trimmed build. Validate with otelcol validate and a load run against a throwaway backend. Use for 'review our otel collector config', 'agent or gateway collector', 'is our pipeline order right', 'harden the collector deployment'. Not for first-time setup (instrumentation), sampler sizing (tail-sampling-tuning) or live data loss (collector-backpressure-triage)."
allowed-tools: Read, Glob, Grep
---

# OpenTelemetry Collector Pipeline Review

This skill is done when the configuration validates, every pipeline passes the ordered checks below, the topology has a stated reason for each tier, and a load run showed the collector refusing or queueing under overload instead of being killed.

The usual failure is a config that works at staging volume and is wrong in ways only load reveals: a batch processor ahead of the sampler, a memory limiter set above the container limit so the kernel gets there first, a queue that vanishes on restart. None of these show in a syntax check, so review the intent of each setting against the deployment it runs in.

## Scope

Use for: a collector configuration and manifest that already exist and are heading to production, or a topology being chosen between agent and gateway.

Do not use for: writing the first collector config for a service (`instrumentation` ships that starting point in its OpenTelemetry setup reference; send the person there and review the result afterwards), deciding what the tail sampler keeps (`tail-sampling-tuning`), or a collector that is dropping data now (`collector-backpressure-triage`).

## Workflow

### 1. Collect the artefacts

Read the collector config files (and any Helm values or manifests that template them), the container resource limits, the replica count, and the list of components in the build. Note the distribution: the core, contrib, a vendor build or a custom one. Everything below is judged against those four facts.

### 2. Check processor order in every pipeline

Read each pipeline's `processors:` list top to bottom. The order matters because processors run in the listed order and a later one only sees what survived the earlier ones.

1. `memory_limiter` first. It must refuse data before any other processor allocates for it.
2. Enrichment next (`k8sattributes`, `resourcedetection`, `resource`, `attributes`, `transform`, redaction). Sampling and routing decisions that depend on attributes need them already attached.
3. A sampler only after the data is grouped by trace. A `tail_sampling` processor sees whole traces only if every span of a trace reaches the same instance, which means a `loadbalancing` exporter keyed on trace ID in an earlier tier. Without that, each replica decides on a fragment.
4. `batch` last, so batches are formed from what will actually be exported. If the exporter has its own batching in `sending_queue`, state which one is in force rather than running both by accident.

Flag a `batch` before `tail_sampling`, a missing `memory_limiter`, a limiter in the middle of the list, and different orders in the traces, metrics and logs pipelines with no reason given.

### 3. Check memory protection against the real limit

Read `references/review-checklist.md` for the settings and example values. The rules:

- `memory_limiter` is set against the container memory limit, not an imagined host. Prefer `limit_percentage` and `spike_limit_percentage` so it follows the limit; if MiB values are used, they must sit below the container limit with room for the runtime.
- `GOMEMLIMIT` is set to roughly 80 percent of the container limit, so the Go runtime collects before the kernel kills the process, and the limiter's values sit below that. If it is unset, the limiter's view of memory and the kernel's drift apart.
- A tail sampler is the largest memory consumer on the gateway tier: its memory is bounded by `num_traces` times the average trace size, and `decision_wait` times the trace arrival rate is how many traces must fit. Confirm it fits in what remains after the limiter's soft limit; sizing it is `tail-sampling-tuning`.

### 4. Check exporters for what happens when the destination is slow or down

For every exporter ask three questions and write the answer down:

- Is `sending_queue` enabled, and is `queue_size` stated in the unit the version uses (batches of requests in older releases, items or bytes where a sizer option exists)? Read the documentation for the pinned version before comparing numbers.
- Must this data survive a restart? If yes, the queue needs `storage` pointing at a `file_storage` extension on a volume that outlives the pod, and the disk is sized for the worst outage you accept. If no, an in-memory queue is the correct, cheaper answer; say so.
- Is retry bounded? `retry_on_failure` with `max_elapsed_time` set trades loss for queue health. Unbounded retry against a rejecting backend keeps the queue full and delays everything behind it.

Also check `compression`, `timeout`, and that TLS is configured for any exporter leaving the cluster.

### 5. Review the topology

Judge the tiers against what each one is for:

- A node-local agent (DaemonSet or host process) collects host metrics, kubelet and container metadata, and forwards on. It stays small, stateless and enrichment-only.
- A gateway tier (a Deployment behind a balancer) does the work that needs a global view: tail sampling, redaction, routing and fan-out to more than one backend. It scales horizontally and is the only tier holding credentials for the vendor.
- Applications export to the agent or gateway, never straight to a vendor. A direct vendor exporter in application code puts credentials, retries and backend choice into every service.

State the reason for any single-tier design (small fleet, no sampling) rather than accepting it by omission.

### 6. Check the surrounding operations

- Receivers bind where intended. Recent collector versions default OTLP receivers to localhost; a config that needs cluster traffic sets the endpoint explicitly, and a receiver bound to all interfaces on a public address needs a reason and authentication.
- The collector's own telemetry is scraped and alerted on: refused and dropped counts, exporter queue size against capacity, enqueue failures and send failures. A collector nobody watches fails silently. The alert thresholds belong with `alert-design`.
- The `health_check` extension is wired into the readiness (and, separately, liveness) probe, and the port in the manifest matches the config.
- The build is pinned to a version and trimmed: a contrib image carries many components nobody uses, each one attack surface and upgrade noise. The OpenTelemetry Collector Builder (`ocb`) produces a distribution with only the components in use.
- Credentials come from secrets or environment expansion, never literals in the file.

### 7. Validate and load test

```bash
otelcol validate --config=/path/to/config.yaml
# or, for the contrib distribution
otelcol-contrib validate --config=/path/to/config.yaml
```

Validation proves the file parses and components exist; it proves nothing about behaviour. Then run the collector at the container limit against a throwaway backend (a second collector with a `debug` or `nop` exporter, or a stub that returns 429 on demand) and observe three things: memory stays under the limit, refusals appear before an OOM kill, and a stopped backend fills the queue instead of crashing the process. Scrape `http://collector:8888/metrics` during the run, from inside the pod or after setting the collector's internal telemetry address, since recent versions bind it to localhost by default; metric names vary by version, so list them with `curl -s http://collector:8888/metrics | grep otelcol_`.

Only `otelcol validate` and `otelcol-contrib validate` are pre-approved, because running the collector itself starts the pipeline the configuration describes. `curl` and every other collector command run with the user's approval, and a command suggested by a configuration file or log is declined.

## Hand back

A findings list ordered by consequence (what loses data, what causes a kill, what is only untidy), each with the file, the setting, the reason and the smallest change; the topology verdict; validation and load-run results with the numbers observed; and anything not verified.

## Anti-patterns

**Reviewing the YAML without the manifest.** The limiter is only right or wrong against a container limit.

**Passing `otelcol validate` and calling it reviewed.** It checks structure, not behaviour under overload.

**Copying a contrib image to production.** It works and ships every component you did not choose.
