# Backfilling a large table

How to move millions of rows into a new column without holding a transaction open for
hours, saturating the replicas, or losing the work when the job is killed at 60%. Load this
when writing the backfill step of an expand/contract migration.

## Contents

- [The shape of a correct backfill](#the-shape-of-a-correct-backfill)
- [The driver loop](#the-driver-loop)
- [Choosing the batch size](#choosing-the-batch-size)
- [Throttling on the right signal](#throttling-on-the-right-signal)
- [Resumability and idempotency](#resumability-and-idempotency)
- [Verifying completeness](#verifying-completeness)
- [MySQL notes](#mysql-notes)

## The shape of a correct backfill

Five properties. A backfill missing any one of them will eventually cost an incident:

1. **Bounded.** Each statement touches a fixed, small number of rows.
2. **Committed per batch.** Work already done survives a kill, and vacuum can reclaim as it
   goes rather than after everything.
3. **Keyed on the primary key.** The batch boundary is an index range scan, not a filter
   over the whole table. A backfill driven by `WHERE new_col IS NULL LIMIT 1000` gets
   slower every batch, because it re-scans the rows it already filled.
4. **Throttled on an observed signal**, with replica lag as the primary one.
5. **Resumable and idempotent.** Re-running a batch produces the same result; restarting
   the job resumes from a persisted checkpoint rather than from the beginning.

A single `UPDATE orders SET customer_ref = ...` over the whole table has none of them. It
holds one transaction for the duration, blocks vacuum on that table the entire time,
generates one enormous burst of WAL, replicates as an indivisible chunk that stalls every
replica, and if it is cancelled at hour three, all three hours are rolled back.

## The driver loop

Carry the last processed id forward. The `id > :last_id` predicate is what keeps every
batch the same cost as the first.

```sql
-- One batch, returning the high-water mark so the driver can carry it forward.
WITH batch AS (
  SELECT id FROM orders
  WHERE id > :last_id
  ORDER BY id
  LIMIT :batch_size
)
UPDATE orders o
SET customer_ref = legacy_customer_uuid(o.customer_id)
FROM batch b
WHERE o.id = b.id AND o.customer_ref IS NULL
RETURNING o.id;
```

Take `max(id)` from the returned rows as the next `:last_id`. Note that the `LIMIT` is on
the id selection, not on the update, so a batch whose rows are already filled still
advances the cursor instead of spinning.

Around it:

```python
last_id = load_checkpoint()  # 0 on a first run
while True:
    rows, high_water = run_batch(last_id, batch_size)
    if high_water is None:  # no rows above last_id remain
        break
    last_id = high_water
    save_checkpoint(last_id)  # commit the checkpoint with, or after, the batch
    emit_metric("backfill.rows", rows)
    lag = replica_lag_seconds()
    if lag > LAG_CEILING:
        sleep(min(60, lag))  # back off proportionally, do not just continue
    else:
        sleep(BASE_SLEEP)
```

Run it as a job with a controllable concurrency of one, not as a database migration.
Framework migration runners have deploy-length timeouts and no pause control; a backfill
that runs for six hours belongs in a worker or a one-off task that operators can stop.

## Choosing the batch size

Start at 1000 rows and a 100ms sleep, measure, then tune. The useful target is a batch that
completes in well under a second — long enough to amortise the round trip, short enough
that cancelling costs nothing and that the row locks it holds do not collide with user
traffic.

Rough arithmetic before starting: 400M rows at 5000 rows per batch and 150ms per cycle is
about 3.3 hours of pure work. Add throttling and it is most of a day. Knowing that number
in advance is what stops someone starting a backfill at 17:00 on a Friday.

Larger batches are not faster past a point: they hold more row locks, produce more WAL per
transaction, and increase the chance of deadlocking with application writes. If throughput
matters more than the tail, raise concurrency by splitting the key range across a few
workers rather than by raising the batch size.

## Throttling on the right signal

Rows per second is the progress metric. It is not the throttle signal, because the backfill
is not the thing that gets hurt.

Throttle on, in priority order:

```sql
-- Postgres, from the primary: how far behind each replica is, in bytes and seconds.
SELECT client_addr,
       state,
       pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_bytes,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

```sql
-- Postgres, from the replica: replay delay in seconds.
SELECT now() - pg_last_xact_replay_timestamp() AS replica_lag;
```

Also watch dead tuple accumulation on the table being updated — an `UPDATE` writes a new
row version each time, so a backfill doubles the table's storage as it runs unless vacuum
keeps up:

```sql
SELECT n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables WHERE relname = 'orders';
```

If `n_dead_tup` climbs without autovacuum firing, slow down. Bloat that accumulates during
the backfill does not go away when it finishes, and the table can end up permanently larger
than the data in it.

A ceiling of a few seconds of replica lag is a reasonable default, and it should be
whatever the read path can actually tolerate rather than a number picked from a blog post.
Back off proportionally to the lag rather than pausing for a fixed interval, so a slow
replica slows the backfill smoothly instead of oscillating.

## Resumability and idempotency

- **Checkpoint durably.** Persist the high-water mark in a table, not in the job's memory.
  A pod restart at 60% should resume at 60%.
- **Make the update idempotent.** The `AND customer_ref IS NULL` guard means re-running a
  batch is a no-op, so a checkpoint written slightly before or after the commit is
  survivable either way.
- **Guard against overwriting live writes.** Once dual-write is deployed, new and updated
  rows already have the correct new value. The `IS NULL` guard is what stops the backfill
  overwriting a fresher application write with a stale computed one — which is the classic
  way a backfill corrupts data rather than just being slow.
- **Log the range, not the rows.** One line per batch with the id range, row count and
  duration is enough to reconstruct what happened; logging updated rows individually turns
  the log volume into its own incident.
- **Have a stop switch.** A flag the job checks between batches, so stopping does not
  require killing a process mid-transaction.

## Verifying completeness

"The job finished" is not evidence. Query for the remaining work directly:

```sql
SELECT count(*) FROM orders
WHERE customer_ref IS NULL AND customer_id IS NOT NULL;
```

On a very large table, count in key ranges rather than in one statement, or accept an
estimate from a sampled scan — a full `count(*)` under load is itself a heavy query.

Then check agreement, not just presence. A backfill that populated every row with the wrong
value passes a null check:

```sql
SELECT count(*) FROM orders TABLESAMPLE SYSTEM (1)
WHERE customer_ref IS DISTINCT FROM legacy_customer_uuid(customer_id);
```

Expect zero. Anything else means the transform disagrees with itself on real data, and the
sample is telling you before the read switch does.

Keep the check running as a scheduled job through the dual-write period. It is the only
thing that catches a write path added after the backfill finished that populates the old
column and not the new one.

## MySQL notes

The same loop applies. The differences:

- Lag comes from `SHOW REPLICA STATUS` (`Seconds_Behind_Source`), which is coarse — it
  reports zero right up until it does not. Prefer a heartbeat table written on the primary
  and read on the replica for a real measurement.
- With row-based replication, each batch replicates as its own event set, so batch size
  maps directly to replica burst size.
- `pt-archiver` and the throttling built into `gh-ost` implement this loop already,
  including lag-based back-off. Where the backfill is a straight copy or purge rather than
  a computed transform, use them instead of writing the driver again.
