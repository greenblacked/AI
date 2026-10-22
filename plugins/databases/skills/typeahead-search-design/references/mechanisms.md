# Mechanisms

Reference for steps 1 to 5. Elasticsearch syntax; OpenSearch accepts the same bodies for
these features.

## Contents

- [Completion suggester](#completion-suggester)
- [search_as_you_type](#search_as_you_type)
- [Edge n-gram analyser](#edge-n-gram-analyser)
- [Ranking and filters](#ranking-and-filters)

## Completion suggester

```json
{ "mappings": { "properties": {
    "suggest": { "type": "completion",
                 "contexts": [ { "name": "tenant", "type": "category" } ] } } } }
```

```json
{ "suggest": { "s": { "prefix": "runni",
    "completion": { "field": "suggest", "size": 8, "skip_duplicates": true,
                    "fuzzy": { "fuzziness": 1, "prefix_length": 2 },
                    "contexts": { "tenant": ["t-42"] } } } } }
```

Index each curated term with an optional `weight` for popularity. Matching is on the
prefix of the input only, so it cannot find "shoes" from "run shoes" unless that string is
also an input. Returned suggestions come from the index, not a live document filter.

## search_as_you_type

```json
{ "mappings": { "properties": { "title": { "type": "search_as_you_type" } } } }
```

```json
{ "query": { "multi_match": {
    "query": "brown f", "type": "bool_prefix",
    "fields": ["title", "title._2gram", "title._3gram"] } } }
```

The field creates `_2gram`, `_3gram` and `_index_prefix` subfields. The last term is
treated as a prefix and the earlier terms as whole words, so mid-phrase typing works.

## Edge n-gram analyser

```json
{ "settings": { "analysis": {
    "filter": { "edge": { "type": "edge_ngram", "min_gram": 2, "max_gram": 15 },
               "cap": { "type": "truncate", "length": 15 } },
    "analyzer": {
      "edge_index": { "tokenizer": "standard", "filter": ["lowercase", "edge"] },
      "plain_search": { "tokenizer": "standard", "filter": ["lowercase", "cap"] } } } },
  "mappings": { "properties": { "name": {
      "type": "text", "analyzer": "edge_index", "search_analyzer": "plain_search" } } } }
```

Check both sides with `_analyze`: the index analyser on "running" should list "ru", "run"
and so on up to "running" itself: grams stop at the word's length when it is shorter than
`max_gram`, and at `max_gram` otherwise. The search analyser on "run" should list only "run".
Words longer than `max_gram` are indexed up to that length only, so a plain search analyser would find nothing for a typed word longer than `max_gram`, the most specific input. The `truncate` filter (`cap`, with `length` equal to `max_gram`) in the search analyser cuts the query term to the longest indexed gram. Keep the two lengths equal.

## Ranking and filters

```json
{ "query": { "bool": {
    "must": [ { "match": { "name": { "query": "run", "fuzziness": "AUTO", "prefix_length": 1 } } } ],
    "filter": [ { "term": { "tenant_id": "t-42" } } ],
    "should": [
      { "term": { "name.raw": { "value": "run", "boost": 5 } } },
      { "rank_feature": { "field": "popularity", "saturation": { "pivot": 100 } } } ] } },
  "size": 8 }
```

The `name.raw` field is a keyword multi-field you add to the mapping, and `popularity` needs a `rank_feature` field mapping (`"popularity": { "type": "rank_feature" }`, a positive number per document); without it the `rank_feature` clause is rejected. The tenant filter sits in `filter`, so it is part of candidate selection. The exact-value
boost lifts a whole-term match above prefix matches; adapt it to a prefix clause on the
keyword subfield for phrase prefixes. Confirm in the replay that fuzzy matching on an
edge n-gram field behaves as expected before relying on it.
