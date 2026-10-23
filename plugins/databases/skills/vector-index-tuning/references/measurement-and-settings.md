# Measurement and settings

Reference for steps 2 to 7.

## Contents

- [Recall harness](#recall-harness)
- [Settings per engine](#settings-per-engine)
- [Filtered-search checks](#filtered-search-checks)
- [Index definitions](#index-definitions)

## Recall harness

Store the exact answers once as JSON lines: `{"qid": 1, "vector": [...], "exact": [ids]}`.
Then for each setting under test:

```python
import json, statistics, time


def run(queries, search, k=10):
    recalls, latencies, skipped = [], [], 0
    for q in queries:
        start = time.perf_counter()
        got = search(q["vector"], k)  # returns a list of ids
        latencies.append(time.perf_counter() - start)
        exact = q["exact"][:k]
        if not exact:
            skipped += 1  # empty exact set (e.g. a filter matching nothing): report separately
            continue
        recalls.append(len(set(got) & set(exact)) / min(k, len(exact)))
    latencies.sort()
    p95 = latencies[int(0.95 * (len(latencies) - 1))]
    return statistics.mean(recalls) if recalls else None, p95, skipped
```

Run it once to warm the cache and discard that result. Report recall and p95 in one table
row per setting. Ties in distance can make exact results ambiguous; if many vectors are
equidistant, compare distances rather than ids.

## Settings per engine

| Engine | Query-time knob | Build-time knobs | Notes |
| --- | --- | --- | --- |
| pgvector HNSW | `hnsw.ef_search` (default 40, at least k) | `m` (16), `ef_construction` (64) | Set per query with `SET LOCAL` |
| pgvector IVFFlat | `ivfflat.probes` (default 1) | `lists` | Build after loading data |
| OpenSearch k-NN | `ef_search` index setting | `m`, `ef_construction` in the method parameters | Index created with `index.knn: true` |
| Elasticsearch knn | `num_candidates` (at least k) | `m`, `ef_construction` in `index_options` | Per request |

Raise the query-time knob first, since it needs no rebuild. Change build-time knobs only
when recall plateaus below the target.

## Filtered-search checks

1. Pick five realistic filters from the product, from very broad to very selective.
2. For each, compute exact filtered top-k by brute force with the filter applied.
3. Run the index with the same filter and count rows returned as well as recall.
4. Any query returning fewer than k rows with at least k matching rows is the trap.
5. Apply iterative scans, a partial index or partitioning, then repeat steps 3 and 4.

For pgvector 0.8.0 and later:

```sql
SET hnsw.iterative_scan = relaxed_order;
SET hnsw.max_scan_tuples = 20000;
```

`relaxed_order` may return results slightly out of order; `strict_order` keeps order and
costs more. The values here are starting points for the sample, not recommendations.

## Index definitions

```sql
-- HNSW for cosine distance, built after loading, without blocking writes
SET maintenance_work_mem = '2GB';
SET max_parallel_maintenance_workers = 4;
CREATE INDEX CONCURRENTLY items_embedding_hnsw
  ON items USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Half-precision storage by expression, with the same operator class family
CREATE INDEX CONCURRENTLY items_embedding_half
  ON items USING hnsw ((embedding::halfvec(1536)) halfvec_cosine_ops);
```

A query must use the same expression (`embedding::halfvec(1536)`) to use the second
index. Keep the dimension count in step with the column.
