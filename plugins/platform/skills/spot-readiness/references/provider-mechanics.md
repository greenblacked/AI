# Provider mechanics for spot capacity

Read this at steps 4, 6 and 7. Provider behaviour changes; where a detail decides a design,
check it against the provider's current documentation before relying on it.

## Contents

- [AWS](#aws)
- [GCP](#gcp)
- [Azure](#azure)
- [Floor mechanisms compared](#floor-mechanisms-compared)

## AWS

**Notice.** Two minutes, delivered as an instance action in instance metadata
(`/latest/meta-data/spot/instance-action`) and as an EventBridge "EC2 Spot Instance
Interruption Warning" event. A rebalance recommendation may arrive earlier when the
instance is at elevated risk; it is a hint, not a guarantee.

**Handler — choose one.**

| Provisioning | Handler |
| --- | --- |
| Karpenter | Karpenter's own interruption handling, fed by an SQS queue that EventBridge rules write to. Do not also run the Node Termination Handler on these nodes |
| EKS managed node groups with spot | Capacity Rebalancing is enabled for spot managed node groups, and the service drains nodes on rebalance; confirm against your version before adding another handler |
| Self-managed Auto Scaling groups | AWS Node Termination Handler. Queue-processor mode (EventBridge to SQS) also handles rebalance recommendations and Auto Scaling lifecycle events; IMDS mode runs as a DaemonSet and sees only its own node's metadata |

**Diversity.** Mixed-instances policy or Karpenter requirements across ten or more types;
`price-capacity-optimized` allocation. `aws ec2 get-spot-placement-scores` scores a set of
types per region or zone before you commit to it.

**Labels.** Karpenter: `karpenter.sh/capacity-type` with `spot` or `on-demand`. Managed
node groups: `eks.amazonaws.com/capacityType` with `SPOT` or `ON_DEMAND`. Neither taints
spot nodes by default; add a taint in the NodePool or node group.

**Injecting an interruption.** AWS Fault Injection Service, action
`aws:ec2:send-spot-instance-interruptions`, targeting spot instances by tag. It sends the
real notice ahead of the stop, so the handler path is exercised end to end. Target a
percentage of a pool for the correlated run.

## GCP

**Notice.** 30 seconds for Spot VMs and preemptible VMs, delivered as an ACPI shutdown;
the instance metadata server also reports the preemption. On GKE, graceful node shutdown
is configured for spot nodes so the kubelet terminates pods within that window — system
pods are given part of it, so ordinary pods get less than the full 30 seconds.

**Handler.** GKE handles shutdown on spot node pools itself; there is no separate drain
step to add. Keep grace periods short enough to fit what the kubelet allows.

**Labels and taints.** Spot nodes carry `cloud.google.com/gke-spot=true` (preemptible nodes
`cloud.google.com/gke-preemptible=true`). On-demand nodes do not carry the label at all, so
a topology spread on it does not balance between the two. GKE does not taint spot pools by
default; add a `NoSchedule` taint on the pool and tolerate it in spot-eligible workloads.

**Injecting an interruption.** Stop a spot node's VM during load. It runs the same ACPI
shutdown path; it does not reproduce the provider reclaiming a whole pool, so for the
correlated run stop several nodes of the same machine type in one zone together.

## Azure

**Notice.** At least 30 seconds, as a `Preempt` event from the Scheduled Events endpoint of
the instance metadata service.

**Handler.** Confirm what cordons and drains an AKS spot node on a `Preempt` event in your
setup. If nothing does, run a handler that polls Scheduled Events on each spot node and
cordons and drains on `Preempt`.

**Labels and taints.** AKS spot node pools are labelled and tainted automatically:
`kubernetes.azure.com/scalesetpriority=spot`, with a `NoSchedule` taint of the same key and
value. Workloads must tolerate it to land there.

**Eviction policy.** `Delete` removes the node; `Deallocate` stops it and keeps the disk,
which still counts against quota. `Delete` is the usual choice for a node pool.

**Injecting an interruption.** `az vm simulate-eviction` for a VM, `az vmss
simulate-eviction` for a scale-set instance, which is what AKS node pools use.

## Floor mechanisms compared

| Mechanism | Guarantees | Does not guarantee |
| --- | --- | --- |
| Auto Scaling group `OnDemandBaseCapacity` | That many on-demand instances exist | That any replica of yours runs on them |
| Karpenter NodePool allowing both capacity types | Falls back to on-demand when spot is unavailable | A floor; it prefers spot whenever spot is available |
| Topology spread on a capacity-type label present on all nodes | An even split between spot and on-demand for that workload | A specific count; the split follows `maxSkew` |
| Two Deployments, one pinned to on-demand | An exact on-demand replica count | Correct total capacity if the spot Deployment is mis-sized |
| Node affinity preferring spot | Nothing about a floor | — |

For a floor that must be an exact number, two Deployments behind one Service is the
portable answer.
