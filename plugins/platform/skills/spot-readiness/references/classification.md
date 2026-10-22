# Classifying workloads for spot

Read this at steps 1 and 2. The output is one row per workload with a measured number and
a verdict someone can argue with.

## Contents

- [The measurement sheet](#the-measurement-sheet)
- [Sizing the on-demand floor](#sizing-the-on-demand-floor)
- [Edge cases](#edge-cases)

## The measurement sheet

Measure each phase separately, because the fix for each is different.

| Phase | How to measure | What shortens it |
| --- | --- | --- |
| Node provisioning | Time from a pending pod to a new node `Ready`, read from the autoscaler's events or logs | Headroom on existing nodes; nothing on the pod side |
| Scheduling | Pod `Scheduled` event minus pod creation | Fewer hard affinity rules |
| Image pull | `Pulling` to `Pulled` events on a node that has never run the image | Smaller image, a pre-pull DaemonSet, a node image with it baked in |
| Start-up to ready | `Started` to the pod's `Ready` condition | Faster start-up, a startup probe that matches reality |
| Warm-up | Ready until the replica's p99 latency matches its steady-state peers | Cache priming before readiness, or accept degraded latency in the SLO |
| System recovery (stateful) | Leader election, rebalance or replication catch-up, from the system's own metrics | Usually nothing short of keeping it off spot |

Recovery time is the sum when no node is free, and the sum minus node provisioning when
spare capacity exists. Record both, and which one your cluster usually hits during a
reclaim — the answer is usually the first, because the reclaim took the spare capacity
too.

```bash
kubectl get events -n "$NS" -o json \
  | jq -r --arg pod "$POD" '.items[] | select(.involvedObject.name == $pod)
    | [.lastTimestamp, .reason, .message] | @tsv'
```

## Sizing the on-demand floor

The floor's job is to carry the workload while spot replicas are gone and their
replacements are still recovering.

1. Find the peak request rate one replica sustains inside its latency objective, from a
   load test or from production at peak — not the average.
2. Divide the workload's peak traffic by that number: that is how many replicas must
   survive.
3. Assume the worst correlated reclaim takes every spot replica in the largest single
   pool. With spread across pools that is a fraction of the spot replicas; without spread
   it is all of them.
4. The floor is whatever on-demand count, plus the spot replicas outside the reclaimed
   pool, meets step 2.

If the floor comes out at or near the full replica count, the workload is not a spot
candidate; the savings are on the replicas above peak, and there are none.

## Edge cases

| Situation | Consequence | Verdict |
| --- | --- | --- |
| Data on instance store or `emptyDir` that takes long to rebuild | Lost on reclaim, rebuilt on the replacement | Count the rebuild in recovery time; usually on-demand |
| Long-lived connections (WebSockets, gRPC streams) | Every client reconnects within the notice | Spot only if clients reconnect with jitter and the remaining replicas take the burst |
| Jobs that cannot be retried safely | A reclaim mid-run means a partial side effect | On-demand until the job is idempotent |
| Workloads holding a PersistentVolume bound to one zone | The replacement must land in the same zone, where the reclaimed capacity was | On-demand, or accept that recovery waits for capacity in that zone |
| GPU or other scarce instance types | Few pools to diversify across; reclaims are correlated and replacements scarce | Spot only for checkpointing training or batch, never for serving with a tight SLO |
| Workload with one replica | A reclaim is an outage | On-demand, or raise replicas first |
