# Stuck volumes

Read this before removing a finalizer, deleting a VolumeAttachment, or tainting a node.
Each row starts from what `kubectl describe pvc` or `kubectl describe pod` shows. The
safe action comes first; the unsafe shortcut is named so it can be recognised and refused.

## Contents

- Claims that will not bind
- Pods that will not mount
- Objects that will not delete
- Volumes that will not reuse
- Node failure and RWO volumes

## Claims that will not bind

| Symptom | Usual cause | Safe action |
| --- | --- | --- |
| PVC `Pending`, event `waiting for first consumer to be created before binding` | `WaitForFirstConsumer`; no pod uses it yet | Nothing. It binds when a pod is scheduled |
| PVC `Pending`, `no persistent volumes available for this claim and no storage class is set` | No default class, or `storageClassName: ""` asks for static binding | Set the class explicitly |
| PVC `Pending`, provisioning errors from the CSI driver | Driver not running, missing cloud permissions, or quota | Read the driver controller's logs; fix the permission or quota |
| Pod `Pending`, `node(s) had volume node affinity conflict` | The volume is in a zone with no schedulable node for this pod | Add capacity in that zone, or relax a node selector; the volume cannot move zones |

## Pods that will not mount

| Symptom | Usual cause | Safe action |
| --- | --- | --- |
| `Multi-Attach error for volume ... Volume is already exclusively attached to one node` | An RWO volume is still attached to the previous node, usually after a node failure or a fast reschedule | Wait for the detach if the old node is healthy. If it is gone, see node failure below |
| Mount takes minutes on a large volume | Recursive ownership change for `fsGroup` on every file | Set `securityContext.fsGroupChangePolicy: OnRootMismatch` |
| `FileSystemResizePending` that never clears | The filesystem resize runs when the node mounts the volume | Restart the pod so the volume is remounted; check the driver supports online expansion |

## Objects that will not delete

| Symptom | Usual cause | Safe action | Unsafe shortcut |
| --- | --- | --- | --- |
| PVC stuck `Terminating` | `kubernetes.io/pvc-protection`: a pod still uses it | Find the pod (`kubectl get pods -n NS -o json` and look for the claim name) and stop it | Removing the finalizer, which pulls the volume from under a running process |
| PV stuck `Terminating` | `kubernetes.io/pv-protection`: still bound to a claim | Delete or release the claim first | Removing the finalizer |
| PV stuck with an external-provisioner finalizer | The driver cannot delete the cloud disk: permissions, or the disk is still attached | Fix the permission or detach; read the driver's logs | Removing the finalizer, which orphans the disk silently |

## Volumes that will not reuse

A `Retain` volume whose claim was deleted goes to `Released` and will not bind to a new
claim, because `spec.claimRef` still names the old one. To reattach the same disk to a new
claim deliberately:

```bash
set -Eeuo pipefail
kubectl patch pv "$PV" --type json -p '[{"op":"remove","path":"/spec/claimRef"}]'
# PV is now Available; create a PVC with spec.volumeName set to "$PV" and a matching
# class, access mode and size, so it binds to this volume and nothing else.
```

Confirm what is on the disk before you do this. A released volume reattached to the wrong
workload is a data leak between tenants.

## Node failure and RWO volumes

When a node dies without shutting down cleanly, Kubernetes cannot know whether the old pod
is still writing, so it does not detach the volume and the replacement pod reports
Multi-Attach. That caution is correct: two writers on one block device corrupt it.

Only when you have confirmed the node is powered off or fenced, not merely unreachable,
mark it out of service so the volume can be detached and the pod recreated elsewhere:

```bash
kubectl taint nodes "$NODE" node.kubernetes.io/out-of-service=nodeshutdown:NoExecute
```

Remove the taint after the node is recovered or deleted. Confirm power state from the
cloud console or provider API, never from the node's `NotReady` status alone: a node can be
unreachable to the control plane while still writing to its disks.

Deleting a `VolumeAttachment` object by hand has the same risk with less tooling around it.
Prefer the taint, and do neither while the old node could still be running.
