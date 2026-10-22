# Horizon blockers

What can hold the oldest visible transaction ID back, how to confirm each, and what
ending it costs. Read at step 2 of the workflow.

## Contents

- [The blockers](#the-blockers)
- [A safe order for acting](#a-safe-order-for-acting)
- [Prevention settings](#prevention-settings)

## The blockers

| Blocker | Where to see it | Remedy | Cost or risk |
| --- | --- | --- | --- |
| Long or idle-in-transaction session | `pg_stat_activity` `xact_start`, `backend_xmin`, `state` | Owner ends it; else `pg_terminate_backend(pid)` | Its work rolls back; record pid, query, application name first |
| Inactive or lagging logical slot | `pg_replication_slots` `xmin`, `catalog_xmin`, `active` | Resume the consumer, or `pg_drop_replication_slot` | Dropping loses the consumer's position; it must resync |
| Prepared transaction | `pg_prepared_xacts` | `COMMIT PREPARED` or `ROLLBACK PREPARED` | Needs the coordinator's decision, otherwise data may disagree across systems |
| Standby with feedback | `pg_stat_replication.backend_xmin`; long query on the standby | End or move the query; or turn feedback off | Without feedback, standby queries can be cancelled by replay conflicts |
| Long `ANALYZE` or index build | `pg_stat_activity` (`backend_xmin`, `query`), `pg_stat_progress_create_index` | Wait; each holds its own snapshot for its duration | `CREATE INDEX [CONCURRENTLY]` holds a snapshot horizon; the concurrent form also waits on old snapshots. A lazy `VACUUM` does not pin the horizon |

## A safe order for acting

1. Take the evidence: the rows from the five queries, saved with a timestamp.
2. Start with what is least risky and most idle: sessions `idle in transaction` for hours.
3. Then forgotten prepared transactions and inactive slots, after confirming nobody owns them.
4. Last, the standby feedback, because ending it changes behaviour for people on the replica.
5. Re-read the oldest `backend_xmin` after each step; stop when it is recent.

## Prevention settings

- `idle_in_transaction_session_timeout` set on application roles (not the superuser), to a
  value above the longest legitimate pause between statements.
- `statement_timeout` or a job-level cap for reporting roles that run on the primary.
- `max_slot_wal_keep_size` so an abandoned slot cannot fill the disk; it invalidates the
  slot instead.
- `max_prepared_transactions = 0` unless a transaction manager uses two-phase commit.
- Alert on the age of the oldest `backend_xmin`, on inactive slots, and on any row in
  `pg_prepared_xacts` older than a few minutes.
