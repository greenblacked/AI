# Storage manifests

Read this when writing a StorageClass, a VolumeSnapshotClass, a snapshot, or the restore
objects for step 5. The driver names and parameters below are for the AWS EBS CSI driver
as a concrete example; every other driver has its own `provisioner`, `driver` and
`parameters`, so take those from that driver's documentation rather than adapting these.

## Contents

- StorageClass for data that must survive its claim
- Marking the default class
- VolumeSnapshotClass and a snapshot
- Restoring into a scratch namespace
- Restoring in the same namespace

## StorageClass for data that must survive its claim

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: data-retain-gp3
provisioner: ebs.csi.aws.com
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
```

The restore example below uses a second class, `scratch-delete-gp3`: the same manifest
with `reclaimPolicy: Delete`, so a disposable copy cleans up its own disk.

Give the class a name that says its reclaim policy. A workload author choosing between
`fast` and `standard` cannot see which one deletes the disk; one choosing between
`data-retain-gp3` and `scratch-delete-gp3` can.

## Marking the default class

Exactly one class should carry the default annotation. A PVC with no `storageClassName`
gets the default, which is how most data ends up on a `Delete` class nobody chose.

```bash
set -Eeuo pipefail
kubectl patch storageclass gp2 \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
kubectl patch storageclass data-retain-gp3 \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

Changing the default affects new claims only; existing PVs keep their class and policy.

## VolumeSnapshotClass and a snapshot

These need the snapshot CRDs and the snapshot controller, which some managed clusters do
not install by default.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: ebs-retain
driver: ebs.csi.aws.com
deletionPolicy: Retain
---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: orders-db-0-pre-upgrade
  namespace: orders
spec:
  volumeSnapshotClassName: ebs-retain
  source:
    persistentVolumeClaimName: data-orders-db-0
```

```bash
set -Eeuo pipefail
kubectl wait volumesnapshot/orders-db-0-pre-upgrade -n orders \
  --for=jsonpath='{.status.readyToUse}'=true --timeout=30m
SNAP_CONTENT="$(kubectl get volumesnapshot orders-db-0-pre-upgrade -n orders \
  -o jsonpath='{.status.boundVolumeSnapshotContentName}')"
kubectl get volumesnapshotcontent "$SNAP_CONTENT" \
  -o jsonpath='{.status.snapshotHandle}{"\t"}{.status.restoreSize}{"\n"}'
```

`deletionPolicy: Retain` keeps the underlying cloud snapshot when the `VolumeSnapshot`
object is deleted, which matters for the same reason `reclaimPolicy: Retain` does.

## Restoring into a scratch namespace

A PVC's `dataSource` can only name a snapshot in its own namespace. To restore elsewhere
without touching the original, pre-provision a second content object pointing at the same
cloud snapshot, and bind a snapshot to it in the scratch namespace.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotContent
metadata:
  name: restore-test-orders-db-0
spec:
  deletionPolicy: Retain          # deleting this object must not delete the cloud snapshot
  driver: ebs.csi.aws.com
  volumeSnapshotClassName: ebs-retain
  source:
    snapshotHandle: snap-0123456789abcdef0   # from the original content's status
  volumeSnapshotRef:
    name: orders-db-0
    namespace: restore-test
---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: orders-db-0
  namespace: restore-test
spec:
  source:
    volumeSnapshotContentName: restore-test-orders-db-0
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-restore
  namespace: restore-test
spec:
  storageClassName: scratch-delete-gp3   # a Delete class: this copy is disposable
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 100Gi                     # at least the snapshot's restoreSize
  dataSource:
    apiGroup: snapshot.storage.k8s.io
    kind: VolumeSnapshot
    name: orders-db-0
```

With `WaitForFirstConsumer`, the claim stays `Pending` until a pod uses it; that is
expected, not a failure. Start the database or application pod against it, run the data
check, record the elapsed time, then delete the namespace and the content object. Both
were created with policies that leave the original snapshot alone; check that it is still
listed before you finish.

## Restoring in the same namespace

When the restore is the real recovery rather than a test, the PVC above without the
pre-provisioned objects is enough: point `dataSource` at the original `VolumeSnapshot` in
the same namespace and use the data class. Point the workload at the new claim; do not
try to restore over the existing one.
