# Diagnostic queries

Reference for steps 1, 2 and 6. All queries read system tables.

## Contents

- [Active parts by partition](#active-parts-by-partition)
- [Merges in flight](#merges-in-flight)
- [Insert pattern from the part log](#insert-pattern-from-the-part-log)
- [Mutations](#mutations)
- [Settings to read](#settings-to-read)

## Active parts by partition

```sql
SELECT partition, count() AS parts, sum(rows) AS rows,
       round(avg(rows)) AS avg_rows_per_part
FROM system.parts
WHERE active AND database = 'db' AND table = 'events'
GROUP BY partition
ORDER BY parts DESC
LIMIT 20;
```

A low average rows per part with a high part count points to tiny inserts. Many
partitions each holding a handful of parts points to partitioning.

## Merges in flight

```sql
SELECT database, table, elapsed, round(progress, 3) AS progress,
       num_parts, formatReadableSize(total_size_bytes_compressed) AS size
FROM system.merges
ORDER BY elapsed DESC;
```

No rows while parts pile up suggests merges are not being scheduled (disk space, the
background pool or a stuck mutation). Long merges on large parts suggest the table is
simply too heavy for the merge capacity.

## Insert pattern from the part log

```sql
SELECT toStartOfMinute(event_time) AS minute,
       countIf(event_type = 'NewPart') AS new_parts,
       round(avgIf(rows, event_type = 'NewPart')) AS avg_rows,
       countIf(event_type = 'MergeParts') AS merges
FROM system.part_log
WHERE database = 'db' AND table = 'events' AND event_time > now() - INTERVAL 1 HOUR
GROUP BY minute
ORDER BY minute;
```

New parts per minute far above 60 on one table, with a small average row count, is the
insert pattern problem. The part log must be enabled in the server configuration; if the
table does not exist, the server is not recording it.

## Mutations

```sql
SELECT database, table, mutation_id, command, create_time, parts_to_do, latest_fail_reason
FROM system.mutations
WHERE NOT is_done
ORDER BY create_time;
```

A mutation with `latest_fail_reason` set will retry and keep working; fix or kill it
(`KILL MUTATION`) as a person decides, not automatically.

## Settings to read

```sql
SELECT name, value FROM system.merge_tree_settings
WHERE name IN ('parts_to_delay_insert', 'parts_to_throw_insert', 'max_parts_in_total');
SELECT name, value FROM system.settings
WHERE name IN ('async_insert', 'wait_for_async_insert', 'async_insert_busy_timeout_ms',
               'max_partitions_per_insert_block');
```

Table-level overrides, set in the `CREATE TABLE ... SETTINGS` clause, appear in
`SHOW CREATE TABLE`. Read both before concluding what the effective threshold is.
