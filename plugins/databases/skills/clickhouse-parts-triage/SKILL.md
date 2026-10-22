---
name: clickhouse-parts-triage
description: "Fix ClickHouse too-many-parts errors and merge backlogs by reading system.parts, system.merges and system.part_log before changing anything, then removing the cause in order of frequency: many tiny inserts (batch to tens of thousands to a million rows at about one insert per second per table, or async_insert with wait_for_async_insert so acknowledgements stay honest), a PARTITION BY that is too granular (many partitions touched per insert), and queued mutations on large tables. Raising parts_to_throw_insert only delays failure. Use for \"Too many parts. Merges are processing significantly slower than inserts\", \"inserts rejected\", \"ClickHouse merges backlog\" or \"how should I batch inserts\". Not for which queries drive scan cost (scan-cost-forensics), query speed (sql-performance), relational partitions (table-partitioning) or backfills (safe-backfill)."
allowed-tools: Read, Glob, Grep
---

# ClickHouse Parts Triage

This skill is done when the number of active parts per partition is stable and well below the insert-rejection threshold, the cause (insert pattern, partitioning or mutations) is named and fixed at its source, and the settings raised as a stopgap, if any, have an expiry.

The usual failure is raising `parts_to_throw_insert` until the error goes away. Every insert creates a part on disk; background merges combine parts; when inserts arrive faster than merges can consolidate them, ClickHouse first delays and then rejects inserts. A higher threshold only lets the backlog grow, with slower queries (each part is read separately) and longer merges, until the failure returns at a larger size.

Run queries through the normal permission prompt. Queries in this skill only read system tables; the changes are table and client changes you propose and a person applies.

## Scope

Use for: a rejected-insert error about too many parts, a merge backlog, choosing batch size or async inserts, and partition and sort key choices that cause parts to pile up.

Do not use for: finding which queries drive scan cost, which is `scan-cost-forensics` for spend and `sql-performance` for a single slow query; relational partitioning in a row-store database, which is `table-partitioning`; running a large backfill safely, which is `safe-backfill`.

## Workflow

### 1. Read before changing

The error text reads like `Too many parts (...). Merges are processing significantly slower than inserts`; the count in it and the default threshold differ by version, so quote the message you have and check the table's settings rather than a remembered number. Find where parts are accumulating:

```sql
SELECT database, table, partition, count() AS active_parts, sum(rows) AS rows,
       formatReadableSize(sum(bytes_on_disk)) AS size
FROM system.parts
WHERE active
GROUP BY database, table, partition
ORDER BY active_parts DESC
LIMIT 20;
```

Then see whether merges are running and how long they take (`system.merges`), and how parts arrive over time (`system.part_log`, where `event_type` is `NewPart` for inserts and `MergeParts` for merges). Read `references/diagnostic-queries.md` for the queries.

### 2. Classify the cause

Check in this order, because it is the order of frequency:

1. Many tiny inserts: `NewPart` events with small `rows`, at a high rate per table.
2. Partitioning too granular: parts spread across hundreds of partitions, each small, or single inserts spanning many partitions.
3. Mutations queued on a large table, holding merge capacity.

Fix the first one the evidence supports; do not combine fixes, so the effect is attributable.

### 3. Batch the inserts

Each insert statement creates at least one part per partition it touches. Batch on the client to tens of thousands up to a million rows per insert, at roughly one insert per second per table. Buffer in the application or a queue consumer, not in a table-per-event pattern. Where clients cannot batch (many small producers), use asynchronous inserts: `async_insert = 1` makes the server buffer and flush them as larger parts. Keep `wait_for_async_insert = 1`, the default, so the client is acknowledged only after the data is flushed; setting it to 0 returns success before the data is durable and hides failures, which is a correctness choice, not a tuning one.

### 4. Repair partitioning

`PARTITION BY` exists for data lifecycle (dropping old data cheaply), not for query speed. A key such as a tenant id, or tenant and day, over long retention multiplies the number of partitions, and every insert touching many partitions writes many parts. Judge it by the partition count and by how many partitions one insert spans: day partitions are acceptable when retention keeps the count to tens and each insert lands in the current partition (a 14-day retention with `ttl_only_drop_parts` is an example). Otherwise prefer month, or none. A partition key cannot be changed in place; create a new table with the right key, copy data in large ordered batches, and swap. Hand the copy to `safe-backfill`. The setting `max_partitions_per_insert_block` exists to stop one insert from creating parts in hundreds of partitions; hitting it is the same cause.

### 5. Review the sort key as a read-cost concern

The `ORDER BY` key does not decide whether parts merge; it decides how rows sort inside parts, so it affects compression and how much a query can skip. It is not a cause of too many parts, so review it after the parts count is stable. Put low-cardinality columns first and the high-cardinality column (a timestamp or id) last. A key beginning with a unique id gives each part no locality, so compression is poor and queries read most of the table. Changing it also means a new table.

### 6. Handle mutations

`ALTER TABLE ... UPDATE` and `DELETE` rewrite whole parts. Check `system.mutations` where `is_done = 0` for a queue, and look at long-running ones. Where deletes are the use, prefer lightweight deletes (`DELETE FROM`), which mark rows rather than rewriting parts. Where updates are the use, consider a ReplacingMergeTree and accept the read-side cost of `FINAL` or deduplicating queries; measure that cost first.

### 7. Use the stopgap with an expiry

If production is rejecting inserts now, raising `parts_to_throw_insert` (and `parts_to_delay_insert`) on the table buys time. Write down the date it must be reverted and the fix that replaces it. Do not reach for `OPTIMIZE TABLE ... FINAL` as the fix: it forces a heavy merge and is rarely the answer to an insert pattern problem.

### 8. Verify

After the fix, watch active parts per partition over a day. The number should hover low and flat. Re-run the step 1 query and keep the result with the change.

## Output format

```markdown
## Evidence
[Error text, top partitions by active parts, insert rate and rows per part from the part log.]

## Cause
[Which of the three, with the numbers that show it.]

## Change
[Client batching or async settings, new table definition, mutation changes, stopgap with expiry date.]

## Verification
[Active parts per partition before and after, over what window.]
```

## Anti-patterns

**Raising the throw threshold and moving on.** The backlog still grows; queries slow first.

**async_insert with wait_for_async_insert = 0.** Clients are told success for data that may not be written.

**Day or tenant partitions for query speed.** The primary key does that job; partitions create parts.

**OPTIMIZE FINAL on a schedule.** It rewrites everything to hide an insert pattern.

**Fixing the sort key and batching together.** The result cannot be attributed to either.

## Reference files

- `references/diagnostic-queries.md` - read at steps 1, 2 and 6: queries over `system.parts`, `system.merges`, `system.part_log` and `system.mutations`, and the table-level settings to read.
