# Restore job skeleton

Read this when writing the job itself: selecting the backup, restoring, waiting, tearing
down, scheduling, and emitting the metrics the alerts read. Commands are shapes to adapt,
not a script to paste; identifiers in capitals are placeholders.

## Contents

- Job shape and exit trap
- Amazon RDS (single instance)
- Amazon Aurora
- Managed restore testing on AWS
- Google Cloud SQL
- Self-hosted PostgreSQL with pgBackRest
- Scheduling
- Metrics and alert rules

## Job shape and exit trap

One script per database, so one failure does not hide another. The trap runs on success,
failure and termination, and the guard refuses to delete anything not tagged as a canary.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

DB_NAME=orders   # one script per database; the name keeps two databases from sharing a target
TARGET="restore-canary-${DB_NAME}-$(date -u +%Y%m%d%H%M%S)"
started=$(date -u +%s)

cleanup() {
  # Delete only what this job created and tagged; see delete_if_canary below.
  delete_if_canary "$TARGET" || echo "teardown failed for $TARGET; sweeper will retry" >&2
}
trap cleanup EXIT

select_backup        # sets BACKUP_ID and BACKUP_TIME, fails if too old
restore_backup       # creates TARGET from BACKUP_ID
wait_until_ready
verify               # runs the four checks in order, fails on the first failure
push_metrics         # only reached when verify succeeded
```

Provider identifiers are short (RDS allows 63 characters of letters, digits and hyphens), so
keep the database name brief. The timestamp means a re-run on the same day does not collide
with a leftover from the first.

Write `delete_if_canary` to read the target's tags or labels from the provider and exit
non-zero unless `purpose=restore-canary` is present. The name pattern alone is not enough:
a bug that sets `TARGET` to an empty string or to a production name must fail closed.

## Amazon RDS (single instance)

Newest available automated snapshot, with its creation time:

```bash
aws rds describe-db-snapshots \
  --db-instance-identifier PROD_INSTANCE --snapshot-type automated \
  --query 'reverse(sort_by(DBSnapshots[?Status==`available`], &SnapshotCreateTime))[0].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output text
```

With no available snapshot the query prints `None`. Treat that as a failed run, not as a
backup with an unparseable time: a loop that compares the printed time to a limit passes
on text it cannot read.

Restore into the isolated subnet group and security group, not publicly accessible, tagged:

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier "$TARGET" \
  --db-snapshot-identifier "$BACKUP_ID" \
  --db-instance-class PROD_CLASS \
  --db-subnet-group-name CANARY_SUBNET_GROUP \
  --vpc-security-group-ids CANARY_SG \
  --no-publicly-accessible \
  --tags Key=purpose,Value=restore-canary
```

To prove point-in-time recovery instead, use `restore-db-instance-to-point-in-time` with
`--source-db-instance-identifier` and either `--use-latest-restorable-time` or
`--restore-time`.

Wait with `aws rds wait db-instance-available --db-instance-identifier "$TARGET"`. The
waiter gives up after a fixed number of polls, so loop over it for a large restore rather
than treating its timeout as a failed restore.

Restored volumes are hydrated from object storage on first read, so the verification scan
is slower than the same scan on production. That time is part of a real recovery; keep it
in the duration.

Teardown:

```bash
aws rds delete-db-instance --db-instance-identifier "$TARGET" \
  --skip-final-snapshot --delete-automated-backups
```

## Amazon Aurora

`aws rds restore-db-cluster-from-snapshot` (or `restore-db-cluster-to-point-in-time`)
creates the cluster with no instances, and a cluster with no instance cannot be queried.
Follow it with `aws rds create-db-instance --db-instance-identifier "$TARGET-1"
--db-cluster-identifier "$TARGET" --db-instance-class PROD_CLASS --engine ENGINE
--tags Key=purpose,Value=restore-canary`, then wait for the instance. Teardown is
two steps in the reverse order: delete the instance, then `delete-db-cluster` with
`--skip-final-snapshot`. The teardown and the sweeper find that instance by its tag and
delete it before the cluster. A sweeper that deletes only instances leaves empty clusters
accumulating.

## Managed restore testing on AWS

AWS Backup offers restore testing plans that restore recovery points on a schedule into
the account and delete them after a retention period, with a validation hook you supply.
It removes the scheduling and teardown work; it does not remove steps 5, 6 and 8 of the
skill. Supply the verification as the validation step, and still push a success timestamp
and alert on its absence, because a plan that stops selecting recovery points does not
page anyone by itself.

## Google Cloud SQL

```bash
gcloud sql backups list --instance=PROD_INSTANCE --limit=5
gcloud sql backups restore BACKUP_ID \
  --restore-instance="$TARGET" --backup-instance=PROD_INSTANCE
```

The restore overwrites the instance named in `--restore-instance`, which must already
exist, in a compatible configuration, with the canary label. This is the command where the
tag guard matters most: the same command with the production name in that flag restores
yesterday's data over production. Create the target in the canary network with no
authorised networks, run the guard against its labels, then restore.

For point-in-time recovery, `gcloud sql instances clone PROD_INSTANCE "$TARGET"
--point-in-time=TIMESTAMP` creates a new instance at that time.

## Self-hosted PostgreSQL with pgBackRest

Restore onto a canary host into an empty data directory:

```bash
pgbackrest --stanza=main --pg1-path=/var/lib/postgresql/canary \
  --type=immediate --target-action=promote restore
```

`--type=immediate` stops at the end of the backup's consistency point, which proves the
base backup; use `--type=time --target=TIMESTAMP` to prove the WAL chain. Before starting
the restored cluster, make sure it cannot archive into the production repository: set the
restore's archive mode to off where your pgBackRest version supports it, or override
`archive_command` in the restored configuration. A restored cluster pushing WAL to the
production stanza confuses the very repository it was restored from.

`pgbackrest verify` checks the repository's files and checksums without restoring; it is a
useful daily addition, not a substitute.

For WAL-G the equivalent is `wal-g backup-fetch DATA_DIR LATEST` followed by recovery
configuration; resolve and log the backup name `LATEST` points at before fetching.

## Scheduling

On Kubernetes, a CronJob with:

| Field | Value | Why |
| --- | --- | --- |
| `concurrencyPolicy` | `Forbid` | Two overlapping restores double cost and fight over the target name |
| `startingDeadlineSeconds` | a few hours | A missed start is skipped rather than run at a surprising time |
| `jobTemplate.spec.backoffLimit` | `0` | A retried restore hides a flaky failure behind a later success |
| `jobTemplate.spec.activeDeadlineSeconds` | the RTO share plus margin | A hung restore is killed, and the absence alert fires |

In a CI scheduler, the same four properties: no overlap, no silent retry, a hard timeout,
and teardown in a step that runs on failure.

## Metrics and alert rules

Metric names, pushed once at the end of a successful run (to a Pushgateway or the
equivalent), labelled by database:

- `restore_canary_last_success_timestamp_seconds`
- `restore_canary_phase_duration_seconds{phase="restore|ready|verify"}`
- `restore_canary_backup_age_seconds` (selection time minus backup completion)
- `restore_canary_recovery_point_age_seconds` (backup completion minus newest restored row)
- `restore_canary_rows_verified`

Alert rules, in Prometheus syntax; thresholds are starting points to adjust:

```yaml
groups:
  - name: restore-canary
    rules:
      - alert: RestoreCanaryStale
        expr: time() - restore_canary_last_success_timestamp_seconds > 30 * 3600
        labels: {severity: ticket}
      - alert: RestoreCanaryNeverReported
        expr: absent(restore_canary_last_success_timestamp_seconds{database="orders"})
        for: 1h
        labels: {severity: ticket}
      - alert: RestoreCanarySlow
        expr: sum by (database) (restore_canary_phase_duration_seconds{phase=~"restore|ready|verify"}) > 0.5 * 7200
        labels: {severity: ticket}
```

The 7200 above stands for the database's RTO share in seconds; set it per database. The
failed-run alert comes from the job runner's own failure notification, carrying the check
that failed and the backup identifier, because a failed run pushes nothing.
