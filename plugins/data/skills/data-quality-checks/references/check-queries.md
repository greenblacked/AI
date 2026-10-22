# Check queries

## Contents

- Baseline dimension queries
- The dbt forms
- Thresholds from 30 days of history
- Backtesting a threshold

The SQL is ANSI-flavoured. Date functions (`DATE_TRUNC`, `CURRENT_TIMESTAMP`, interval syntax, `DAYOFWEEK` versus `EXTRACT(DOW ...)`) differ between Snowflake, BigQuery, Redshift, Postgres and others; translate them and run each query once by hand before wiring it into a check.

## Baseline dimension queries

Each query returns one measured value; the check compares it to a threshold. Keeping measurement and threshold separate is what lets you backtest.

**Freshness** — minutes since the newest row arrived. Use the load timestamp for "did the job run" and the event timestamp for "is the source sending".

```sql
-- an empty table or all-null timestamps would give NULL, which no threshold
-- comparison fires on; report it as infinitely stale instead
SELECT COALESCE(
         EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(_loaded_at))) / 60,
         1e9) AS minutes_stale
FROM analytics.fct_orders;
```

**Volume** — rows in the latest complete partition.

```sql
SELECT COUNT(*) AS rows_loaded
FROM analytics.fct_orders
WHERE order_date = CURRENT_DATE - 1;
```

**Key uniqueness** — rows violating the declared grain. Expected value is zero.

```sql
SELECT COUNT(*) AS duplicate_keys
FROM (
  SELECT order_id
  FROM analytics.fct_orders
  GROUP BY order_id
  HAVING COUNT(*) > 1
) d;
```

**Null rate** — on a column a consumer uses.

```sql
SELECT AVG(CASE WHEN customer_id IS NULL THEN 1.0 ELSE 0.0 END) AS null_rate
FROM analytics.fct_orders
WHERE order_date = CURRENT_DATE - 1;
```

**Enum drift** — two directions: new values, and expected values that vanished.

```sql
-- values not in the accepted set
SELECT status, COUNT(*) AS n
FROM analytics.fct_orders
WHERE order_date = CURRENT_DATE - 1
  AND status NOT IN ('placed', 'shipped', 'delivered', 'returned', 'cancelled')
GROUP BY status;

-- accepted values seen in the last 30 days but absent yesterday
SELECT a.status
FROM (SELECT DISTINCT status FROM analytics.fct_orders
      WHERE order_date BETWEEN CURRENT_DATE - 31 AND CURRENT_DATE - 2) a
LEFT JOIN (SELECT DISTINCT status FROM analytics.fct_orders
           WHERE order_date = CURRENT_DATE - 1) y
  ON a.status = y.status
WHERE y.status IS NULL;
```

**Referential integrity** — fact rows whose key is missing from the dimension.

```sql
SELECT COUNT(*) AS orphans
FROM analytics.fct_orders f
LEFT JOIN analytics.dim_customers c ON f.customer_id = c.customer_id
WHERE f.customer_id IS NOT NULL
  AND c.customer_id IS NULL;
```

## The dbt forms

dbt ships four generic tests: `unique`, `not_null`, `accepted_values` and `relationships`. Each takes a `config` block with `severity` (`error` or `warn`), optional `warn_if` and `error_if` conditions on the failure count, and `store_failures`. Recent dbt versions name the property `data_tests:` (older ones use `tests:`) and have been moving test arguments and source freshness settings under `config:`; check the property names against the documentation for the dbt version you run.

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        data_tests:
          - unique:
              config:
                severity: error        # block: duplicates double revenue
                store_failures: true
          - not_null
      - name: status
        data_tests:
          - accepted_values:
              values: ['placed', 'shipped', 'delivered', 'returned', 'cancelled']
              config:
                severity: warn         # warn: new status needs a mapping decision
      - name: customer_id
        data_tests:
          - relationships:
              to: ref('dim_customers')
              field: customer_id
              config:
                severity: error
                warn_if: ">0"
                error_if: ">50"        # from 30-day history of late dimension rows
```

Source freshness is declared on the source and run with `dbt source freshness`:

```yaml
sources:
  - name: billing
    loaded_at_field: _loaded_at
    freshness:
      warn_after: {count: 6, period: hour}
      error_after: {count: 12, period: hour}
    tables:
      - name: invoices
```

Volume, null-rate and business-rule checks are written as singular tests (a SQL file under `tests/` that returns failing rows) or with a package that provides parameterised tests; whichever you use, keep the threshold in the YAML or a variable so the monthly review can change it without editing SQL.

Great Expectations and Soda express the same dimensions with their own syntax. The procedure does not change: measure, set the threshold from history, choose the action.

## Thresholds from 30 days of history

Volume by weekday, with a median and median absolute deviation per weekday:

```sql
WITH days AS (
  -- a calendar spine, so a day with no rows at all appears with n = 0
  SELECT date_day AS d
  FROM analytics.dim_date
  WHERE date_day BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE - 1
),
daily AS (
  SELECT days.d, COUNT(o.order_date) AS n
  FROM days
  LEFT JOIN analytics.fct_orders o ON o.order_date = days.d
  GROUP BY days.d
)
SELECT EXTRACT(DOW FROM d) AS weekday,
       MIN(n) AS min_n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY n) AS median_n,
       MAX(n) AS max_n
FROM daily
GROUP BY EXTRACT(DOW FROM d)
ORDER BY weekday;
```

Both queries build the days from a calendar table (`dim_date` here; `generate_series` on PostgreSQL), not from the fact table: a day the source delivered nothing has no fact rows to group, so grouping the facts alone silently drops the most important volume failure from the history. Thirty days gives four or five values per weekday, which is enough for a minimum and maximum but thin for anything finer. The query below uses fail below 0.7 x the weekday's minimum or above 1.3 x its maximum as an illustrative starting point; the margins are yours to set by backtest, not a standard. Use a longer window for tables with monthly cycles, and exclude known incident days from the baseline so the threshold is not trained on the failure.

Freshness: take the distribution of observed lag at each scheduled check time over the 30 days. Set warn just above the highest normal lag and error at the consumer's stated deadline. If the highest normal lag already exceeds the consumer's deadline, the problem is the schedule, not the check.

Null rate: take the maximum observed daily null rate and add a margin; a column that was always 0% null and is suddenly 3% has changed, even though 3% sounds small.

## Backtesting a threshold

Replay the check over days it was not trained on, and count firings. Bounds taken from the same days can never fire on them: every day's count lies between that weekday's minimum and maximum by definition, so an in-sample replay always reports zero, outages included.

```sql
WITH days AS (
  SELECT date_day AS d
  FROM analytics.dim_date
  WHERE date_day BETWEEN CURRENT_DATE - 60 AND CURRENT_DATE - 1
),
daily AS (
  SELECT days.d,
         EXTRACT(DOW FROM days.d) AS weekday,
         COUNT(o.order_date) AS n
  FROM days
  LEFT JOIN analytics.fct_orders o ON o.order_date = days.d
  GROUP BY days.d
),
bounds AS (
  -- trained on days 31 to 60 only
  SELECT weekday, 0.7 * MIN(n) AS lo, 1.3 * MAX(n) AS hi
  FROM daily
  WHERE d < CURRENT_DATE - 30
  GROUP BY weekday
)
SELECT d.d, d.n, b.lo, b.hi,
       CASE WHEN d.n < b.lo OR d.n > b.hi THEN 1 ELSE 0 END AS would_fire
FROM daily d
JOIN bounds b ON b.weekday = d.weekday
WHERE d.d >= CURRENT_DATE - 30            -- tested on days 1 to 30
ORDER BY d.d;
```

Exclude known incident days from the training window, as for the baseline, then replay each incident day from the register against bounds trained without it: the check is only worth keeping if it fires on those. Record the firing count on normal days and the incidents it caught in the check register.
