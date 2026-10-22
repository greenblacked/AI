# Judgments and `_rank_eval`

Reference for steps 1 and 2.

## Contents

- [The judgment file](#the-judgment-file)
- [Building the three groups](#building-the-three-groups)
- [A `_rank_eval` request](#a-_rank_eval-request)
- [Reading the output](#reading-the-output)

## The judgment file

One JSON object per query, in version control beside the query templates:

```json
{
  "id": "q-0042",
  "query": "running shoes",
  "category": "head",
  "snapshot": "2026-10-01",
  "ratings": [
    { "doc": "sku-1001", "grade": 3 },
    { "doc": "sku-2044", "grade": 2 },
    { "doc": "sku-9120", "grade": 0 }
  ]
}
```

Grades: 0 irrelevant, 1 related but not wanted, 2 good, 3 the ideal answer. Write the
grading guide in the same repository so a second grader reaches the same number. Have two
people grade a sample of 30 queries and compare; if they disagree often, the guide is
the problem, not the graders.

## Building the three groups

- Top 100 by volume: group the search log by normalised query text (lowercase, trimmed) and
  take the most frequent. These protect the traffic that matters most.
- 50 zero-result queries: take them from the log where hits were 0, sampled across the
  frequency range, not only the most frequent. Grade what the product does have that
  should have been found; if nothing, record an empty rating list to confirm the zero is
  correct.
- The complaint list: every reported bad query from support, sales or feedback, with the
  document the reporter expected. Add each new complaint to the set when it is fixed so it
  cannot return.

## A `_rank_eval` request

```bash
curl -s -X GET "$ES/products/_rank_eval" -H 'Content-Type: application/json' -d '{
  "requests": [
    {
      "id": "q-0042",
      "request": { "query": { "multi_match": { "query": "running shoes", "fields": ["name^3", "description"] } } },
      "ratings": [
        { "_index": "products", "_id": "sku-1001", "rating": 3 },
        { "_index": "products", "_id": "sku-2044", "rating": 2 }
      ]
    }
  ],
  "metric": { "dcg": { "k": 10, "normalize": true } }
}'
```

`dcg` with `normalize: true` is NDCG. For reciprocal rank use
`"metric": { "mean_reciprocal_rank": { "k": 10 } }`. Generate the request from the
judgment file with a short script rather than by hand, and use a template
(`"templates"` plus `"params"` in the body) so every query goes through the same query
shape you ship. Run against the alias the application uses, or against a scratch index
for analyser changes.

## Reading the output

The response carries `metric_score` (the mean) and `details`, keyed by request id, with
each query's `metric_score` and an `unrated_docs` list. Save both. Sort per-query deltas
between two runs; a mean that rose by a point can hide ten queries that fell badly. The
unrated list is the grading to-do list for the next round.
