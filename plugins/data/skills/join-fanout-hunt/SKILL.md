---
name: join-fanout-hunt
description: "Find why a total is inflated or a row count grew after a join, and fix it at the grain instead of hiding it: write the grain of every input in one sentence, compare COUNT(*) with COUNT(DISTINCT key) after each join while bisecting the query join by join, classify the cause as many-to-many, a dimension not unique on its key (an unfiltered type-2 history table, overlapping validity ranges) or duplicate source rows, and fix by pre-aggregating to the join grain, never by DISTINCT on the output. Use when revenue is 3x too high after adding a join, a model's row count doubled, a SUM disagrees with its source table, or someone proposes SELECT DISTINCT to make the numbers match. Not for a slow query (sql-performance), two dashboards disagreeing on one metric (metric-reconciliation) or designing new tables (schema-design)."
allowed-tools: Read, Grep, Glob
---

# Join Fan-out Hunt

This is finished when you can name the join that multiplies rows, say which input is not at the grain everyone assumed and why, and show the corrected query reproducing the base table's total exactly, with a test that would have failed before the fix.

The usual failure is a `DISTINCT` added to the outer select until the number looks right. It hides the duplicate rows rather than removing their cause, collapses rows that were legitimately identical, does nothing for a `SUM` computed before it, and leaves the next join on the same table to fan out again. A fan-out is a statement that some input has more rows per key than the query assumed; the fix is to make that input match the assumption, before the join.

## Scope

Use for: a total that is a multiple of what it should be after a join, a model whose row count jumped when a table was added, a metric that drifted up when a dimension started keeping history, choosing between `DISTINCT` and a real fix, a total that dropped after a join (the mirror case, found by the same bisection).

Do not use for: a query that is slow rather than wrong, which is `sql-performance`; two dashboards that disagree and nobody knows whose rows differ, which is `metric-reconciliation` (it hands back here when a difference turns out to be join grain); designing the keys of tables that do not exist yet, which is `schema-design`; deduplicating customers that have no shared key across systems, which is `entity-resolution`.

## Workflow

### 1. Fix the right number and the wrong one

Compute the measure from the base table alone, at the report grain, with no joins: that is the number the joined query has to reproduce. Write beside it the inflated number and the ratio between them. An exact integer ratio (2.00, 3.00) usually means every key gained the same number of copies — a dimension carrying one row per currency, region or snapshot date. A ratio like 1.17 means some keys duplicated and most did not — a few customers with two current rows, a replayed day of events.

### 2. State the grain of every input in one sentence

For each table or subquery in the `FROM` and every join: "one row per order", "one row per order line", "one row per customer per validity period". Then prove each sentence with a duplicate check on the key it names:

```sql
SELECT customer_id, COUNT(*) AS n
FROM dim_customer
GROUP BY customer_id
HAVING COUNT(*) > 1
ORDER BY n DESC
LIMIT 20;
```

A grain sentence is a claim until this returns no rows. The input whose check returns rows is the suspect, but continue to step 3: a table that is not unique on its key fans out only when it is joined on that key.

### 3. Bisect the query join by join

Rewrite the query as a chain of CTEs, one join per step, carrying the base table's key through. After each step, compute three numbers:

```sql
SELECT
  COUNT(*)                 AS row_count,
  COUNT(DISTINCT order_id) AS base_keys,
  SUM(amount)              AS measure
FROM step_2;
```

The first step where `row_count` exceeds `base_keys`, or `measure` exceeds the base total, is the fan-out. If the base CTE already has `row_count` above `base_keys`, the source itself carries duplicates and no join is to blame. For a composite key, concatenate or hash its columns where the dialect has no multi-column `COUNT(DISTINCT)`. Read `references/bisect-queries.md` for the full template and the composite-key forms.

### 4. Look at the duplicated rows

Take the five keys with the most rows after the guilty join and select every column of the joined table for them. The column whose value differs between the copies names the grain you missed: `valid_from` means history, `currency` means one row per currency, `_loaded_at` with everything else identical means a replayed load. Write that column down; the fix depends on it.

### 5. Classify the cause

| Class | Signature | Fix |
| --- | --- | --- |
| Many-to-many | Both sides have several rows per join key: orders joined to payments and to shipments on `order_id`, so every payment is repeated per shipment | Aggregate each child to the parent's key, then join the aggregates |
| Dimension not unique on its key | The right side should be one row per key and is not: a type-2 history table joined without a validity predicate, overlapping `valid_from`/`valid_to` ranges, a join on a non-key such as email or name, case or whitespace variants of the key | Join as of the fact's timestamp, or filter to the current row, and repair the dimension so its key is unique; a non-key join needs a real key |
| Duplicate source rows | The base already has more rows than keys before any join: an ingest replay, at-least-once delivery, a union of overlapping extracts | Deduplicate at the first model that reads the source, by its natural key with a stated rule (latest load wins), and tell the producer |

A many-to-many between two facts through a shared dimension is the case most often argued about, because each join alone looks correct. Draw the three tables and their grains before arguing.

### 6. Fix at the join grain

Pre-aggregate the many side to the grain of the join before joining it, or restrict the dimension to one row per key, so the join cannot multiply. When a report genuinely needs measures from two different grains — order totals and line-level discounts on one row — aggregate each to the report's grain separately and join the two results on that grain.

Do not fix with `DISTINCT` on the output or `SUM(DISTINCT amount)`. The first collapses rows that are legitimately identical (two identical items in one basket); the second drops every repeated amount, so two £10 orders count once. Both leave the input that caused it unchanged for the next query.

### 7. Prove the fix and leave a test behind

Rerun step 3's three numbers on the fixed query: `row_count` equals `base_keys` at the report grain, and the measure equals step 1's base total exactly, not approximately. Then add the test that would have caught it: a uniqueness test on the dimension's key (or on key plus `valid_from` for a history table, with a test that ranges do not overlap), and a row-count comparison between the base model and the joined model where the join is meant to preserve rows. Read `references/bisect-queries.md` for the as-of join, the pre-aggregation rewrite and the test definitions.

## Output format

```markdown
## Numbers
Base-table total: [x]. Joined total: [y]. Ratio: [y/x].

## Grains
| Input | Stated grain | Duplicate check |

## Bisection
| Step | Join added | row_count | base_keys | measure |

## Cause
[Class from step 5, the column that differed between copies, five example keys.]

## Fix
[The rewritten join, and why it cannot multiply now.]

## Proof and guard
[Fixed query's numbers against the base total; the tests added.]
```

## Anti-patterns

**`DISTINCT` until it matches.** It treats the symptom on one query. The next query joining the same table fans out again, and identical legitimate rows vanish.

**Trusting the documented grain.** A table described as "one row per customer" that started keeping history last quarter is now one row per customer per change. Run the duplicate check.

**Bisecting by deleting joins from the finished query.** An inner join that drops unmatched rows can offset a fan-out elsewhere, so removing either one changes the total in a way that points at the wrong join. Build up from the base, one join at a time, and measure after each.

**Fixing the dimension in the report.** A `WHERE is_current` in one dashboard leaves every other consumer of the table exposed. Repair the table or publish a current-row view, then use it.

**Calling a close total fixed.** If the corrected total is within a fraction of a per cent of the base, something still duplicates or drops. Fan-out fixes reconcile exactly.

## Reference files

- `references/bisect-queries.md` — read at steps 3, 6 and 7: the CTE bisection template, composite-key counting per dialect, the duplicate-row inspection query, the as-of join for type-2 tables, the pre-aggregation rewrite with a before and after, and uniqueness and row-count test definitions.
