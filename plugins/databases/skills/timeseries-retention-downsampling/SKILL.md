---
name: timeseries-retention-downsampling
description: "Design retention, rollups and compression for a time-series store: compute ingest rate, bytes per point and active series cardinality first, write a resolution-versus-retention table driven by what old data is asked, build the rollup (TimescaleDB continuous aggregate, ClickHouse materialized view into AggregatingMergeTree, Prometheus recording rules), backfill it, verify against raw over an overlap window, and only then drop raw by dropping whole chunks or partitions, never DELETE. Sizes Timescale chunks, compresses after the late-write window, audits high-cardinality labels. Use for \"our metrics table is 4TB\", \"how long should we keep raw data\", \"set up continuous aggregates\", \"chunk interval\" or \"downsample old data without losing history\". Not for general relational partitions (table-partitioning), what to emit (instrumentation) or hardware sizing (capacity-planning)."
allowed-tools: Read, Glob, Grep
---

# Time-series Retention and Downsampling

This skill is done when a written table says what resolution is kept for how long and why, the rollups exist and have been checked against raw data, raw data expires by dropping whole chunks or partitions, and the storage forecast under the new policy is on file.

The usual failure is dropping or deleting before the rollup is proven. Someone sets a retention policy on the raw table, the rollup was never backfilled or silently misses a column, and the only copy of last year's data is a summary that cannot answer the question being asked. The second failure is `DELETE`, which rewrites or bloats storage instead of freeing it.

Run SQL through the normal permission prompt, rehearse on a copy, and never run a drop against production without a person confirming the boundary date.

## Scope

Use for: retention policy, rollup design, compression and chunk sizing for TimescaleDB, ClickHouse and Prometheus-compatible stores.

Do not use for: partitioning a general relational table, which is `table-partitioning`; deciding which metrics and labels the code emits, which is `instrumentation`; sizing hardware and growth planning, which is `capacity-planning`; running the backfill itself safely at scale, which is `safe-backfill`.

## Workflow

### 1. Measure before choosing anything

Compute three numbers: ingest rate (points per second), bytes per point on disk (table size over row count, after compression if enabled), and active series cardinality (distinct label or key combinations seen in a recent window). Storage is roughly points per second times seconds retained times bytes per point; cardinality multiplies how many series each scrape or tick writes. Read `references/sizing-and-queries.md` for queries on each store.

### 2. Write the resolution against retention table

Drive it from the questions asked of old data, not from the storage you would like. Ask who looks at data older than a week and what they ask: an incident review needs per-minute detail for weeks; a capacity trend needs hourly for years. A typical result:

| Age | Resolution | Why |
| --- | --- | --- |
| 0 to 14 days | raw | incident debugging |
| 14 to 90 days | 1 minute | dashboards, comparisons |
| 90 days to 2 years | 1 hour | trends, capacity |

Choose aggregates that survive rollup: sum, count, min, max, and for averages keep sum and count. Percentiles cannot be averaged across buckets; keep histograms or a sketch if percentiles matter at old ages.

### 3. Build the rollup before touching raw

- TimescaleDB: a continuous aggregate (`CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)` over `time_bucket`), with a refresh policy via `add_continuous_aggregate_policy`.
- ClickHouse: a materialized view writing into an `AggregatingMergeTree` using `-State` functions, read back with `-Merge`. A materialized view sees only rows inserted after it exists, so existing data needs an explicit backfill.
- Prometheus-compatible stores: recording rules that compute the coarse series, with the long-term store retaining those.

### 4. Backfill and verify against raw

Populate the rollup for the whole existing history, then compare to raw over a bucket-aligned overlap window where both exist, reporting a bucket missing on either side as a failure: counts, min, max and integer sums per bucket must match exactly, and float sums and averages within a stated tolerance, since summation order changes the last bits. Prometheus recording rules evaluate only going forward; backfill history with `promtool tsdb create-blocks-from rules`, or accept that data older than the rule stays raw-only. For ClickHouse, backfill strictly below the timestamp at which the view was created. Check the most recent bucket separately, since it may be incomplete. Keep the comparison query and its output with the change. Do not proceed on a rollup that differs without an explanation.

### 5. Expire by dropping whole units

Delete by dropping chunks or partitions, which is a metadata operation that frees space at once, never `DELETE`, which leaves dead rows to vacuum or rewrite.

- TimescaleDB: `add_retention_policy('table', INTERVAL '14 days')`, or `drop_chunks`. Keep the continuous aggregate's refresh window newer than the raw retention (start offset inside it), or a refresh over dropped raw data can remove history from the aggregate.
- ClickHouse: partition the raw table by the retention unit and set `TTL time_column + INTERVAL 14 DAY DELETE` together with `SETTINGS ttl_only_drop_parts = 1`, so expired parts are dropped whole rather than rewritten, or drop partitions explicitly with `ALTER TABLE ... DROP PARTITION`.
- Rollup tables carry their own, longer retention.

Raw expiry is the last step, after the verification in step 4, and the first run should be on a copy.

### 6. Size chunks and compress

For TimescaleDB, choose `chunk_time_interval` so that the recent chunks, with their indexes, fit in about a quarter of memory, which is Timescale's own guidance; too small gives thousands of chunks and planning overhead, too large evicts the hot set. Change it with `set_chunk_time_interval`, which applies to new chunks only. Compress with `segmentby` on the main query key (the column almost every query filters on, such as `device_id`) and `orderby` time, and compress only chunks past the late-write window, because updating compressed data is slower or restricted. Setting names differ between versions (older `compress`, newer columnstore naming); read your version's documentation.

### 7. Audit cardinality

High-cardinality labels (user ids, request ids, full URLs) are the usual cost driver: each distinct combination is a series with its own storage and index entries. List the labels by distinct count, remove or bucket the offenders at the source, and re-run the sizing. Cardinality fixes beat any retention setting.

### 8. Forecast and record

Re-estimate storage under the new policy from step 1's numbers and compare with the disk budget. Record the policy table, the verification output, the drop boundary and the person who confirmed it.

## Output format

```markdown
## Measurements
[Ingest rate, bytes per point, active series, current size.]

## Policy
[Resolution against retention table with the question each row serves.]

## Rollups
[Definitions, refresh policy, backfill range, verification result against raw.]

## Expiry and compression
[Retention mechanism, chunk interval, segmentby and orderby, late-write window.]

## Forecast
[Storage under the policy and the date it is reviewed.]
```

## Anti-patterns

**Dropping raw before verifying the rollup.** The summary may not answer tomorrow's question.

**DELETE for expiry.** It leaves dead space; drop chunks or partitions.

**Averaging averages or percentiles.** Keep sum and count; keep histograms for percentiles.

**Compressing recent chunks.** Late writes then hit compressed data; wait out the window.

**Retention before cardinality.** One unbounded label outgrows any retention window.

## Reference files

- `references/sizing-and-queries.md` - read at steps 1, 3, 5 and 6: sizing queries per store, rollup and retention statements, and the verification query.
