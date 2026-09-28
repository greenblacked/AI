# Upgrade sequence and version skew

Read this at steps 1, 4 and 5: what decides the order components upgrade in, why the
control plane cannot skip a minor, and when a routine upgrade should instead become a
replatform.

## Contents

- [The no-skip rule](#the-no-skip-rule)
- [Version-skew table](#version-skew-table)
- [The fixed add-on order](#the-fixed-add-on-order)
- [When to stop upgrading in place](#when-to-stop-upgrading-in-place)

## The no-skip rule

Kubernetes' own policy requires `kube-apiserver` not to skip minor versions when
upgrading, even in a single-instance cluster. This is a project policy tied to the API
deprecation and change guidelines, not a convenience recommendation — an API removed at
version N+2 may still need to be readable at N+1 during the migration, and skipping the
intermediate version removes the window in which that is possible.

A target three minors away is therefore three separate control-plane upgrades, each with
its own step-2 API check, its own add-on sequence and its own bake period. Nothing about
this changes because the cluster runs one control-plane instance rather than several.

## Version-skew table

The components below must stay within a bounded number of minor versions of
`kube-apiserver`, which is why the control plane always moves first:

| Component | Allowed skew from `kube-apiserver` |
| --- | --- |
| `kube-apiserver` (HA) | Within 1 minor of each other instance |
| `kubelet` | Up to 3 minors older (2, before `kubelet` 1.25) |
| `kube-controller-manager`, `kube-scheduler` | Up to 1 minor older |
| `kube-proxy` | Never newer than `kube-apiserver`; up to 3 minors older (2, before 1.25); independently, within 3 minors of the `kubelet` on its own node, either direction |
| `kubectl` | Within 1 minor, either direction |

The `kubelet` allowance is the one that makes staged node-pool rolls possible: node pools
running the previous minor's `kubelet` remain compatible with the new control plane while
the canary pool proves itself, which is what step 6 relies on.

## The fixed add-on order

CNI, CoreDNS, kube-proxy, CSI driver, ingress controller — in that order, each one moved
to a version compatible with the new control plane before the next is touched.

- **CNI first.** Nothing schedules onto a node without working pod networking, so every
  later step depends on it.
- **CoreDNS and kube-proxy next.** Service discovery and service routing are
  load-bearing for every workload's own health checks, including the ones the CNI's
  rollout itself depends on.
- **CSI driver.** Anything with a persistent volume needs the driver compatible with the
  new control plane before its pods can reschedule during the node-pool step.
- **Ingress controller last.** It depends on the CNI and CoreDNS being stable, and
  upgrading it earlier risks routing flaps while the networking layer underneath it is
  still moving.

An add-on updated ahead of the control plane, or left behind after it, is the second most
common cause of an upgrade window turning into an incident — after a blocking
PodDisruptionBudget discovered mid-drain.

## When to stop upgrading in place

A cluster more than one minor behind means multiple sequential control-plane hops, each
with no rollback. Use this table to decide whether the in-place path is still the safe
one:

| Signal | In-place (N sequential hops) | New cluster and traffic shift |
| --- | --- | --- |
| Minors behind | One or two, with a downtime budget that absorbs each hop's bake | Three or more, or a downtime budget that cannot absorb N full bake periods |
| Deprecated API findings | A short, owned list per hop | A long list spanning several removed API generations at once |
| Add-on compatibility | Each add-on has a supported version for every intermediate hop | An add-on has no supported version for an intermediate minor, forcing an unsupported gap |
| Blast radius of a mistake | One control plane, one set of node pools | Same, but multiplied by the number of unattended hops |

When the right-hand column applies, hand the cluster to `plan-platform-migration` for the
phased design of the replacement cluster, and to `cutover` for the switch window that
moves traffic once it is ready. Treat that decision as made once, before the first hop,
not renegotiated part-way through a sequence of upgrades that turns out to be harder than
planned.
