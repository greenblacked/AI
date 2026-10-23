# Bloat and vacuum queries

Read-only queries for steps 1 and 3. Run them as a role that can read the statistics
views; `pgstattuple` needs `CREATE EXTENSION pgstattuple;` once per database.

## Contents

- [Per-table dead tuples and vacuum history](#per-table-dead-tuples-and-vacuum-history)
- [Measured waste](#measured-waste)
- [HOT update ratio](#hot-update-ratio)
- [Running vacuums](#running-vacuums)
- [Settings in force](#settings-in-force)
- [Reading the result](#reading-the-result)

## Per-table dead tuples and vacuum history

```sql
SELECT relname, n_live_tup, n_dead_tup, n_mod_since_analyze,
       last_vacuum, last_autovacuum, vacuum_count, autovacuum_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 20;
```

Counters reset on a crash or a statistics reset, so a zero `autovacuum_count` on an old
table can mean the counters are new. Check `pg_stat_database.stats_reset`.

## Measured waste

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT table_len, scanned_percent, approx_tuple_percent,
       dead_tuple_percent, approx_free_percent
FROM pgstattuple_approx('public.big_table');
SELECT * FROM pgstatindex('public.big_table_pkey');
```

`pgstattuple_approx` scans the pages not marked all-visible exactly and estimates the
free space on the all-visible rest from the free space map. `approx_free_percent` is space already reusable inside the file;
`dead_tuple_percent` is space vacuum has not yet reclaimed. A large free percentage with a
small dead percentage means vacuum is fine and the file needs a rebuild (step 5). For an
index, `avg_leaf_density` well below 90 on a default btree, or high `leaf_fragmentation`,
justifies `REINDEX INDEX CONCURRENTLY`.

## HOT update ratio

```sql
SELECT relname, n_tup_upd, n_tup_hot_upd,
       round(100.0 * n_tup_hot_upd / nullif(n_tup_upd, 0), 1) AS hot_pct
FROM pg_stat_user_tables WHERE n_tup_upd > 10000 ORDER BY n_tup_upd DESC LIMIT 20;
```

A hot table with a low `hot_pct` is rewriting index entries on every update. Find which
indexed column changes, and either stop updating it or drop the index if it is not needed.

## Running vacuums

```sql
SELECT p.pid, p.relid::regclass AS tbl, p.phase, p.heap_blks_total,
       p.heap_blks_scanned, p.heap_blks_vacuumed, p.index_vacuum_count,
       now() - a.xact_start AS running_for, a.query
FROM pg_stat_progress_vacuum p JOIN pg_stat_activity a USING (pid);
```

`index_vacuum_count` above 1 means the dead-tuple list overflowed memory and the indexes
were scanned more than once. A query beginning `autovacuum: ... (to prevent wraparound)`
is a freeze run: leave it alone and go to `xid-wraparound-defense`.

## Settings in force

```sql
SELECT name, setting, unit, source FROM pg_settings
WHERE name LIKE 'autovacuum%' OR name IN ('vacuum_cost_limit','vacuum_cost_delay',
  'maintenance_work_mem','idle_in_transaction_session_timeout');
SELECT relname, reloptions FROM pg_class WHERE reloptions IS NOT NULL;
```

The second query lists tables that already carry per-table overrides, so you do not
overwrite or duplicate someone's earlier tuning.

## Reading the result

| Reading | Meaning | Next step |
| --- | --- | --- |
| High dead tuples, recent autovacuum, oldest xmin is old | Horizon pinned | Step 2 |
| High dead tuples, old autovacuum, horizon recent | Vacuum too late or throttled | Steps 3 and 4 |
| Low dead tuples, high free percent | Space not returned | Step 5 |
| Low hot_pct on a hot table | Indexed column updates | Step 4, fillfactor and indexes |
| Bloat returns within weeks | Workload pattern | Step 6 |
