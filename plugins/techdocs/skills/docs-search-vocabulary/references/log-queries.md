# Search log queries

Read this when computing the baseline, extracting reformulation chains or building the
cluster table. The SQL runs unchanged in PostgreSQL and DuckDB; DuckDB is the quick route
when all you have is a CSV export.

## Contents

- [The event schema](#the-event-schema)
- [Loading an export](#loading-an-export)
- [Zero-result rate](#zero-result-rate)
- [Reformulation chains](#reformulation-chains)
- [Twice-reformulated rate](#twice-reformulated-rate)
- [Reader word to wanted page](#reader-word-to-wanted-page)
- [Per-cluster before and after](#per-cluster-before-and-after)

## The event schema

One row per search, with the first result clicked from that results page, if any:

| Column | Type | Notes |
| --- | --- | --- |
| `session_id` | text | Stable for one reader's visit; without it chains cannot be built |
| `event_id` | integer | Unique per row and increasing within a session, never text because text ids order lexically ('10' before '9'); breaks ties between searches logged in the same second, which would otherwise order (and chain) arbitrarily |
| `ts` | timestamp | When the search ran |
| `query` | text | As typed |
| `result_count` | integer | Zero is the signal; a missing value is not zero |
| `clicked_url` | text, nullable | The result opened from this search |
| `is_internal` | boolean | Staff, monitoring and known bots; excluded everywhere below. A null is treated as not internal (`IS NOT TRUE`): `NOT is_internal` would silently drop every row where the flag was never set |

If the source logs clicks as separate events, join each click to the latest search in the
same session before it, then load the result in this shape.

## Loading an export

```bash
duckdb search.duckdb <<'SQL'
CREATE TABLE search_events AS SELECT * FROM read_csv_auto('search_events.csv');
SQL
duckdb search.duckdb < zero_result_rate.sql
```

## Zero-result rate

```sql
SELECT
  count(*) AS searches,
  count(result_count) AS searches_with_count,
  sum(CASE WHEN result_count = 0 THEN 1 ELSE 0 END) * 1.0
    / nullif(count(result_count), 0) AS zero_result_rate
FROM search_events
WHERE is_internal IS NOT TRUE
  AND ts >= TIMESTAMP '2026-09-01' AND ts < TIMESTAMP '2026-10-01';
```

The denominator is `count(result_count)`, not `count(*)`, because a search whose result
count was never logged is unknown, not a success. Dividing by every row would read an
instrumentation gap as searches that found something: ten searches with two zero-result
and four unlogged give 0.20 over all rows against the true 0.33. If `searches` and
`searches_with_count` differ by more than a few percent, fix the logging before trusting
either rate.

The top zero-result queries for the cluster work:

```sql
SELECT lower(trim(query)) AS q, count(*) AS n
FROM search_events
WHERE is_internal IS NOT TRUE AND result_count = 0
  AND ts >= TIMESTAMP '2026-09-01' AND ts < TIMESTAMP '2026-10-01'
GROUP BY 1
ORDER BY n DESC
LIMIT 200;
```

## Reformulation chains

A chain is consecutive searches in one session with no click between them and no long gap.
A click ends a chain, and a gap longer than the chain limit starts a new one. Two minutes
is a starting value, not a standard; check it against a sample of sessions read by hand.

```sql
CREATE OR REPLACE VIEW chains AS
WITH s AS (
  SELECT session_id, event_id, ts, lower(trim(query)) AS q, result_count, clicked_url,
         lag(ts) OVER (PARTITION BY session_id ORDER BY ts, event_id) AS prev_ts,
         lag(clicked_url) OVER (PARTITION BY session_id ORDER BY ts, event_id) AS prev_click
  FROM search_events
  WHERE is_internal IS NOT TRUE
    AND ts >= TIMESTAMP '2026-09-01' AND ts < TIMESTAMP '2026-10-01'
),
marked AS (
  SELECT *,
         CASE WHEN prev_ts IS NULL
                OR ts - prev_ts > INTERVAL '2 minutes'
                OR prev_click IS NOT NULL
              THEN 1 ELSE 0 END AS starts_chain
  FROM s
),
numbered AS (
  SELECT *,
         sum(starts_chain) OVER (PARTITION BY session_id ORDER BY ts, event_id
                                 ROWS UNBOUNDED PRECEDING) AS chain_id
  FROM marked
)
SELECT session_id, chain_id,
       count(DISTINCT q) AS distinct_queries,
       (array_agg(q ORDER BY ts, event_id))[1] AS first_query,
       string_agg(q, ' -> ' ORDER BY ts, event_id) AS path,
       max(clicked_url) AS clicked_url
FROM numbered
GROUP BY session_id, chain_id;
```

Because a click ends a chain, only a chain's last search can carry a click, so
`clicked_url` is the page the reader finally reached, or null when they gave up.

## Twice-reformulated rate

A chain with three or more distinct queries is an original plus at least two
reformulations, none of which got a click before the last.

```sql
SELECT
  count(DISTINCT CASE WHEN distinct_queries >= 3 THEN session_id END) * 1.0
    / count(DISTINCT session_id) AS twice_reformulated_rate
FROM chains;
```

## Reader word to wanted page

The most useful table in the analysis: what readers typed first, and where they ended up.

```sql
SELECT first_query, clicked_url, count(*) AS n, min(path) AS example_path
FROM chains
WHERE distinct_queries >= 2 AND clicked_url IS NOT NULL
GROUP BY first_query, clicked_url
ORDER BY n DESC
LIMIT 200;
```

Rows here with high counts are near-certain synonym or rename candidates. Chains with
`clicked_url` null and high counts are the candidates for a missing page.

## Per-cluster before and after

Keep the hand-made clustering as a two-column file, `cluster,q`, with `q` normalised the
same way as above, and load it as `cluster_queries`. Compare windows of equal length either
side of the change.

```sql
SELECT c.cluster,
       CASE WHEN e.ts >= TIMESTAMP '2026-10-15' THEN 'after' ELSE 'before' END AS period,
       count(*) AS searches,
       avg(CASE WHEN e.result_count = 0 THEN 1.0
                WHEN e.result_count > 0 THEN 0.0 END) AS zero_result_rate,
       avg(CASE WHEN e.clicked_url IS NOT NULL THEN 1.0 ELSE 0 END) AS click_rate
FROM search_events e
JOIN cluster_queries c ON c.q = lower(trim(e.query))
WHERE e.is_internal IS NOT TRUE
  AND e.ts >= TIMESTAMP '2026-09-15' AND e.ts < TIMESTAMP '2026-11-14'
GROUP BY 1, 2
ORDER BY 1, 2;
```

The zero-result `CASE` has no `ELSE`, so a row with no logged count is null and `avg`
leaves it out, for the same reason as in the overall rate.

Each query must sit in one cluster only. A query listed twice in `cluster_queries` joins to
every row twice and inflates both rates' denominators; check before running:

```sql
SELECT q, count(*) FROM cluster_queries GROUP BY q HAVING count(*) > 1;
```

A cluster whose zero-result rate fell but whose click rate did not rise now returns
results nobody wants: check where its clicks go before calling it fixed.
