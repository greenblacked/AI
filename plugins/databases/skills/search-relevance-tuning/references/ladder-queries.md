# Ladder queries

Reference for steps 4 and 5. Elasticsearch syntax; OpenSearch accepts the same bodies for
these features except where noted.

## Contents

- [Rung 1: synonyms and analysis](#rung-1-synonyms-and-analysis)
- [Rung 2: multi_match](#rung-2-multi_match)
- [Rung 3: business signals](#rung-3-business-signals)
- [Rung 4: similarity](#rung-4-similarity)

## Rung 1: synonyms and analysis

```bash
curl -s -X PUT "$ES/products-scratch" -H 'Content-Type: application/json' -d '{
  "settings": { "analysis": {
    "filter": { "syn": { "type": "synonym_graph", "synonyms": ["tv, television", "sneakers, trainers"] } },
    "analyzer": {
      "text_index":  { "tokenizer": "standard", "filter": ["lowercase", "asciifolding"] },
      "text_search": { "tokenizer": "standard", "filter": ["lowercase", "asciifolding", "syn"] }
    } } },
  "mappings": { "properties": { "name": { "type": "text", "analyzer": "text_index", "search_analyzer": "text_search" } } }
}'
curl -s -X GET "$ES/products-scratch/_analyze" -H 'Content-Type: application/json' \
  -d '{ "field": "name", "analyzer": "text_search", "text": "Cafe TV" }'
```

Synonyms applied only at search time can change without reindexing. Check every
multi-word synonym with `_analyze`, and re-run the judged set because a synonym can pull
unrelated products in.

## Rung 2: multi_match

```json
{ "multi_match": {
    "query": "acme trail runner",
    "type": "cross_fields",
    "fields": ["brand^2", "name^3", "description"],
    "operator": "and"
} }
```

Use `best_fields` with `"tie_breaker": 0.2` when the whole query should match one field.
Use `cross_fields` when terms are spread over fields (brand in one, model in another);
it scores them as if they were one field, which avoids a brand-only match outranking a
full match. Change one weight per run.

## Rung 3: business signals

Map a numeric field as `rank_feature` (positive values only), then add it as a `should`
clause so it contributes a bounded amount:

```json
{ "bool": {
    "must":   [ { "multi_match": { "query": "running shoes", "fields": ["name^3", "description"] } } ],
    "should": [ { "rank_feature": { "field": "popularity", "saturation": { "pivot": 50 } } } ]
} }
```

`saturation` returns value / (value + pivot), so it approaches 1 and never swamps the
text score; set `pivot` near the median of the field. `log` and `sigmoid` are the other
shapes. If `function_score` is required (for example a recency decay), use a bounded
function with `boost_mode: "sum"` or cap with `max_boost`, not a bare `field_value_factor`
multiplier.

## Rung 4: similarity

```json
{ "settings": { "index": { "similarity": { "tuned_bm25": { "type": "BM25", "k1": 1.2, "b": 0.75 } } } },
  "mappings": { "properties": { "description": { "type": "text", "similarity": "tuned_bm25" } } } }
```

Defaults are k1 1.2 and b 0.75. Lower `b` reduces the penalty on long fields; raise `k1`
to let repeated terms count for more. Build on a scratch index, compare with the judged
set, and expect small differences.
