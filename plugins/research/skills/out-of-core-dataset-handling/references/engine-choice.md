# Engine choice

Contents: decision table, spill and memory settings, common failures.

## Decision table

| Operation | First choice | Why |
| --- | --- | --- |
| Filter and select columns | DuckDB or Polars lazy | Row group statistics skip data; columns read selectively |
| Group-by and aggregate | DuckDB or Polars lazy | Streaming hash aggregation; spills when large |
| Join large to small | DuckDB, or Polars lazy | Build a hash table from the small side |
| Join large to large | DuckDB (spills); sort both on the key into Parquet first | Hash tables on both sides may not fit; sorted inputs help |
| Row-wise Python function | Iterate row groups with pyarrow, write results per group | Python holds one group at a time |
| Many files, same operation | Process files independently (a job array) | Parallel with no shared state |
| Data beyond one machine's disk | Dask or Spark | The measured limit that justifies the overhead |

## Memory and spill

DuckDB takes a memory cap and a spill directory: `SET memory_limit='8GB'` and `SET temp_directory='/path/with/space'`. Set the limit below the machine's free memory so the operating system does not kill the process, and make sure the spill directory has several times the data size free. `SET threads=N` caps cores on a shared machine or a cluster node, where it should match the cores requested.

Polars lazy queries stream when collected with the streaming engine; not every operation supports streaming, and an unsupported one falls back to in-memory execution, so check the plan (`explain`) when memory still climbs.

## Common failures

- A CSV column read as integer from a sample and containing text later fails midway; give explicit types.
- Thousands of tiny Parquet files make the footer reads dominate; compact to files of a few hundred megabytes.
- One huge row group defeats skipping; use a row group size of a few hundred thousand to a million rows.
- A sort by a high-cardinality string column uses much memory; sort by an integer or date key where possible.
- Threads multiply memory use; lower the thread count before lowering the data.
- Pandas `merge` on large frames copies both sides; do the join in the engine and bring back the result.
