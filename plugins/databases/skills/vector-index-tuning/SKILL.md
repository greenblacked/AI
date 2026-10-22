---
name: vector-index-tuning
description: "Tune an approximate nearest-neighbour index against measured recall and latency: compute exact top-k by brute force for about 1,000 sampled real queries, score recall@k as overlap with the index's answers, tune to a stated target such as recall 0.95 at k=10 and a p95 rather than defaults. Covers pgvector HNSW (ef_search via SET LOCAL, maintenance_work_mem) and IVFFlat (lists, probes), OpenSearch k-NN, Elasticsearch knn, the filtered-search trap returning fewer than k rows, and memory cuts with halfvec or quantisation plus exact re-ranking. Use for \"vector search misses obvious neighbours\", \"HNSW build takes forever\", \"filtered vector query returns fewer than k\", \"pick ef_search or lists\" or \"vector index uses too much memory\". Not for chunking, hybrid search and the pipeline (rag-design), relevance judgments (retrieval-evaluation) or table design (schema-design)."
allowed-tools: Read, Glob, Grep
---

# Vector Index Tuning

This skill is done when the index meets a written target (for example recall 0.95 at k=10 with a p95 under a stated number) on real queries, measured against exact results, with the settings that achieved it recorded and a plan for the filtered queries.

The usual failure is shipping defaults and judging by eye. An approximate index returns plausible neighbours whichever settings you pick, so a recall of 0.7 looks fine in a demo and shows up months later as "search misses obvious things". Recall is only visible when compared with the exact answer, and it is cheap to compute.

Run SQL and requests through the normal permission prompt, on a copy of the data or a replica for the brute-force pass, which scans the whole table.

## Scope

Use for: setting index parameters, building and rebuilding the index, diagnosing missed neighbours, filtered-query behaviour and memory use, for pgvector, OpenSearch k-NN, Elasticsearch knn and dedicated vector stores.

Do not use for: chunking, hybrid lexical-plus-dense search, reranking and the pipeline around the index, which is `rag-design`; whether the right documents are relevant to the question, which is `retrieval-evaluation` (this skill measures approximation error against exact search, not relevance); table and column design, which is `schema-design`.

## Workflow

### 1. Write the target

State the recall at k the product needs, the latency percentile and the memory budget. Recall 0.95 at k=10 with p95 under a number is a typical shape. Without a target, tuning has no stopping point: more recall always costs latency.

### 2. Build the ground truth

Sample about 1,000 real query vectors from production traffic (not rows from the table itself, whose nearest neighbour is themselves). For each, compute the exact top-k by brute force and store the ids. In pgvector, disable index use for the session so the planner scans exactly:

```sql
SET enable_indexscan = off;
SET enable_bitmapscan = off;
SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
```

Use the same distance operator the index was built for (`<=>` cosine, `<->` L2, `<#>` negative inner product); an index serves only the operator class it was created with. In OpenSearch or Elasticsearch, compute exact neighbours with a `script_score` query over a match-all, or the engine's exact-search option, and keep it away from live traffic. Recall@k for a query is the size of the overlap between the index's ids and the exact ids, divided by k; average over the sample. Read `references/measurement-and-settings.md` for a harness.

### 3. Measure the current index

Run the same 1,000 queries through the index at the current settings, recording recall@k and latency percentiles together. Warm the cache first and report the percentile that matches the target. Record data size, index size and build time.

### 4. Tune one setting at a time

For pgvector HNSW the query-time knob is `hnsw.ef_search` (default 40, must be at least k). Set it per query so one workload does not set it for all:

```sql
BEGIN;
SET LOCAL hnsw.ef_search = 100;
SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
COMMIT;
```

Raise `ef_search` until recall meets the target, then stop: latency grows with it. If recall plateaus below target, the graph itself is the limit and needs a rebuild with higher `m` (default 16) or `ef_construction` (default 64), which costs build time and memory.

For IVFFlat, create the index after loading representative data, because the lists are computed from the rows present. Start with `lists` of rows / 1000 up to a million rows and sqrt(rows) beyond, and `ivfflat.probes` near sqrt(lists), as the pgvector README advises; the default `probes` is 1, which gives poor recall. Raise `probes` for recall, and rebuild when the data distribution shifts.

For OpenSearch k-NN and Elasticsearch knn, the equivalents are `ef_search` (OpenSearch index setting for the HNSW method) and `num_candidates` (Elasticsearch, per request, which must be at least k). Same protocol: raise until the target recall holds on the sample, then compare p95.

### 5. Make the build tolerable

HNSW builds slow sharply once the graph no longer fits in `maintenance_work_mem`; pgvector notes this when it happens. Set `maintenance_work_mem` high enough for the graph for the build session and raise `max_parallel_maintenance_workers` (parallel HNSW builds exist from pgvector 0.6.0). Build with `CREATE INDEX CONCURRENTLY` on a live table, and build after the bulk load rather than before it. Time a build on a sample before promising a window for the full table.

### 6. Handle filtered queries

A selective `WHERE` combined with an approximate scan is the usual cause of "fewer than k rows". The index returns its candidate set (for HNSW, `ef_search` rows), the filter is applied afterwards, and a filter that keeps 1 percent of rows leaves under one row on average, often zero. Options in order of effort:

- iterative index scans, available from pgvector 0.8.0 (`hnsw.iterative_scan` set to `strict_order` or `relaxed_order`, with `hnsw.max_scan_tuples` bounding the work), which keeps scanning until enough rows pass the filter;
- a partial index per large tenant or category, so the filter is the index predicate;
- partitions by the filter column, each with its own index.

Elasticsearch and OpenSearch have their own filter semantics (the filter inside knn applies during the search in Elasticsearch; check your engine's documentation for the mode in use), so test filtered recall on the sample rather than assuming. Measure filtered queries as their own category, with a sample drawn from realistic filters.

### 7. Cut memory only with a recall check

Options: store as `halfvec` (pgvector 0.7.0 and later), or use scalar or binary quantisation in the engine, then re-rank the top candidates with the original full-precision vectors. Compare recall against the ground truth before and after; quantisation without exact re-ranking usually costs measurable recall. Fewer dimensions from the embedding model is the other lever, and it changes the embeddings, so it is a re-embed.

### 8. Record and monitor

Write the settings, the recall and latency table, and the sample file into the repository. Re-run the sample after large data loads, a model change or a version upgrade, since recall drifts as the data does.

## Output format

```markdown
## Target
[Recall at k, latency percentile, memory budget.]

## Ground truth
[Sample size and source, distance operator, how exact results were produced.]

## Results
[Table: setting, recall@k, p50/p95, index size, build time. Filtered queries separately.]

## Decision
[Chosen parameters, where they are set (per query, per role), rebuild conditions.]
```

## Anti-patterns

**Defaults as a decision.** `probes` of 1 or an untouched `ef_search` is a recall nobody measured.

**Using table rows as test queries.** Each finds itself; recall looks perfect and means nothing.

**Setting ef_search globally.** One high-recall workload makes every query slower; use `SET LOCAL`.

**Building IVFFlat on an empty table.** The lists come from the data at build time; build after loading.

**Quantising without re-ranking.** Memory drops and recall drops with it; check the sample.

## Reference files

- `references/measurement-and-settings.md` - read at steps 2 to 7: a recall harness, the settings table per engine, and the filtered-search checks.
