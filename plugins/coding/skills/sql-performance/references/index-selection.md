# Index selection

An index is a permanent cost paid on every write in exchange for a read that may or may not
need it. Read this file before adding, extending or dropping one.

## Contents

- [The decision, in order](#the-decision-in-order)
- [Column order](#column-order)
- [Covering indexes and index-only scans](#covering-indexes-and-index-only-scans)
- [Partial indexes](#partial-indexes)
- [Expression, prefix and text indexes](#expression-prefix-and-text-indexes)
- [Cardinality: when an index earns nothing](#cardinality-when-an-index-earns-nothing)
- [What an index costs to carry](#what-an-index-costs-to-carry)
- [Why the planner is ignoring your index](#why-the-planner-is-ignoring-your-index)
- [Finding indexes that are not earning their keep](#finding-indexes-that-are-not-earning-their-keep)
- [Before you ship it](#before-you-ship-it)

## The decision, in order

1. Is the estimate wrong? Fix statistics first. An index added to compensate for a bad estimate is a second problem on top of the first, and the planner may not use it anyway.
2. Can an existing index be extended by one column instead? Extending `(customer_id)` to `(customer_id, created_at)` costs one index, not two, and the original queries still work because the old columns remain a leading prefix.
3. How selective is the predicate on production data? Under about 1% of rows, an index is almost always right. Above about 20%, a sequential scan usually wins and the index will sit unused.
4. What does it cost to write? Rows per second into the table, multiplied by the index count, is the number to state before adding another.
5. Is the query on a path anyone waits on? An index for a nightly report is usually the wrong trade.

## Column order

A b-tree is sorted by the whole tuple, in order. That single fact decides everything below.

An index on `(a, b, c)` can serve:

- `WHERE a = ?`
- `WHERE a = ? AND b = ?`
- `WHERE a = ? AND b = ? AND c = ?`
- `WHERE a = ? AND b = ? ORDER BY c`
- `WHERE a = ? AND b > ?` — as a range on `b`, with `c` no longer usable for ordering or filtering

It cannot serve `WHERE b = ?` or `WHERE c = ?` on their own. PostgreSQL will occasionally choose a full scan of the index for a non-leading column, and it does so because it is marginally cheaper than a table scan, not because the index works — the fix is still a different index.

The rule: **equality columns first, then the single range column, then the columns you sort by.** A range predicate exhausts the index's usable ordering, so everything after it is filtered rather than sought. With `WHERE tenant_id = ? AND created_at > ? ORDER BY id`, the index is `(tenant_id, created_at)`, and adding `id` to it does nothing for the sort because `created_at` is a range.

Direction matters only for multi-column sorts. `ORDER BY a DESC, b DESC` is served by an index on `(a, b)` scanned backwards; `ORDER BY a DESC, b ASC` is not, and needs `(a DESC, b ASC)` in PostgreSQL. MySQL supports descending indexes from 8.0; before that the syntax was accepted and ignored, which is a quiet way to lose a sort.

The reason to get this right on the first attempt is that a redundant index is hard to remove later: nobody can prove which query needs it, so it stays.

## Covering indexes and index-only scans

PostgreSQL:

```sql
CREATE INDEX orders_customer_idx ON orders (customer_id) INCLUDE (total, status);
```

`INCLUDE` (PostgreSQL 11 and later) stores extra columns in the leaf pages without making them part of the sort key, so the index stays narrow for seeking and still answers the query. Verify it worked by finding `Index Only Scan` in the plan with `Heap Fetches: 0`. A non-zero heap-fetch count means the visibility map is stale — the scan must check each row's visibility in the table, and the advantage is gone. `VACUUM orders;` and check that autovacuum reaches the table often enough; on an append-heavy table it often does not.

MySQL: `Extra: Using index` is the same thing. Because an InnoDB secondary index already stores the primary key, primary-key columns are covered at no cost. There is no `INCLUDE`; extra columns have to be part of the key, which makes the index wider and the seeks more expensive, so the trade has to be worth it.

Covering is what makes `SELECT *` expensive in a hot path: adding one unindexed column to the select list turns an index-only scan into an index scan plus a heap fetch per row.

## Partial indexes

PostgreSQL only:

```sql
CREATE INDEX jobs_pending_idx ON jobs (created_at) WHERE state = 'pending';
```

On a queue table where 0.3% of rows are pending, this index is small enough to stay in cache permanently, and it gives the planner an accurate row estimate because the count comes from the index rather than from multiplied selectivities. It is the right answer for queue tables, soft-deleted rows (`WHERE deleted_at IS NULL`), and any predicate that is both constant and highly selective.

The predicate must be provably implied by the query's `WHERE` clause for the index to be used. `WHERE state = 'pending'` matches; `WHERE state = $1` with a parameter does not, even when the parameter is `'pending'`, because the planner cannot prove it at plan time.

A unique partial index also expresses a constraint nothing else can: `CREATE UNIQUE INDEX ON subscriptions (customer_id) WHERE status = 'active'` permits one active subscription per customer and any number of cancelled ones.

MySQL has no partial index. The usual workaround is a generated column holding the value only for the rows of interest and null otherwise, with an ordinary index on it. InnoDB still stores an index entry for every row including the nulls, so this narrows the index rather than shortening it, and the benefit is a fraction of a real partial index.

## Expression, prefix and text indexes

A predicate that wraps a column in a function cannot use an index on that column. `WHERE lower(email) = 'a@b.com'` needs the index built on the same expression:

```sql
CREATE INDEX users_lower_email_idx ON users (lower(email));            -- PostgreSQL
ALTER TABLE users ADD INDEX ((lower(email)));                          -- MySQL 8.0.13+
```

MySQL implements a functional index as a hidden generated column, so the expression must be deterministic; before 8.0.13 the workaround was an explicit generated column with an ordinary index on it.

Prefix indexes are MySQL-only: `INDEX (url(64))` indexes the first 64 characters. It keeps a long-text index small, and it cannot be used as a covering index, because the index does not hold the whole value.

`LIKE 'prefix%'` uses a b-tree only when the collation sorts the way the pattern match compares. In PostgreSQL, on a database with any non-C collation, that requires an explicit operator class:

```sql
CREATE INDEX docs_path_prefix_idx ON docs (path text_pattern_ops);
```

`LIKE '%middle%'` cannot use a b-tree at all in either engine. PostgreSQL answers it with trigrams:

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX docs_body_trgm_idx ON docs USING gin (body gin_trgm_ops);
```

That index is large and slow to build, so it is worth it for search and not for one admin screen. Full-text search is a different index again (`tsvector` with GIN in PostgreSQL, `FULLTEXT` in MySQL) and a different query; reaching for it to fix a `LIKE` is a rewrite, not an index change.

## Cardinality: when an index earns nothing

An index on a column with three distinct values matches roughly a third of the table for any query. The planner will decline it and be right, and the index will still be maintained on every write. The same applies to a boolean, to a `status` with an even distribution, and to any column where the most common value covers a large share of rows.

It is worth something in exactly three shapes:

- As the leading column of a composite index whose later columns are selective: `(status, created_at)` is useful even though `status` alone is not.
- As the predicate of a PostgreSQL partial index on the rare value.
- When the distribution is skewed and the query asks for the rare value — a `status` that is 99.7% `done` and 0.3% `failed` is low-cardinality and highly selective for `failed`. PostgreSQL will get this right from the most-common-values list if statistics are current; MySQL needs a histogram (`ANALYZE TABLE t UPDATE HISTOGRAM ON status WITH 32 BUCKETS`).

## What an index costs to carry

- Every `INSERT` and `DELETE` updates every index on the table. Every `UPDATE` updates the indexes whose columns it touches.
- In PostgreSQL the sharper cost is heap-only-tuple updates. An `UPDATE` that touches no indexed column and finds free space on its own page writes the new row version on that page and updates no index at all. Indexing a frequently-updated column removes that, so every update writes to every index and leaves dead tuples behind for autovacuum. A `last_seen_at` column updated on each request is the classic one to leave unindexed.
- Indexes consume cache. Check the size before adding: `SELECT pg_size_pretty(pg_relation_size('orders_customer_idx'));` in PostgreSQL; in MySQL, `INDEX_LENGTH` in `information_schema.tables` gives the total per table and `mysql.innodb_index_stats` rows with `stat_name = 'size'` give the page count per index. An index larger than the memory you can spare will itself be read from disk.
- Each index gives the planner another path to cost, and near-duplicate indexes make it more likely to pick the wrong one.
- In MySQL, a wide or random primary key is multiplied across every secondary index, because each secondary entry stores the primary key. A random UUID primary key inflates every index on the table and scatters insert positions across the clustered index.

## Why the planner is ignoring your index

Work down this list; the last entry is more often the answer than the rest combined.

1. The leading column is not in the predicate. See [Column order](#column-order).
2. The column is wrapped in a function or an implicit cast. Check the plan's `Index Cond` for a cast that is not in your SQL.
3. The index expression does not match the query's expression exactly.
4. The collation or operator class is wrong for the operator — `LIKE` on a non-C collation without `text_pattern_ops`.
5. Statistics are stale, so the planner thinks the table is small enough not to bother. `ANALYZE` and re-check.
6. The index is invalid: in PostgreSQL, `SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;` finds indexes left behind by a failed `CREATE INDEX CONCURRENTLY`. They are maintained on write and used by nothing.
7. The predicate is not sargable in a way that is easy to miss — `NOT IN` against a subquery that can produce nulls, or `OR` across two columns where neither branch alone can be indexed.
8. The planner costed it and the sequential scan is cheaper. Confirm with `SET enable_seqscan = off;` and compare the estimated cost of the two plans. If the index plan is genuinely more expensive, the index is not the answer.

## Finding indexes that are not earning their keep

PostgreSQL:

```sql
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY idx_scan, pg_relation_size(indexrelid) DESC;
```

Two traps before dropping anything. Counters are cumulative since the last `pg_stat_reset()` or the last restore, so a young counter proves nothing; and each replica keeps its own counters, so an index unused on the primary may be carrying every read on a replica. Also exclude indexes backing a primary key, a unique constraint or a foreign key — those are constraints, not optimisations.

MySQL: `sys.schema_unused_indexes` lists indexes `performance_schema` has never seen used, and `sys.schema_redundant_indexes` lists those whose columns are a leading prefix of another index. The same caution about the observation window applies.

In both engines, an index whose columns are a leading prefix of another index's columns is redundant by definition: `(a)` is contained in `(a, b)`. Dropping it is one of the few safe index changes.

## Before you ship it

- Verify against production-like data, not a development dump. The plan shape changes with volume.
- Name the write cost you accepted, in the change description.
- Build it without locking the table: `CREATE INDEX CONCURRENTLY` in PostgreSQL, an online DDL or `gh-ost`/`pt-online-schema-change` in MySQL. That is `db-migration`'s subject, and the reason the index decision and the index deployment are two different pieces of work.
- After it is live, confirm it is used. An index that was going to make the query fast and is not being scanned is a regression with a plausible story attached.
