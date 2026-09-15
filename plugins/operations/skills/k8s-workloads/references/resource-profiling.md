# Resource profiling

Read this at step 1, before writing any `requests` or `limits` value.

## Contents

- [Which statistic, for which resource](#which-statistic-for-which-resource)
- [The queries](#the-queries)
- [Using the VPA recommender without letting it act](#using-the-vpa-recommender-without-letting-it-act)
- [Profiling a workload that is not in production yet](#profiling-a-workload-that-is-not-in-production-yet)
- [What a provisional number needs attached to it](#what-a-provisional-number-needs-attached-to-it)
- [Correcting a number without a rollout](#correcting-a-number-without-a-rollout)
- [Multi-container pods and pod-level accounting](#multi-container-pods-and-pod-level-accounting)

## Which statistic, for which resource

The right summary statistic follows from what the kernel does when the number is wrong, which is different for the two resources.

| Number | Statistic | Why that one |
| --- | --- | --- |
| `requests.memory` | A high percentile of the working set over the window | Exceeding the request costs eviction ranking under node pressure, not a kill. Sizing it at the absolute peak wastes schedulable memory on every node for a condition that occurs once a week. |
| `limits.memory` | The maximum over the window, with room for the growth you expect before the next revision | Exceeding the limit is a kill. A limit at the 99th percentile kills the container during one window in a hundred, which reads as an intermittent application fault. |
| `requests.cpu` | A high percentile of usage — p95 or p99 — over the window | Exceeding it costs scheduling position and eviction ranking; the process keeps running. CPU is reclaimable, so over-requesting is pure waste of schedulable capacity. |
| `limits.cpu` | Usually absent. Where one is required, well above the measured peak, with throttling verified at zero | The limit throttles in 100ms windows, so it has to clear the burst rather than the average. |

The window has to contain a weekly peak, at least one deploy, and one start from cold. A profile taken from a warm, mid-week, mid-afternoon hour describes a state the workload is not in when the numbers matter.

Memory has one more wrinkle: the kubelet counts `tmpfs` `emptyDir` volumes as container memory use, so a workload writing to a memory-backed scratch volume has a working set that includes files it thinks are on disk.

## The queries

`container_memory_working_set_bytes` is the figure the kubelet uses, and it is the right one to read. Resident set size is not: it includes reclaimable page cache and will lead you to over-provision.

```promql
# Peak working set per container over a week
max_over_time(container_memory_working_set_bytes{namespace="production", container="checkout"}[7d])

# A high percentile of the same, for the request
quantile_over_time(0.95, container_memory_working_set_bytes{namespace="production", container="checkout"}[7d])

# CPU cores used, at the 99th percentile of five-minute rates
quantile_over_time(0.99, rate(container_cpu_usage_seconds_total{namespace="production", container="checkout"}[5m])[7d:5m])

# Fraction of CFS periods in which the container was throttled
rate(container_cpu_cfs_throttled_periods_total{namespace="production", container="checkout"}[5m])
  / rate(container_cpu_cfs_periods_total{namespace="production", container="checkout"}[5m])

# OOMKills, which is what the alert on a provisional memory number watches
kube_pod_container_status_last_terminated_reason{reason="OOMKilled", namespace="production"}
```

The throttling ratio is the query that settles the argument about CPU limits. Run it against the current limit before changing anything: a sustained non-zero value is a measurement, not an opinion, and it is usually the answer to a tail-latency question somebody is asking in a different channel.

Without a metrics stack, `kubectl top pod --containers` is all there is, and it is a spot reading from metrics-server's sampling interval. Use it to confirm an order of magnitude and nothing more. An hourly cron capturing it into a file for a week is a poor profile but a real one, and it beats a guess.

## Using the VPA recommender without letting it act

The Vertical Pod Autoscaler in recommendation mode is the least intrusive profiler available for a workload already running:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: checkout
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: checkout
  updatePolicy:
    updateMode: "Off"
```

With `updateMode: "Off"` nothing is evicted or mutated; the recommender populates `status.recommendation.containerRecommendations` with `target`, `lowerBound`, `upperBound` and `uncappedTarget` per container. Read `target` as a starting point for requests and `upperBound` as evidence about the limit, then sanity-check both against the queries above rather than accepting them.

Two cautions. The recommender needs time to see a representative window, so a recommendation read an hour after installing it describes an hour. And running VPA in `Auto` mode alongside a Horizontal Pod Autoscaler on CPU makes the two fight over the same signal — that interaction is `capacity-planning` territory, not this skill's.

## Profiling a workload that is not in production yet

Run it against a load profile rather than against nothing. `capacity-planning` owns designing that load — the peak-to-mean ratio, the data volumes, the shape of the test. What this skill needs back from it is narrow:

- Peak working set during the test, including the cold-start phase before caches fill.
- CPU at the peak, and whether throttling occurred if a limit was set.
- Memory at the end of a long steady-state run compared with the start, which is the only cheap way to see a leak before it is a production incident.

A profile taken against an empty database measures an empty database. If the test data volume is unrepresentative, say so when quoting the numbers.

## What a provisional number needs attached to it

A guessed number is acceptable when it is labelled and watched. It becomes dangerous when the label falls off and it starts being cited as a measurement — including by the next service that copies it.

Attach three things:

1. A comment in the manifest saying the number is provisional and what would replace it.
2. An alert. For memory, `OOMKilled` appearing in a container's last terminated reason; for CPU where a limit exists, the throttling ratio above becoming sustained.
3. A dated ticket with an owner to replace the guess with a profile.

There is no correct multiplier to apply to a guess. Published guidance does not offer one, and the figures that circulate — double it, add a fifth — are folklore with the shape of a rule. Inventing one here is how a guess acquires the authority of a measurement, which is worse than the guess.

## Correcting a number without a rollout

In-place pod resize needs a cluster at Kubernetes v1.33 or newer, and a `kubectl` client at v1.32 or newer for the `--subresource=resize` flag:

```bash
set -Eeuo pipefail
kubectl patch pod checkout-7d9f -n production --subresource=resize --patch \
  '{"spec":{"containers":[{"name":"checkout","resources":{"requests":{"cpu":"800m"},"limits":{"cpu":"800m"}}}]}}'
```

`resizePolicy[*].restartPolicy` defaults to `NotRequired`, so CPU changes apply to the running container. Memory behaves differently: a decrease is best-effort unless the policy for memory is `RestartContainer`, and Windows pods do not support in-place resize at all. Treat this as a way to correct a provisional CPU number cheaply during an experiment, and then write the result back into the manifest — a pod patched in place loses the change the moment it is rescheduled.

## Multi-container pods and pod-level accounting

Requests and limits are per container, and the scheduler sums them. A sidecar with no request contributes nothing to the sum and can still consume the node's memory, which is how a pod sized correctly gets evicted for its logging agent. Profile every container in the pod, including the ones you did not write.

Init containers are accounted differently again — the effective request is the larger of the highest init container request and the sum of the regular containers — so a heavyweight init container can dominate the pod's scheduling footprint for the entire life of the pod, long after it has exited.
