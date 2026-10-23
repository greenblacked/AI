# Method and rollback

Read this at steps 4, 5 and 8: the commands for each method, what each leaves you to roll
back to, and the sheet the rehearsal fills in.

## Contents

- [pg_upgrade](#pg_upgrade)
- [PostgreSQL logical replication](#postgresql-logical-replication)
- [Managed services](#managed-services)
- [MySQL](#mysql)
- [Rollback window by method](#rollback-window-by-method)
- [Rehearsal timing sheet](#rehearsal-timing-sheet)

## pg_upgrade

Initialise the target cluster with the same encoding, locale and checksum setting as the
old one, stop the old server, then:

```bash
pg_upgrade --old-bindir="$OLD_BIN" --new-bindir="$NEW_BIN" \
  --old-datadir="$OLD_DATA" --new-datadir="$NEW_DATA" \
  --link --jobs="$JOBS"
```

| Mode | Duration | Old cluster afterwards |
| --- | --- | --- |
| `--copy` (default) | Proportional to data size | Intact and startable |
| `--clone` | Near link speed on file systems that support reflinks | Intact and startable |
| `--link` | Seconds to minutes, barely data-dependent | Unsafe to start once the new server has started |

Streaming standbys do not upgrade themselves. Either follow the standby procedure in the
`pg_upgrade` documentation, which must run before the new primary starts, or rebuild
each standby from the new primary; time whichever you choose in rehearsal, because the
cluster runs without a replica until it is done.

## PostgreSQL logical replication

The new-version cluster subscribes to the old one, catches up, and becomes primary at a
short switch. Requirements and gaps:

- `wal_level = logical` on the old primary, which needs a restart if it is not set.
- Load the schema on the target first (`pg_dump --schema-only`), then:

  ```sql
  -- on the old primary
  CREATE PUBLICATION upgrade_pub FOR ALL TABLES;
  -- on the new cluster
  CREATE SUBSCRIPTION upgrade_sub CONNECTION 'host=old-primary dbname=app user=replicator'
    PUBLICATION upgrade_pub;
  ```

- DDL is not replicated: freeze schema changes from subscription to switch.
- Sequence values are not replicated: at the switch, set each sequence on the new
  cluster past the old value with `setval`.
- Large objects are not replicated.
- Every table that receives updates or deletes needs a primary key or a replica
  identity, or those changes fail on the publisher.
- The initial copy of a large database takes hours and holds a slot on the old primary;
  watch the old primary's disk while it runs.

At the switch: stop writes, confirm the subscriber has replayed everything the publisher
wrote, set sequences, repoint the application. For a rollback that keeps post-switch
writes, create a publication on the new cluster and a subscription on the old one before
reopening writes.

## Managed services

| Service | Method | Command or mechanism |
| --- | --- | --- |
| Amazon RDS and Aurora | In place | `aws rds modify-db-instance` (or `modify-db-cluster` for Aurora) with `--engine-version`, `--allow-major-version-upgrade`, and a parameter group for the target family; take a manual snapshot first |
| Amazon RDS | Blue/Green Deployments | `aws rds create-blue-green-deployment --blue-green-deployment-name "$NAME" --source "$ARN" --target-engine-version "$TARGET"`, then `aws rds switchover-blue-green-deployment --blue-green-deployment-identifier "$BGD_ID"`; PostgreSQL needs logical replication enabled on the source, with the logical-replication gaps above |
| Cloud SQL | In place | `gcloud sql instances patch "$INSTANCE" --database-version=POSTGRES_17` (or the MySQL equivalent) |
| Azure Database for PostgreSQL flexible server | In place | `az postgres flexible-server upgrade --name "$SERVER" --resource-group "$RG" --version 17` |

Rehearse on a clone or snapshot restore of the production instance, not on a fresh
instance: the managed upgrade's duration depends on the data, the extensions and the
instance class, and the provider's pre-upgrade checks run against what is actually
there.

## MySQL

- **In place.** Stop the server cleanly, replace the binaries, start it; since 8.0.16
  the server upgrades the data dictionary and system tables itself at startup. There is
  no in-place downgrade, so the rollback is a backup or a kept instance.
- **Replica on the target version.** Replication from a source to a replica one series
  newer is supported. Build a replica on the target, let it catch up and bake under
  read traffic, then promote it in a short switch. The old primary, made read-only with
  `super_read_only=ON`, is the rollback until writes on the new one would be lost.

## Rollback window by method

| Method | Rollback mechanism | Point of no return |
| --- | --- | --- |
| `pg_upgrade --copy` or `--clone` | Start the old cluster | First write on the new cluster that you are not willing to lose |
| `pg_upgrade --link` | Snapshot or standby kept on the old version | Same, and restoring a snapshot costs its own duration |
| Logical replication without reverse | Repoint to the old cluster | First write on the new cluster |
| Logical replication with reverse subscription | Repoint to the old cluster | None while reverse replication runs |
| RDS Blue/Green | Old instances remain, renamed, but receive no writes after switchover | First write after switchover |
| Managed in place | Restore the pre-upgrade snapshot | First write after the upgrade |

Write the point of no return into the plan in those words, and give `cutover` the
decision of who may call a rollback before it and what happens after it.

## Rehearsal timing sheet

| Phase | Start | End | Duration | Notes |
| --- | --- | --- | --- | --- |
| Pre-checks on the night | | | | |
| Write stop to upgrade start | | | | |
| Upgrade, link, or replication catch-up and switch | | | | |
| `ANALYZE` first stage complete | | | | |
| Extension updates | | | | |
| Smoke tests passing | | | | |
| Standbys rebuilt | | | | |
| Total write downtime | | | | |

Record the snapshot's size and instance class beside the numbers, so the next upgrade
can tell whether its rehearsal is comparable.
