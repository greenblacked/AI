# Culprits and fixes

## Contents

- Refresh faster than the data changes
- SELECT * on wide tables
- Unpruned partitions
- Identical repeats missing the result cache
- Measuring before and after

Work through these in order for each top fingerprint and stop at the first that explains most of its cost. A fingerprint can carry more than one, and a schedule fix often makes the others small enough to leave.

## 1. Refresh faster than the data changes

**Detect.** For the fingerprint, compute runs per day and the median gap between runs. Then find how often the tables it reads actually change:

- The orchestrator's run log for the models or loads that write those tables is the most direct answer.
- BigQuery: count write jobs per day with that `destination_table`, and load jobs (`job_type = 'LOAD'`). Streaming inserts do not appear as jobs, so a streamed table changes continuously and this check does not apply to it.
- Snowflake Enterprise edition: `SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY` records written objects in `objects_modified`; count distinct writing queries per day.
- ClickHouse: `system.parts` shows when active parts were created per table.

A fingerprint that runs 96 times a day over tables written once a day returns the same answer 95 times. Then check whether anyone looks: the BI tool's usage or audit log (Looker's System Activity, Tableau's administrative views, the Power BI activity log) gives views per dashboard. A scheduled dashboard with no views in the window is a deletion candidate, not a tuning candidate.

**Fix.** Make the refresh follow the data:

- Trigger the refresh at the end of the load instead of on a clock: the orchestrator's last task calls the BI tool's refresh API.
- In Looker, a datagroup with a `sql_trigger` that selects the load log's latest timestamp rebuilds only when the load has run.
- For dbt, the `source_status:fresher+` selector rebuilds only models downstream of sources that changed since the previous run; it needs that run's source freshness artefacts.
- Where a clock is unavoidable, set the interval to the source's change frequency, and on Snowflake keep it longer than the warehouse's auto-suspend so the warehouse can sleep between runs.
- Route BI refreshes to their own small warehouse or reservation so their uptime is visible as one number.

## 2. SELECT * on wide tables

**Detect.** Search the sample texts for `select *` and `.*` against tables with many columns. In BigQuery, a dry run reports what a query would read without running it, so compare the star against the named columns the dashboard actually uses:

```bash
bq query --dry_run --use_legacy_sql=false 'SELECT * FROM `project.dataset.events` WHERE event_date = "2026-10-01"'
bq query --dry_run --use_legacy_sql=false 'SELECT user_id, event_name FROM `project.dataset.events` WHERE event_date = "2026-10-01"'
```

On Snowflake, the query profile for one run shows bytes scanned per table scan.

**Fix.** Name the columns. When a BI tool generates the star from a whole-table data source, give it a narrow view or model with only the fields the dashboard uses, or hide the unused fields before an extract is built (Tableau has a "hide all unused fields" action for this). `LIMIT` is not a fix: on an unclustered BigQuery table it does not reduce the bytes read.

## 3. Unpruned partitions

**Detect.**

- Snowflake: `partitions_scanned` against `partitions_total` in `QUERY_HISTORY`. A dashboard over the last seven days that scans most of a multi-year table's micro-partitions is not pruning. `SYSTEM$CLUSTERING_INFORMATION('db.schema.table', '(event_date)')` shows how well the table is clustered on the column being filtered.
- BigQuery: dry-run the query and compare bytes with the same query filtered on the partition column by a constant. Filters whose value comes from a subquery or a join do not prune.
- Redshift: in `SVL_QUERY_SUMMARY`, scan steps with `is_rrscan` false over a large table read every block rather than using the sort key's zone maps.
- ClickHouse: `EXPLAIN indexes = 1` before the query shows how many parts and granules the partition key and primary key leave selected.

**Fix.** Filter on the partition or clustering column directly, by constant or parameter, with no cast or function on the column. Where the dashboard has no date filter at all, add one with a sensible default. On BigQuery, set `require_partition_filter = true` on large partitioned tables so an unfiltered query fails instead of reading everything:

```sql
ALTER TABLE `project.dataset.events` SET OPTIONS (require_partition_filter = true);
```

Announce that change first: every existing query without the filter starts failing on the day it lands.

## 4. Identical repeats missing the result cache

**Detect.** Group by a hash of the raw submitted text, with no normalising at all, and count runs between writes to the underlying tables. Result caches match the text as submitted, so two runs that differ only in case, whitespace or a comment are different queries to the cache. On Snowflake that means `MD5(query_text)`, not `query_hash`, which canonicalises the text and would group runs the cache treats as distinct. Many identical runs between two writes should be cache hits.

- BigQuery: `cache_hit` is false on runs that should have hit. Queries using non-deterministic functions such as `CURRENT_TIMESTAMP()`, queries with a destination table, and queries over a table receiving streaming writes are not served from cache; on editions other than Enterprise and Enterprise Plus the cache is per user, so a dashboard running as each viewer's own credentials misses where a shared service account would hit. On Enterprise and Enterprise Plus, cached results can be reused across users in the same project, so identity is not the cause there; look at the other exceptions first.
- Snowflake: a run served from the result cache scans no bytes. Repeats that scan bytes each time usually differ in text (a per-run comment or timestamp), call a non-deterministic function, or run with `USE_CACHED_RESULT` set to false.
- Redshift: `result_cache_hit` in `SYS_QUERY_HISTORY`; the session setting is `enable_result_cache_for_session`.
- ClickHouse: the query cache is opt-in per query or profile with the `use_query_cache` setting, and its entries expire by time rather than on insert, so it suits dashboards that tolerate a short staleness.

**Fix.** Remove what makes each run's text unique: per-run comments, embedded timestamps (pass a date parameter instead of calling the current time), random ordering. Re-enable the cache where a session setting turned it off. If the BI tool has its own cache, set its lifetime to the data's change interval from culprit 1.

## Measuring before and after

Pick the before window and the after window with the same length and the same weekdays, and keep both clear of month-end, backfills and holidays where you can. Run the step 2 query once over both windows with a period label, restricted to the fingerprints you changed plus a total row:

```sql
-- Snowflake shape; adapt the cost column and view per warehouse
SELECT
  CASE WHEN start_time < '2026-10-01' THEN 'before' ELSE 'after' END AS period,
  query_parameterized_hash AS fingerprint,
  COUNT(*)                 AS runs,
  SUM(credits_attributed_compute
      + COALESCE(credits_used_query_acceleration, 0)) AS credits
FROM snowflake.account_usage.query_attribution_history
WHERE start_time >= '2026-09-17' AND start_time < '2026-10-15'
GROUP BY 1, 2
ORDER BY fingerprint, period;
```

Report the warehouse's metered total for both windows beside the per-fingerprint numbers. A saving that appears per fingerprint but not in the metered total is not a saving yet; on Snowflake it usually means the warehouse is still awake for the same hours.
