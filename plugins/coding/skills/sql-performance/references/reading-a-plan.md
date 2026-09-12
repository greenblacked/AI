# Reading a plan node by node

A plan read in the wrong order produces a confident wrong answer. Read it in this order,
on a worked example, in both engines. Read this file when you have a plan in front of you.

## Contents

- [The reading order](#the-reading-order)
- [A worked PostgreSQL example](#a-worked-postgresql-example)
- [The same query in MySQL](#the-same-query-in-mysql)
- [Node types worth recognising](#node-types-worth-recognising)
- [MySQL `type` and `Extra`](#mysql-type-and-extra)
- [Strings to search a plan for first](#strings-to-search-a-plan-for-first)
- [Getting the plan when it only happens in production](#getting-the-plan-when-it-only-happens-in-production)

## The reading order

1. `Planning Time` and `Execution Time`, at the bottom. Planning time that is a large share of the total is a partitioning or plan-cache problem, not a data problem, and nothing in the tree will show it.
2. The deepest, most-indented node. Rows enter the plan there and flow outward.
3. At each node, the estimate is `rows=` in the first parenthesis and the measurement is `rows=` in the `actual` parenthesis. Both are per execution of that node.
4. Walk outward and stop at the first node where those two differ by about tenfold. That is the cause.
5. `loops=N` multiplies the work but not the comparison: total rows through a node is `rows × loops`, while the estimate is still compared against the per-loop `actual rows`.
6. A node's `actual time` includes its children, so its own cost is `(total time × loops)` minus the same product for each child.

## A worked PostgreSQL example

The query: pending orders since the start of last month, with their line items.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, o.total, i.sku, i.quantity
FROM orders o
JOIN order_items i ON i.order_id = o.id
WHERE o.status = 'pending'
  AND o.created_at >= '2026-08-01';
```

```text
Nested Loop  (cost=0.86..3419.24 rows=36 width=48) (actual time=0.121..3874.552 rows=144639 loops=1)
  Buffers: shared hit=148203 read=39122
  ->  Index Scan using orders_created_at_idx on orders o  (cost=0.43..1284.10 rows=12 width=24) (actual time=0.038..91.204 rows=48213 loops=1)
        Index Cond: (created_at >= '2026-08-01 00:00:00+00'::timestamptz)
        Filter: (status = 'pending'::text)
        Rows Removed by Filter: 210544
        Buffers: shared hit=20110 read=38904
  ->  Index Scan using order_items_order_id_idx on order_items i  (cost=0.43..177.60 rows=3 width=24) (actual time=0.061..0.078 rows=3 loops=48213)
        Index Cond: (order_id = o.id)
        Buffers: shared hit=128093 read=218
Planning Time: 0.402 ms
Execution Time: 3912.118 ms
```

**Step 1.** Planning time is 0.4ms against an execution time of 3.9 seconds. The problem is in the tree.

**Step 2 and 3.** The deepest node is the index scan on `orders`. Estimated 12 rows; measured 48,213. That is the first divergence and it is four thousandfold, so stop here — everything above inherits it.

**Step 4, the part that is usually done wrong.** The largest time in the plan belongs to the inner index scan on `order_items`: 0.078ms per loop across 48,213 loops is about 3.76 seconds, which is 96% of the query. It is also entirely blameless. It is an index scan on the correct column returning three rows per call, and there is no version of it that is faster. Its cost exists because the node below it returned four thousand times the rows the planner expected, so the nested loop ran 48,213 times instead of 12. Time points at `order_items`; the cause is in `orders`.

**Why the estimate was wrong.** Two predicates on the same table. PostgreSQL estimates the selectivity of `status = 'pending'` and of `created_at >= ...` separately and multiplies them, which assumes the columns are independent. They are the opposite of independent: orders become non-pending as they age, so almost every pending order is recent. `Rows Removed by Filter: 210544` alongside 48,213 kept rows says the index range was reasonable and the correlated filter is where the estimate went.

**The fix.** Give the planner a cheap path for the predicate as written:

```sql
CREATE INDEX orders_pending_created_idx ON orders (created_at) WHERE status = 'pending';
```

The partial index serves both predicates, is a fraction of the size of the table, and stays in cache when pending orders are a small share of it. The plan changes because this path is cheap, not because the estimate improved — verify that by reading the new plan rather than assuming it.

Be precise about what extended statistics can and cannot do here, because reaching for them first is the common wrong move:

```sql
CREATE STATISTICS orders_status_created (dependencies, mcv) ON status, created_at FROM orders;
ANALYZE orders;
```

Functional dependencies apply to equality clauses, and an MCV list cannot represent a range over a column with hundreds of thousands of distinct values. So this corrects `status = 'pending' AND customer_tier = 'gold'` and leaves `status = 'pending' AND created_at >= …` essentially where it was — measured on PostgreSQL 16, the estimate moved from 92 to 87 against 3,441 actual rows, and raising the statistics target did not help. Extended statistics are for correlated equality predicates; a correlated range wants an index or a rewrite.

The partial index stops helping the day someone queries a different status, which is the trade.

**What to check afterwards.** Re-run with `BUFFERS` and compare `shared read=` between runs: the first execution above did 39,122 physical reads, so part of the 3.9 seconds was cold cache rather than the plan. The honest comparison is second run against second run.

## The same query in MySQL

Classic `EXPLAIN` on the `orders` access, in vertical form:

```text
mysql> EXPLAIN SELECT ... \G
*************************** 1. row ***************************
           id: 1
  select_type: SIMPLE
        table: o
         type: range
possible_keys: orders_created_at_idx,orders_status_idx
          key: orders_created_at_idx
      key_len: 6
          ref: NULL
         rows: 258757
     filtered: 4.63
        Extra: Using index condition; Using where
```

The arithmetic almost nobody does: the estimated rows out of this table is `rows × filtered / 100`, which is 258,757 × 0.0463 ≈ 11,980 — the same wrong estimate of roughly twelve rows that PostgreSQL produced, arrived at the same way. `key_len: 6` is a five-byte `DATETIME` plus one byte because the column is nullable, which confirms only the `created_at` column of the index is being used for the range.

`EXPLAIN ANALYZE` (MySQL 8.0.18 and later) adds the measurement, printing `(cost=... rows=...) (actual time=... rows=... loops=...)` on each line of the `FORMAT=TREE` output. The comparison is the same one: estimated `rows` against actual `rows`, per loop, from the innermost iterator outward. The exact wording of an iterator line varies between 8.0 minor versions, so read the numbers rather than pattern-matching the text.

MySQL has no multi-column statistics, so the PostgreSQL fix has no equivalent. The options are a composite index on `(status, created_at)`, which gives the optimiser a real row estimate for the pair and serves the query directly, or a single-column histogram when the skew is in one column:

```sql
ANALYZE TABLE orders UPDATE HISTOGRAM ON status WITH 32 BUCKETS;
```

## Node types worth recognising

| Node | What it means | When it is the problem |
| --- | --- | --- |
| `Seq Scan` | Every page of the table | Only when the row count returned is a small fraction of the rows read |
| `Index Scan` | Walk the index, fetch each matching heap row | When `loops` is large, or when the heap fetches dominate — a bitmap scan may be cheaper |
| `Index Only Scan` | Answered from the index alone | When `Heap Fetches:` is not near zero, which means the visibility map is stale and it is not index-only in practice |
| `Bitmap Heap Scan` | Collect matching page numbers, then read pages in physical order | When `Heap Blocks: lossy=` is non-zero: `work_mem` was too small to keep exact row bitmaps, so whole pages are rechecked |
| `Nested Loop` | For each outer row, probe the inner side | When the outer estimate is wrong — see the worked example. Correct for a small outer side with an indexed inner |
| `Hash Join` | Build a hash table from one side, probe with the other | When `Batches:` exceeds 1, meaning the hash spilled to disk, or when the build side is the larger relation |
| `Merge Join` | Both inputs in sorted order, walked together | When it forced a sort that spilled; usually a sign the inputs could have been indexed in that order |
| `Materialize` | Cache a subplan's rows for repeated scanning | Rarely the cause, usually a symptom of a nested loop that should be a hash join |
| `Gather` / `Gather Merge` | Parallel workers feeding one leader | When `Workers Launched:` is below `Workers Planned:` — the pool was exhausted and the plan was costed for workers it did not get |
| `Sort` | An explicit sort | `Sort Method: external merge  Disk:` means it spilled; `quicksort Memory:` means it fit |
| `Incremental Sort` | Partially ordered input finished per group | Usually good news: an index provided part of the order |
| `SubPlan` with high `loops` | A correlated subquery run once per row | Frequently the whole problem; rewrite as a join or a lateral |

## MySQL `type` and `Extra`

`type` from best to worst: `const`, `eq_ref`, `ref`, `range`, `index`, `ALL`. `index` is a full scan of the index rather than an efficient lookup, and it only beats `ALL` when the index is covering. `ALL` on a large table with a selective predicate is the finding.

`Extra` values that are routinely misread:

- `Using index` means the query was answered from the index alone — a covering index. It does **not** mean "an index was used"; that is the `key` column.
- `Using index condition` is index condition pushdown: the filter was evaluated in the storage engine rather than the server. Good news.
- `Using where` means rows were filtered after they were read. Combined with a large `rows` estimate it is the MySQL equivalent of PostgreSQL's `Rows Removed by Filter`.
- `Using temporary` and `Using filesort` mean an intermediate table and a sort; on a large result they are where the time is.
- `Using join buffer (hash join)` means there was no usable index on the join column.

An InnoDB secondary index implicitly contains the primary key, so primary-key columns are covered for free — a secondary index on `(customer_id)` answers `SELECT id FROM orders WHERE customer_id = ?` without touching the table.

## Strings to search a plan for first

Before reading the tree in detail, search it. Each of these names a specific fault:

- `Rows Removed by Filter` — work done and thrown away.
- `Heap Fetches` — an index-only scan that is not.
- `lossy=` — the bitmap did not fit in `work_mem`.
- `external merge` or `Disk:` — a sort spilled.
- `Batches:` followed by anything but 1 — a hash spilled.
- `loops=` with a large number — check the node below it, not this one.
- `Workers Launched: 0` — planned parallel, ran serial.
- `$1`, `$2` in a condition — a generic plan, planned without the parameter values.
- `never executed` — a branch the plan did not need; useful for confirming a partition or a `LIMIT` did its job.

## Getting the plan when it only happens in production

`auto_explain` captures the plan for the parameters that were actually slow:

```sql
LOAD 'auto_explain';                          -- session; use session_preload_libraries to persist
SET auto_explain.log_min_duration = '500ms';
SET auto_explain.log_analyze = on;            -- adds per-node instrumentation overhead
SET auto_explain.log_buffers = on;
```

Turn `log_analyze` on for a window rather than leaving it on, because the timing instrumentation is charged to every statement it captures.

On PostgreSQL 16 and later, `EXPLAIN (GENERIC_PLAN) SELECT ... WHERE id = $1;` plans a parameterised statement without executing it and without needing values, which is how to see the generic plan that a prepared statement switched to. Before 16, reproduce it with `PREPARE` and six `EXECUTE` calls.
