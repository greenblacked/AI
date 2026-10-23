# Lag and slot queries

Read this at steps 2 to 4: the queries that measure lag and retention on each engine, the
heartbeat pattern, the managed-service metrics, and the arithmetic for retention limits.

## Contents

- [PostgreSQL lag](#postgresql-lag)
- [PostgreSQL slots](#postgresql-slots)
- [Replica query conflicts](#replica-query-conflicts)
- [MySQL lag](#mysql-lag)
- [The heartbeat pattern](#the-heartbeat-pattern)
- [Managed-service metrics](#managed-service-metrics)
- [Sizing retention against disk](#sizing-retention-against-disk)

## PostgreSQL lag

On the primary, one row per connected standby:

```sql
SELECT application_name, client_addr, state, sync_state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn)   AS send_lag_bytes,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

A standby missing from this view is not connected at all, which is its own alert. A
standby that has just connected shows NULL in the lag columns, and a comparison with NULL
is never true. PostgreSQL also resets the three lag columns to NULL shortly after a standby
catches up and the primary goes idle, so NULL alone is not a fault. Treat NULL lag as
lagging only when `replay_lag_bytes` is above zero or `state` is not `streaming`;
otherwise alert on byte lag or the heartbeat. On a standby:

```sql
SELECT pg_last_wal_receive_lsn() AS received,
       pg_last_wal_replay_lsn()  AS replayed,
       pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()) AS apply_backlog_bytes,
       now() - pg_last_xact_replay_timestamp() AS since_last_replayed_commit;
```

`since_last_replayed_commit` grows while the primary has no write traffic, so it pages
at night on a healthy replica unless it is read alongside byte lag or a heartbeat.

For logical replication, the slot's `confirmed_flush_lsn` is how far the consumer has
acknowledged; on a native subscriber, `pg_stat_subscription` shows what it has received.

## PostgreSQL slots

```sql
SELECT slot_name, slot_type, database, active, wal_status, safe_wal_size,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_wal
FROM pg_replication_slots
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC NULLS LAST;
```

| Column | Read it as |
| --- | --- |
| `active` false | No consumer is connected; retention grows with every write |
| `wal_status` `reserved` | Within `max_wal_size` |
| `wal_status` `extended` | Retaining beyond it, still safe |
| `wal_status` `unreserved` | About to be lost at the next checkpoint |
| `wal_status` `lost` | The slot can no longer be used; its consumer must re-sync |
| `safe_wal_size` | Bytes that can still be written before the slot is lost; null without a limit |

Settings that bound retention: `max_slot_wal_keep_size` (PostgreSQL 13 and later,
unlimited by default) caps WAL kept for slots; PostgreSQL 18 adds
`idle_replication_slot_timeout`, which invalidates slots inactive for longer than the
set time. A slot is dropped with `pg_drop_replication_slot('name')`, which fails while a
consumer is connected to it.

## Replica query conflicts

A replica can lag because it is waiting for its own queries. With
`hot_standby_feedback` off, replay cancels conflicting queries after
`max_standby_streaming_delay` (30 seconds by default), and `pg_stat_database_conflicts`
counts the cancellations. Raising the delay lets long reports finish and lets lag grow;
turning feedback on stops cancellations and moves the cost to bloat on the primary.
Give long reporting queries their own replica rather than tuning a shared one for both.

## MySQL lag

```sql
SHOW REPLICA STATUS\G
```

Read `Replica_IO_Running` and `Replica_SQL_Running` (both must be `Yes`),
`Last_IO_Error` and `Last_SQL_Error`, and compare `Retrieved_Gtid_Set` with
`Executed_Gtid_Set`: transactions retrieved but not executed are the applier's backlog.
`Seconds_Behind_Source` is the difference between the replica's clock and the timestamp
of the event being applied; it reads zero when the applier is idle even if the receiver
is far behind the source, and `NULL` when a thread has stopped.

For a diagnostic view of applier delay per worker:

```sql
SELECT WORKER_ID,
       TIMESTAMPDIFF(MICROSECOND, LAST_APPLIED_TRANSACTION_ORIGINAL_COMMIT_TIMESTAMP,
                     LAST_APPLIED_TRANSACTION_END_APPLY_TIMESTAMP) / 1000000 AS last_txn_lag_s
FROM performance_schema.replication_applier_status_by_worker;
```

It reports the delay of the last applied transaction and holds that value while idle, so
use the heartbeat below for alerting. To compare positions across servers, the
`GTID_SUBSET()` function tells whether one executed set contains another.

Binary log retention is `binlog_expire_logs_seconds` (30 days by default in 8.0);
`SHOW BINARY LOGS` lists files and sizes.

## The heartbeat pattern

Write a timestamp on the primary every second into a one-row table and read
`now() - ts` on each replica. It measures what the application experiences, end to end,
whatever the engine reports, and it never reads zero on an idle primary because the
heartbeat itself is the traffic. `pt-heartbeat` from Percona Toolkit implements this for
MySQL; on PostgreSQL a scheduled `UPDATE` does the same. Keep clocks synchronised, since
skew becomes apparent lag.

## Managed-service metrics

| Service | Metric | Unit |
| --- | --- | --- |
| Amazon RDS read replica | `ReplicaLag` | Seconds |
| Amazon RDS for PostgreSQL | `OldestReplicationSlotLag` | Bytes of WAL behind for the most-lagging slot |
| Amazon RDS for PostgreSQL | `TransactionLogsDiskUsage` | Bytes used by WAL |
| Amazon RDS | `FreeStorageSpace` | Bytes |
| Amazon Aurora | `AuroraReplicaLag` | Milliseconds |
| Cloud SQL | `database/replication/replica_lag` | Seconds |

RDS storage autoscaling can absorb a stuck slot for a while and then hit its maximum;
it delays the alert rather than removing the need for it.

## Sizing retention against disk

Measure the primary's WAL generation rate at peak by sampling `pg_current_wal_lsn()`
twice and taking `pg_wal_lsn_diff` over the interval. Runway with a stuck slot is free
disk divided by that rate.

| Quantity | Example |
| --- | --- |
| Free disk on the WAL volume | 400 GB |
| Peak WAL rate | 40 GB per hour |
| Runway with a stuck slot | 10 hours |
| Alert when a slot retains | 25% of free disk: about 2.5 hours of WAL, leaving 7.5 hours to act |
| `max_slot_wal_keep_size` | Below free disk minus a working margin, for example 300 GB |

The alert threshold is set by the time it takes a human to be paged, find the consumer
and decide; the cap is set by the point at which losing the slot is better than losing
the primary.
