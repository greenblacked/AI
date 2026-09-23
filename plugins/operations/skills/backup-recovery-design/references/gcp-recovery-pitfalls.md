# Google Cloud recovery pitfalls

Use these checks only for Google Cloud designs. Verify current product documentation and
the resource's actual configuration before approving a claim.

## Storage retention is layered

Cloud Storage soft delete retains recently deleted objects and buckets for a configured
duration; it is distinct from Object Versioning and retention policies. A bucket
retention policy prevents deletion or replacement until an object's retention age is
met. Locking that policy with Bucket Lock is irreversible, so validate duration, privacy
deletion and cost before locking it. These controls do not by themselves create an
independent administrator or project boundary.

Sources: [Soft delete](https://cloud.google.com/storage/docs/soft-delete) and
[Bucket Lock](https://cloud.google.com/storage/docs/bucket-lock).

## Snapshot consistency follows the workload

Compute Engine snapshots are incremental and provide crash-consistent protection for
Persistent Disk. Application-consistent snapshots require the workload to quiesce or use
documented guest-flush handling. For a database or a transaction spanning disks, specify
the application boundary and validate recovery rather than assuming simultaneous API
requests create a consistent set.

Source: [Create Linux application consistent disk snapshots](https://docs.cloud.google.com/compute/docs/disks/creating-linux-application-consistent-pd-snapshots).

## Location and recovery scope must match

Cloud SQL backup location can be configured and does not automatically prove the whole
service survives the selected regional failure. Record backup location, database
edition and point-in-time recovery settings, then include networking, identity, keys,
quotas and dependent services in the regional recovery graph.

Source: [Cloud SQL backups](https://cloud.google.com/sql/docs/mysql/backup-recovery/backups).

## Customer-managed keys add a recovery dependency

Cloud KMS key material is not a substitute for a separately designed recovery path.
Disabling or destroying a key can make protected data unavailable, and key location and
IAM must remain usable in the target scope. Separate key administration from backup
administration, protect against premature destruction, and prove the recovery identity
can use the key without production SSO or network dependencies.

Sources: [Cloud KMS key states](https://cloud.google.com/kms/docs/key-states) and
[Cloud KMS locations](https://docs.cloud.google.com/kms/docs/locations).

## Project separation needs organisational design

A second project can reduce coupling only when its IAM, organisation policies, billing,
keys and recovery roles do not inherit the same destructive path. Document who can alter
retention, delete projects, disable billing, change keys and impersonate recovery
principals. Keep audit evidence in a scope that remains available if the workload project
is lost.

Source: [Google Cloud security foundations guide](https://cloud.google.com/architecture/security-foundations).
