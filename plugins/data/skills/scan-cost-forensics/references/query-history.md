# Query history by warehouse

## Contents

- What every version of the query returns
- Snowflake
- BigQuery
- Redshift
- ClickHouse
- Normalising text when there is no fingerprint
- Reading the result

## What every version of the query returns

One row per fingerprint over the fixed window, with: run count, the cost column summed, elapsed time summed, the distinct users or service accounts, one tag or label sample, and one sample of the text. Sort by the cost column, descending. Replace the 14-day window with the one you fixed in step 1.

Run these as a role that can read the account-wide history, and say in the report which role was used: a project-scoped or user-scoped view silently returns a subset, and the ranking from a subset looks just as convincing.

## Snowflake

`SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` lags real time by up to about 45 minutes and keeps a year of history. `query_parameterized_hash` groups statements that differ only in literals.

```sql
SELECT
  query_parameterized_hash                        AS fingerprint,
  COUNT(*)                                        AS runs,
  SUM(bytes_scanned) / POWER(1024, 4)             AS tib_scanned,
  SUM(total_elapsed_time) / 1000 / 3600           AS elapsed_hours,
  SUM(partitions_scanned) / NULLIF(SUM(partitions_total), 0) AS share_partitions_scanned,
  ARRAY_AGG(DISTINCT user_name)                   AS users,
  ARRAY_AGG(DISTINCT warehouse_name)              AS warehouses,
  ANY_VALUE(query_tag)                            AS sample_tag,
  ANY_VALUE(LEFT(query_text, 300))                AS sample_text
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(day, -14, CURRENT_DATE())
  AND start_time <  CURRENT_DATE()
  AND warehouse_name IS NOT NULL
GROUP BY 1
ORDER BY elapsed_hours DESC
LIMIT 50;
```

Bytes scanned is a proxy on Snowflake, because the bill is warehouse running time. For the credit view, rank on `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY`, which attributes warehouse compute credits to individual queries:

```sql
SELECT
  query_parameterized_hash        AS fingerprint,
  warehouse_name,
  COUNT(*)                        AS runs,
  SUM(credits_attributed_compute) AS credits
FROM snowflake.account_usage.query_attribution_history
WHERE start_time >= DATEADD(day, -14, CURRENT_DATE())
  AND start_time <  CURRENT_DATE()
GROUP BY 1, 2
ORDER BY credits DESC
LIMIT 50;
```

Attribution leaves out idle time and very short queries. Compare its total per warehouse with `credits_used_compute` from `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` over the same window. A large gap is a warehouse kept awake between queries: look for a schedule firing more often than the warehouse's `AUTO_SUSPEND` (`SHOW WAREHOUSES` shows it) before looking at any SQL.

## BigQuery

`INFORMATION_SCHEMA.JOBS_BY_PROJECT` is regional and keeps 180 days. Qualify it with the region the datasets live in. `JOBS_BY_ORGANIZATION` covers every project when you have the permission for it.

```sql
WITH jobs AS (
  SELECT
    -- The native hash (query_info.query_hashes.normalized_literals) is empty for
    -- cache hits, and mixing it with a fallback would split one query's misses
    -- and hits across two rows. Hash the normalised text for every job, in the
    -- order "Normalising text when there is no fingerprint" sets out:
    -- comments, literals, whitespace, IN lists.
    TO_HEX(MD5(TRIM(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(LOWER(query), r'(?s)/\*.*?\*/', ' '),
                r'--[^\n]*', ' '),
              r"'[^']*'", '?'),
            r'\b[0-9]+(\.[0-9]+)?\b', '?'),
          r'\s+', ' '),
        r'in \(\?(\s*,\s*\?)*\)', 'in (?)')
    ))) AS fingerprint,
    total_bytes_billed,
    total_slot_ms,
    cache_hit,
    user_email,
    (SELECT value FROM UNNEST(labels) WHERE key = 'looker_studio_report_id') AS report_id,
    SUBSTR(query, 1, 300) AS text_head
  FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
  WHERE creation_time >= TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY), INTERVAL 14 DAY)
    AND creation_time <  TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY)
    AND job_type = 'QUERY'
    AND statement_type != 'SCRIPT'
)
SELECT
  fingerprint,
  COUNT(*)                                             AS runs,
  SUM(total_bytes_billed) / POW(1024, 4)               AS tib_billed,
  SUM(total_slot_ms) / 1000 / 3600                     AS slot_hours,
  COUNTIF(cache_hit)                                   AS cache_hits,
  ARRAY_AGG(DISTINCT user_email IGNORE NULLS LIMIT 10) AS users,
  ANY_VALUE(report_id)                                 AS sample_report,
  ANY_VALUE(text_head)                                 AS sample_text
FROM jobs
GROUP BY fingerprint
ORDER BY tib_billed DESC
LIMIT 50;
```

Two things to get right:

- Exclude `statement_type = 'SCRIPT'`. A script's parent job reports the totals of its child jobs, so including both counts the same bytes twice.
- On capacity pricing, order by `slot_hours` instead. Bytes billed is still worth reporting because it says what the same workload would cost on demand.

`labels` is where BI tools and orchestrators leave their mark. List the label keys in use before deciding how to attribute:

```sql
SELECT l.key, COUNT(*) AS jobs
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT, UNNEST(labels) AS l
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
GROUP BY 1
ORDER BY 2 DESC;
```

## Redshift

Redshift has no fingerprint column in the views below, so normalise the text (next section) and hash it.

Provisioned clusters are billed per node hour, so the spend does not move with a single query; what moves is whether the cluster needs to be bigger or needs concurrency scaling. Rank by blocks read and by queue time, which is what forces a resize. Spectrum is billed by bytes scanned, so rank Spectrum work on `spectrum_scan_size_mb`.

```sql
SELECT
  MD5(REGEXP_REPLACE(REGEXP_REPLACE(LOWER(TRIM(q.querytxt)), '''[^'']*''', '?'), '[0-9]+', '?')) AS fingerprint,
  COUNT(*)                                AS runs,
  SUM(m.query_blocks_read)                AS blocks_read,
  SUM(m.spectrum_scan_size_mb)            AS spectrum_mb,
  SUM(m.query_execution_time) / 3600.0    AS execution_hours,  -- the summary view reports seconds
  MIN(q.label)                            AS sample_label,
  MIN(LEFT(TRIM(q.querytxt), 300))        AS sample_text
FROM stl_query q
JOIN svl_query_metrics_summary m ON m.query = q.query
WHERE q.starttime >= DATEADD(day, -14, TRUNC(GETDATE()))
GROUP BY 1
ORDER BY blocks_read DESC
LIMIT 50;
```

`STL_QUERY.querytxt` is truncated to the first 4,000 characters, and STL views keep only a few days; for a 14-day window, copy them into a table of your own every day and run the query against that.

Redshift Serverless is billed on RPU time. Use `SYS_QUERY_HISTORY`, rank by `elapsed_time` (microseconds), and read `result_cache_hit` for step 5's fourth culprit. `query_label` carries the label set with `SET query_group`.

## ClickHouse

`system.query_log` holds one row per query event. Keep only finished queries, or each query counts twice (start and finish). On a cluster or ClickHouse Cloud, each replica has its own log: read it through `clusterAllReplicas` with the cluster's name.

```sql
SELECT
  normalized_query_hash                       AS fingerprint,
  count()                                     AS runs,
  sum(read_bytes)                             AS read_bytes,
  formatReadableSize(sum(read_bytes))         AS read_readable,
  sum(query_duration_ms) / 1000 / 3600        AS hours,
  groupUniqArray(user)                        AS users,
  any(log_comment)                            AS sample_comment,
  any(substring(normalizeQuery(query), 1, 300)) AS sample_text
FROM clusterAllReplicas('default', system.query_log)
WHERE type = 'QueryFinish'
  AND event_date >= today() - 14
  AND event_date <  today()
GROUP BY fingerprint
ORDER BY read_bytes DESC
LIMIT 50;
```

Failed queries also read data. Rerun with `type IN ('ExceptionWhileProcessing')` to see whether a retry loop is a top spender in its own right.

## Normalising text when there is no fingerprint

Apply, in this order, to the lower-cased text: strip block and line comments; replace quoted string literals with `?`; replace numeric literals with `?`; collapse runs of whitespace to one space; collapse `IN (?, ?, ?)` lists to `IN (?)`. Hash the result. The comment strip comes first because a per-run comment (a timestamp, a request id) otherwise makes every run unique. Keep the raw sample beside the hash, because the comment you stripped is often the best attribution evidence step 4 has.

## Reading the result

- **One fingerprint, many users.** A shared dashboard or a template query. Attribute through the tag or the schedule, not the users.
- **One user, many fingerprints, regular interval.** A job or a BI extract refresh. Find the schedule.
- **High runs, low cost per run, high total.** Schedule culprit. Go to step 5's first test.
- **Low runs, very high cost per run.** A real candidate for SQL work: star selects, missing partition filters.
- **High cache-hit count already.** The repeats are cheap; the remaining cost is elsewhere.
