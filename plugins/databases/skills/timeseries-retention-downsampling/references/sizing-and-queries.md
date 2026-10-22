# Sizing and queries

Reference for steps 1, 3, 5 and 6.

## Contents

- [Sizing](#sizing)
- [TimescaleDB rollup and policies](#timescaledb-rollup-and-policies)
- [ClickHouse rollup and TTL](#clickhouse-rollup-and-ttl)
- [Prometheus recording rules](#prometheus-recording-rules)
- [Verification query](#verification-query)

## Sizing

```sql
-- PostgreSQL / TimescaleDB: rows and size of a hypertable
SELECT count(*) AS points FROM metrics WHERE time > now() - INTERVAL '1 day';
SELECT pg_size_pretty(hypertable_size('metrics'));
SELECT count(*) AS series FROM (SELECT DISTINCT device_id, metric FROM metrics
                                WHERE time > now() - INTERVAL '1 day') s;
```

Bytes per point is hypertable size divided by total row count. For ClickHouse:

```sql
SELECT sum(rows) AS points, formatReadableSize(sum(bytes_on_disk)) AS size,
       round(sum(bytes_on_disk) / sum(rows), 2) AS bytes_per_point
FROM system.parts WHERE active AND database = 'db' AND table = 'metrics';
```

## TimescaleDB rollup and policies

```sql
CREATE MATERIALIZED VIEW metrics_1m WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', time) AS bucket, device_id,
       sum(value) AS sum_value, count(*) AS n, min(value) AS min_value, max(value) AS max_value
FROM metrics GROUP BY bucket, device_id WITH NO DATA;

CALL refresh_continuous_aggregate('metrics_1m', NULL, now() - INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('metrics_1m',
  start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '30 minutes');

SELECT add_retention_policy('metrics', INTERVAL '14 days');
```

The policy start offset (3 days) is newer than raw retention (14 days), so the refresh
never recomputes over dropped raw data. Compression, with names from the 2.x series (a
newer release renames these under a columnstore setting):

```sql
ALTER TABLE metrics SET (timescaledb.compress,
  timescaledb.compress_segmentby = 'device_id', timescaledb.compress_orderby = 'time DESC');
SELECT add_compression_policy('metrics', INTERVAL '7 days');
```

## ClickHouse rollup and TTL

```sql
CREATE TABLE metrics_1m (bucket DateTime, device_id UInt32,
  sum_value AggregateFunction(sum, Float64), n AggregateFunction(count),
  min_value AggregateFunction(min, Float64), max_value AggregateFunction(max, Float64))
ENGINE = AggregatingMergeTree ORDER BY (device_id, bucket);

CREATE MATERIALIZED VIEW metrics_1m_mv TO metrics_1m AS
SELECT toStartOfMinute(time) AS bucket, device_id,
       sumState(value) AS sum_value, countState() AS n,
       minState(value) AS min_value, maxState(value) AS max_value
FROM metrics
WHERE time >= toDateTime('2026-01-01 00:00:00')  -- the cut-over, a fixed literal
GROUP BY bucket, device_id;
```

Read with `sumMerge(sum_value)`, `countMerge(n)`, `minMerge(min_value)`,
`maxMerge(max_value)`. Choose the cut-over before creating the view and put it in the
view's `WHERE time >= <cut-over>` as a fixed literal, as above. Backfill history with an
`INSERT INTO metrics_1m SELECT ...` over `time < <cut-over>` in time-bounded batches, using
the same `-State` expressions. The two ranges are then disjoint whenever a row arrives:
a late row with an old `time` inserted after the view exists is excluded by the view and
picked up by the backfill if it arrives before that batch runs. Without the view filter,
a late row below the cut-over would be counted by the view and again by the backfill. Pause
late writers for the backfill if rows below the cut-over can still arrive after it.

Raw expiry: partition the raw table by the retention unit and let whole parts expire.

```sql
-- in the raw table definition
PARTITION BY toYYYYMMDD(time)
TTL time + INTERVAL 14 DAY DELETE
SETTINGS ttl_only_drop_parts = 1
```

With `ttl_only_drop_parts = 1` a part is dropped only when every row in it has expired, so
the partition key must line up with the retention unit; without the setting the TTL
rewrites parts row by row during merges, which is the `DELETE` this skill avoids.
`ALTER TABLE metrics DROP PARTITION <id>` is the explicit alternative.

## Prometheus recording rules

```yaml
groups:
  - name: rollups
    interval: 1m
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))
```

Keep the recorded series in the long-term store with the longer retention, and drop the
raw label dimensions that the rule aggregates away.

## Verification query

Align the window to bucket boundaries, here whole hours (both ends are `date_trunc`
results), and end it an hour or more before now so the newest bucket is complete. The
full outer join reports a bucket present on only one side, so an empty or never-backfilled
rollup fails the check instead of passing it.

```sql
WITH win AS (
  SELECT date_trunc('hour', now() - INTERVAL '3 days') AS t_from,
         date_trunc('hour', now() - INTERVAL '2 hours') AS t_to
),
raw AS (
  SELECT time_bucket('1 minute', time) AS bucket, device_id,
         count(*) AS n, sum(value) AS sum_value,
         min(value) AS min_value, max(value) AS max_value
  FROM metrics, win WHERE time >= t_from AND time < t_to GROUP BY 1, 2
),
roll AS (
  SELECT bucket, device_id, n, sum_value, min_value, max_value
  FROM metrics_1m, win WHERE bucket >= t_from AND bucket < t_to
)
SELECT coalesce(r.bucket, a.bucket) AS bucket, coalesce(r.device_id, a.device_id) AS device_id,
       r.n AS rollup_n, a.n AS raw_n, r.sum_value, a.sum_value AS raw_sum
FROM roll r
FULL OUTER JOIN raw a ON r.bucket = a.bucket AND r.device_id = a.device_id
WHERE r.bucket IS NULL OR a.bucket IS NULL
   OR r.n IS DISTINCT FROM a.n
   OR r.min_value IS DISTINCT FROM a.min_value OR r.max_value IS DISTINCT FROM a.max_value
   OR (r.sum_value IS NULL) <> (a.sum_value IS NULL)
   OR abs(r.sum_value - a.sum_value) > 1e-9 * greatest(abs(a.sum_value), 1);
```

Zero rows means the overlap window agrees. Counts, min and max are compared exactly. A
float sum is compared within a relative tolerance (1e-9 here, chosen for double precision;
state the value you use), because the same values added in a different order differ in
the last bits. An integer sum can be compared exactly.

The query above is PostgreSQL and TimescaleDB. For ClickHouse, run the same comparison
with the rollup side read through `-Merge` functions, and expire raw data only after it
returns zero rows:

```sql
SELECT bucket, device_id, r.n, a.n
FROM (SELECT bucket, device_id, countMerge(n) AS n, sumMerge(sum_value) AS s,
             minMerge(min_value) AS mn, maxMerge(max_value) AS mx
      FROM metrics_1m WHERE bucket >= {t_from:DateTime} AND bucket < {t_to:DateTime}
      GROUP BY bucket, device_id) AS r
FULL OUTER JOIN
     (SELECT toStartOfMinute(time) AS bucket, device_id, count() AS n, sum(value) AS s,
             min(value) AS mn, max(value) AS mx
      FROM metrics WHERE time >= {t_from:DateTime} AND time < {t_to:DateTime}
      GROUP BY bucket, device_id) AS a
  USING (bucket, device_id)
WHERE r.n != a.n OR r.mn != a.mn OR r.mx != a.mx
   OR abs(r.s - a.s) > 1e-9 * greatest(abs(a.s), 1)
   OR r.n IS NULL OR a.n IS NULL
SETTINGS join_use_nulls = 1;
```

With `join_use_nulls = 1` a bucket missing on one side appears as NULL columns, and a
comparison against NULL is never true, so the final `IS NULL` terms are what report those
buckets.
