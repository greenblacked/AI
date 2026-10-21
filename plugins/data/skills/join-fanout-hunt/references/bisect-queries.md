# Bisection queries and fixes

## Contents

- The bisection template
- Counting a composite key
- Inspecting the duplicated rows
- The as-of join for a type-2 table
- Overlapping validity ranges
- Pre-aggregating before the join
- Tests that keep it fixed
- The mirror case: a total that dropped

## The bisection template

Carry the base table's key through every step, and add exactly one join per CTE. Union the three numbers from each step into one result so the jump is visible on one screen.

```sql
WITH base AS (
  SELECT o.order_id, o.customer_id, o.ordered_at, o.amount
  FROM orders o
  WHERE o.ordered_at >= '2026-09-01' AND o.ordered_at < '2026-10-01'
),
step_1 AS (
  SELECT b.*, c.segment
  FROM base b
  LEFT JOIN dim_customer c ON c.customer_id = b.customer_id
),
step_2 AS (
  SELECT s.*, p.payment_method
  FROM step_1 s
  LEFT JOIN payments p ON p.order_id = s.order_id
)
SELECT 'base'   AS step, COUNT(*) AS row_count, COUNT(DISTINCT order_id) AS base_keys, SUM(amount) AS measure FROM base
UNION ALL
SELECT 'step_1', COUNT(*), COUNT(DISTINCT order_id), SUM(amount) FROM step_1
UNION ALL
SELECT 'step_2', COUNT(*), COUNT(DISTINCT order_id), SUM(amount) FROM step_2
ORDER BY step;
```

Keep the joins the original query uses — same type, same predicates, same order. A bisection over a tidied version of the query finds the bug in the tidied version.

## Counting a composite key

Where the key is more than one column:

| Dialect | Form |
| --- | --- |
| Snowflake | `COUNT(DISTINCT order_id, line_no)` |
| MySQL | `COUNT(DISTINCT order_id, line_no)` |
| PostgreSQL | `COUNT(DISTINCT (order_id, line_no))` |
| BigQuery | `COUNT(DISTINCT TO_JSON_STRING(STRUCT(order_id, line_no)))` |
| Other dialects | `COUNT(DISTINCT CONCAT(CAST(order_id AS VARCHAR), '~', CAST(line_no AS VARCHAR)))`, with a separator that cannot appear in the values (`STRING` instead of `VARCHAR` on BigQuery) |

The Snowflake and MySQL multi-column form ignores rows where any listed column is null, and so does concatenation in dialects where concatenating a null yields null. Count null keys separately when the key can be null.

## Inspecting the duplicated rows

Find the keys with the most copies after the guilty step, then pull every column of the joined table for them:

```sql
WITH worst AS (
  SELECT order_id, COUNT(*) AS copies
  FROM step_2
  GROUP BY order_id
  ORDER BY copies DESC
  LIMIT 5
)
SELECT p.*
FROM payments p
JOIN worst w ON w.order_id = p.order_id
ORDER BY p.order_id;
```

Read across the copies for one key at a time. The column whose value changes between them is the grain the query did not account for. When nothing changes except a load timestamp or a batch id, the source has duplicate rows.

## The as-of join for a type-2 table

A type-2 dimension holds one row per key per validity period. Joining it on the key alone returns every period. Join on the key and the fact's timestamp falling inside the period:

```sql
SELECT o.order_id, o.amount, c.segment
FROM orders o
LEFT JOIN dim_customer_history c
  ON  c.customer_id = o.customer_id
  AND o.ordered_at >= c.valid_from
  AND o.ordered_at <  COALESCE(c.valid_to, TIMESTAMP '9999-12-31 00:00:00');
```

Use a half-open interval (`>=` start, `<` end). A closed interval on both ends matches two rows whenever an event lands exactly on a boundary, which is a fan-out that shows up only on a few keys and is easy to miss.

If the report wants the attribute as it is today rather than as it was then, filter to the current row instead (`valid_to IS NULL`, or the table's current flag) — and check that the current flag is unique per key, because a load that failed half-way often leaves two.

## Overlapping validity ranges

A history table can have the right shape and still overlap. This returns every pair of periods for one key that overlap, including two versions that start at the same moment. It needs a column that tells versions apart (here the surrogate key `customer_sk`), so each pair is compared once:

```sql
SELECT a.customer_id,
       a.customer_sk, a.valid_from, a.valid_to,
       b.customer_sk AS other_sk, b.valid_from AS other_from, b.valid_to AS other_to
FROM dim_customer_history a
JOIN dim_customer_history b
  ON  b.customer_id = a.customer_id
  AND b.customer_sk > a.customer_sk
  AND a.valid_from < COALESCE(b.valid_to, TIMESTAMP '9999-12-31 00:00:00')
  AND b.valid_from < COALESCE(a.valid_to, TIMESTAMP '9999-12-31 00:00:00');
```

Two half-open intervals overlap when each starts before the other ends; comparing start times alone misses versions with the same start.

Rows here are a defect in the dimension's build, not in the query. Fix the build, then add this query as a test that must return nothing.

## Pre-aggregating before the join

The many-to-many case: orders with several payments and several shipments.

Wrong — every payment is repeated once per shipment, so `paid` is inflated by the shipment count:

```sql
SELECT o.order_id, SUM(p.amount) AS paid, COUNT(s.shipment_id) AS shipments
FROM orders o
LEFT JOIN payments  p ON p.order_id = o.order_id
LEFT JOIN shipments s ON s.order_id = o.order_id
GROUP BY o.order_id;
```

Right — bring each child to one row per order first, then join one-to-one:

```sql
WITH paid AS (
  SELECT order_id, SUM(amount) AS paid
  FROM payments
  GROUP BY order_id
),
shipped AS (
  SELECT order_id, COUNT(*) AS shipments
  FROM shipments
  GROUP BY order_id
)
SELECT o.order_id, COALESCE(paid.paid, 0) AS paid, COALESCE(shipped.shipments, 0) AS shipments
FROM orders o
LEFT JOIN paid    ON paid.order_id    = o.order_id
LEFT JOIN shipped ON shipped.order_id = o.order_id;
```

After the rewrite each joined input is unique on `order_id`, so the join cannot multiply rows, and the duplicate check from step 2 proves it.

## Tests that keep it fixed

In dbt (version 1.8 and later name the key `data_tests`; earlier versions use `tests`):

```yaml
models:
  - name: dim_customer
    columns:
      - name: customer_id
        data_tests:
          - unique
          - not_null
  - name: dim_customer_history
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns: [customer_id, valid_from]
  - name: fct_orders_enriched
    columns:
      - name: order_id
        data_tests:
          - unique
          - not_null
    data_tests:
      - dbt_utils.equal_rowcount:
          compare_model: ref('stg_orders')
```

The last two tests together catch the next fan-out on the same model whatever its cause. `unique` on `order_id` fails the moment any join multiplies a row; `equal_rowcount` alone does not, because a join that drops one order and duplicates another leaves the count unchanged. The row count adds the mirror case, an order lost to an inner join. Save the overlapping-ranges query above as a singular test, which fails when it returns rows.

Without dbt, schedule the duplicate check from step 2 and the bisection's final row count against the base count, and fail the publish when either disagrees.

## The mirror case: a total that dropped

The same bisection finds a total that fell after a join. The signature is `base_keys` dropping between steps. The usual causes: an inner join to a table missing some keys; a `LEFT JOIN` whose right-hand table is then filtered in `WHERE`, which discards the unmatched rows and turns it into an inner join (move the filter into the `ON` clause); a join on a key with mismatched types or padding that silently matches nothing for part of the data.
