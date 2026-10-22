# Partition conversion

Read this when you are ready to convert a live table and need the statements in order.

## PostgreSQL: attach the old table as the first partition

```sql
-- 1. New parent, same shape, key-inclusive primary key. LIKE does not copy an identity
--    column's generator unless INCLUDING IDENTITY is added, so add it for identity keys.
CREATE TABLE events_new (LIKE events INCLUDING DEFAULTS INCLUDING CONSTRAINTS)
  PARTITION BY RANGE (created_at);
ALTER TABLE events_new ADD PRIMARY KEY (id, created_at);

-- 2. Prove the old table's range without a blocking scan.
ALTER TABLE events ADD CONSTRAINT events_range
  CHECK (created_at >= '2020-01-01' AND created_at < '2026-11-01') NOT VALID;
ALTER TABLE events VALIDATE CONSTRAINT events_range;

-- 3. The parent's primary key needs created_at NOT NULL; a range CHECK does not prove it.
ALTER TABLE events ADD CONSTRAINT events_created_nn
  CHECK (created_at IS NOT NULL) NOT VALID;
ALTER TABLE events VALIDATE CONSTRAINT events_created_nn;
ALTER TABLE events ALTER COLUMN created_at SET NOT NULL;  -- uses the CHECK, no scan
ALTER TABLE events DROP CONSTRAINT events_created_nn;

-- 4. Build the matching key concurrently. Attach reuses a partition index only if it backs
--    a primary key constraint, so a plain unique index is not enough.
CREATE UNIQUE INDEX CONCURRENTLY events_pk2 ON events (id, created_at);

-- 5. Promote it, then rename and attach, in one short transaction. Foreign keys that
--    reference events(id) block the DROP CONSTRAINT: drop them first and recreate them
--    against the new key (or the application) once the swap is done.
SET lock_timeout = '2s';
BEGIN;
ALTER TABLE events DROP CONSTRAINT events_pkey;
ALTER TABLE events ADD CONSTRAINT events_pkey_new PRIMARY KEY USING INDEX events_pk2;
ALTER TABLE events RENAME TO events_2020_2026;
ALTER TABLE events_new RENAME TO events;
ALTER TABLE events ATTACH PARTITION events_2020_2026
  FOR VALUES FROM ('2020-01-01') TO ('2026-11-01');
COMMIT;
ALTER TABLE events_2020_2026 DROP CONSTRAINT events_range;
```

Rehearse the whole sequence on a scratch copy before production. Create partitions for the current and following periods before the swap so inserts have somewhere to go. The attach holds an exclusive lock on the old table briefly; test the duration on a copy and keep the transaction short.

## Check pruning

```sql
EXPLAIN (ANALYZE, COSTS OFF) SELECT count(*) FROM events WHERE created_at >= now() - interval '1 day';
```

Look for the scanned partitions list, and `Subplans Removed` for run-time pruning.

## Retention

```sql
ALTER TABLE events DETACH PARTITION events_2020_01 CONCURRENTLY;
-- archive, then
DROP TABLE events_2020_01;
```

A detach that was interrupted leaves the partition marked pending; finish it with `ALTER TABLE ... DETACH PARTITION ... FINALIZE`.

## Rows in the default partition

```sql
SELECT count(*) FROM events_default;
```

Alarm on a non-zero count. Create the missing partition, then move rows: detach the default, create the partition, insert the affected rows from the default, delete those rows from the detached default (otherwise reattaching fails because it still holds rows inside the new range), and reattach.

## MySQL

On a TIMESTAMP column, `TO_DAYS(created_at)` is rejected as a partitioning function; use `UNIX_TIMESTAMP(created_at)` with integer boundaries instead. The example below suits a DATE or DATETIME column.

```sql
ALTER TABLE events PARTITION BY RANGE (TO_DAYS(created_at)) (
  PARTITION p202610 VALUES LESS THAN (TO_DAYS('2026-11-01')),
  PARTITION pmax VALUES LESS THAN MAXVALUE);
ALTER TABLE events REORGANIZE PARTITION pmax INTO (
  PARTITION p202611 VALUES LESS THAN (TO_DAYS('2026-12-01')),
  PARTITION pmax VALUES LESS THAN MAXVALUE);
-- Retention is these two statements together, in this order: exchange the data out into an
-- empty, non-partitioned table of identical structure, then drop the now-empty partition.
ALTER TABLE events EXCHANGE PARTITION p202610 WITH TABLE events_archive;
ALTER TABLE events DROP PARTITION p202610;
```

The primary key must contain `created_at`. Keep `pmax` empty by reorganising it ahead of time, as above. The first statement rebuilds the whole table.
