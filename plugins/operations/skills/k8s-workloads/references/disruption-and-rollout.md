# Disruption budgets, rollouts and placement

Read this at steps 5 to 7, when deciding what the workload tolerates during a drain, a rollout or the loss of a failure domain.

## Contents

- [What a PodDisruptionBudget actually covers](#what-a-poddisruptionbudget-actually-covers)
- [Budget shapes, worked through](#budget-shapes-worked-through)
- [unhealthyPodEvictionPolicy](#unhealthypodevictionpolicy)
- [The drain arithmetic](#the-drain-arithmetic)
- [Rollout parameters at real replica counts](#rollout-parameters-at-real-replica-counts)
- [Topology spread against pod anti-affinity](#topology-spread-against-pod-anti-affinity)

## What a PodDisruptionBudget actually covers

Only voluntary disruption, and only when it goes through the Eviction API. That covers `kubectl drain`, the cluster autoscaler scaling a node group down, and node pool upgrades performed by a tool that evicts rather than deletes.

It does not cover a node failing, a kubelet crashing, an OOMKill, a `kubectl delete pod`, or a Deployment's own rolling update. A budget is not an availability guarantee and cannot be cited as one; it is a protocol for negotiating with whoever is draining a node.

Budgets also apply per-pod-set. A pod covered by two overlapping budgets cannot be evicted at all, so overlapping selectors are worth checking for during a review.

## Budget shapes, worked through

| Replicas | Budget | Effect on a drain |
| --- | --- | --- |
| 1 | `minAvailable: 1` | No eviction is ever permitted. Every drain of that node blocks indefinitely. |
| 1 | `maxUnavailable: 0` | Identical to the above. So is `minAvailable: 100%`. |
| 1 | none | The pod is evicted with its grace period and rescheduled. There is a gap in service, which is the truth about a single replica either way. |
| 3 | `maxUnavailable: 1` | One pod at a time moves; two stay serving. |
| 3 | `minAvailable: 2` | The same thing today, and it silently becomes weaker at 5 replicas and stronger at 2. |
| 5 (quorum) | `minAvailable: 3` | Expresses a quorum requirement directly, which is the case where `minAvailable` is the better field. |

Two conclusions follow. First, prefer `maxUnavailable` unless you are expressing a quorum: upstream recommends it because it keeps meaning the same thing when the replica count changes, whereas an absolute `minAvailable` drifts in meaning every time somebody scales.

Second, a single replica with a budget is the worst of the options in that table. The drain blocks, and the escalation is `kubectl drain --disable-eviction`, which stops using the eviction API and deletes the pod directly, bypassing the budget. That delete is still graceful — it honours `terminationGracePeriodSeconds` and runs `preStop` — so the budget did not protect the pod, it only stalled the drain and cost somebody an afternoon. (`--force` is unrelated: it governs pods with no controller and has no effect on a budget.) Either run two replicas with `maxUnavailable: 1`, or run one replica with no budget and be honest that it has a maintenance window.

Percentages round in a specific direction: `minAvailable` as a percentage rounds up, so seven pods at `"50%"` requires four available, not three.

## unhealthyPodEvictionPolicy

`.spec.unhealthyPodEvictionPolicy` decides whether pods that are Running but not yet healthy may be evicted.

| Policy | Behaviour |
| --- | --- |
| `IfHealthyBudget` (the default when the field is unset) | Running-but-unhealthy pods can be evicted only while the application is undisrupted — that is, while `currentHealthy` is at least `desiredHealthy`. A CrashLooping or never-Ready deployment therefore blocks node drains. |
| `AlwaysAllow` | Running-but-unhealthy pods are treated as already disrupted and can be evicted regardless of the budget. |

Pods in `Pending`, `Succeeded` or `Failed` are always evictable under either policy.

The default is the safer choice for an application whose pods will recover on their own, and the cause of a long class of "why is this drain stuck" incidents when they will not. `AlwaysAllow` is the right setting for a workload whose unhealthy pods are not worth protecting, which is most stateless services. Check the field is available in your cluster's version before relying on it.

## The drain arithmetic

With `maxUnavailable: 1`, a drain moves one pod at a time and waits for the replacement to become ready before the next eviction is permitted. So for one workload:

```text
drain time  ≈  pods of that workload on the node
               × (scheduling + image pull + startup + readiness + minReadySeconds)
```

Multiply by the number of workloads on the node, then by the number of nodes in the pool, and the reason a cluster upgrade is scheduled for a weekend stops being mysterious. Two things shorten it materially: a larger `maxUnavailable` where the workload can tolerate it, and a shorter path to readiness — which is usually image pull time and startup probe budget, not scheduling.

Two things lengthen it without anyone deciding to: a budget that permits nothing, and a workload whose pods are never all healthy, under the default eviction policy.

## Rollout parameters at real replica counts

`maxUnavailable` rounds down, `maxSurge` rounds up. The defaults are 25% for both.

| Replicas | Default `maxUnavailable` (25%, down) | Default `maxSurge` (25%, up) | Served capacity during the rollout |
| --- | --- | --- | --- |
| 2 | 0 | 1 | 100% — the rounding happens to protect you here |
| 3 | 0 | 1 | 100% |
| 4 | 1 | 1 | 75% |
| 10 | 2 | 3 | 80% |
| 20 | 5 | 5 | 75% |

The table is the argument for reading these fields rather than inheriting them. The same two defaults mean "no capacity loss" at three replicas and "a quarter of capacity gone for the length of the rollout" at twenty, and nothing announces the change as the service grows.

Settings worth choosing deliberately:

- `maxUnavailable: 0` with `maxSurge: 1` for latency-sensitive services with room to surge. Capacity never drops below the declared count. The cost is a slower rollout and one pod's worth of extra headroom in the node pool.
- `maxUnavailable: 1` with `maxSurge: 0` where a replica cannot be duplicated — a workload holding an exclusive lock, a licence limit, or a fixed-size connection pool on a downstream.
- `minReadySeconds` above the time it takes for the first real request to reach a new pod and fail. At the default of 0, a pod that passes readiness and dies eight seconds later has already let the rollout advance, and the rollout will replace every healthy replica with a broken one before anything stops it.
- `progressDeadlineSeconds`, default 600, sets `ProgressDeadlineExceeded` and retries. It does not roll back. A Deployment has no automatic rollback of any kind, so either a controller or a person is watching for that condition, or nothing is.
- `revisionHistoryLimit`, default 10, is what `kubectl rollout undo` reads. Setting it to 0 makes the rollout unrollbackable, which removes the first mitigation `k8s-triage` reaches for during an incident.

A rollout also needs the resources to surge into. `maxSurge: 25%` on a workload whose requests already fill the node pool produces Pending pods and a rollout that stalls halfway, with both versions serving — a state that is harder to reason about than either version alone.

## Topology spread against pod anti-affinity

`topologySpreadConstraints` is the current instrument:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: checkout
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: checkout
```

`whenUnsatisfiable` defaults to `DoNotSchedule` and is the decision that matters: when the spread cannot be satisfied, is not running better than being unbalanced?

- `DoNotSchedule` across zones is defensible for a workload that must survive losing one, and its cost is real — during a zone outage, replacement pods stay Pending rather than piling into the surviving zones, which is exactly when you wanted them to run.
- `ScheduleAnyway` degrades to a scheduler preference and keeps the workload running unbalanced.

There can be only one constraint per `topologyKey` and `whenUnsatisfiable` pair, so the two above coexist only because they differ in both fields.

`minDomains` behaves as 1 when unset and may only be used with `DoNotSchedule`. `nodeAffinityPolicy` and `nodeTaintsPolicy` control whether nodes the pod could not use anyway count as domains; leaving them at their defaults is usually right, but they are the explanation when a constraint behaves as though domains exist that the pod cannot reach.

Pod anti-affinity expresses the same intent more bluntly. `requiredDuringSchedulingIgnoredDuringExecution` on `kubernetes.io/hostname` caps the replica count at the number of eligible nodes: the eleventh replica of a ten-node pool is permanently Pending, and it discovers this during a scale-up in a traffic spike. `preferredDuringScheduling...` is the soft form and is roughly equivalent to `ScheduleAnyway` with a weight.

`IgnoredDuringExecution` is the load-bearing half of both names. Placement is evaluated once, at scheduling time, and never revisited — so after a zone outage recovers, the surviving zones stay overloaded and the recovered zone stays empty until pods are recreated. Rebalancing needs a descheduler or a deliberate rollout; no constraint does it.

Finally, check the node labels exist. A `topologyKey` matching no node label is not an error and produces no warning; the constraint simply has no effect, and the spread you believe you have is imaginary until a zone fails and proves otherwise.
