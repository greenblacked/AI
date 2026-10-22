# Patterns and queries

## Contents

- Patterns
- Luhn check
- Query shapes
- Reporting without leaking

## Patterns

PCRE/RE2-style regular expressions (what Loki, OTTL and `grep -P` accept); tune for your stack and run on a sample, not the whole store.

| Pattern | Expression | Notes |
| --- | --- | --- |
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | exclude your own service accounts and `.invalid` canaries when counting |
| JWT | `eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*` | `eyJ` is the base64url start of `{"` |
| Authorization header | `(?i)authorization["']?\s*[:=]\s*["']?(bearer\|basic)\s+\S+` | also search attribute keys such as `http.request.header.authorization` |
| Long hex | `\b[0-9a-f]{32,}\b` | trace ids are 32 hex characters: exclude the `trace_id` field or the count is all trace ids |
| Long base64 | `\b[A-Za-z0-9+/_-]{40,}={0,2}` | high false-positive rate; rank by source and inspect a few |
| Card candidate | `\b(?:\d[ -]?){13,19}\b` | accept only if the Luhn check passes |

## Luhn check

Strip spaces and hyphens, keep candidates of 13 to 19 digits, and apply:

```python
def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
```

Run this over a locally saved sample and print counts only, never the matched digits.

## Query shapes

Loki, through `logcli`, counting rather than printing:

```bash
logcli instant-query --limit=100 \
  'sum by (service) (count_over_time({env="prod"} |~ "eyJ[A-Za-z0-9_-]{8,}\\.eyJ" [1h]))'
```

Elasticsearch, count of documents with a JWT-shaped string in the message field:

```bash
curl -s "$ES/logs-*/_count" -H 'Content-Type: application/json' -d '{
  "query": {"regexp": {"message": {"value": ".*eyJ[A-Za-z0-9_-]{8,}.*", "flags": "NONE", "case_insensitive": true}}}
}' | jq .count
```

Regexp is a term-level query, and an analysed text field stores lowercased terms, so the case-insensitive option (or a keyword sub-field such as `message.keyword`, which is truncated at its `ignore_above` limit) is needed for the pattern to match at all. A zero count proves nothing until a known canary value, sent through the same path, has been counted by the same query. Regexp queries on large indices are slow; restrict by time range and service, and run off peak. Trace stores differ: use the store's attribute search for the keys that should never hold values (`http.request.header.authorization`, `db.statement` with literals) and export a sample of spans for local scanning.

Metric labels: list label names and a sample of values per label, then flag any label whose values look like emails, ids or tokens (`topk(20, count by (__name__)({__name__=~".+"}))` shows which metrics are large; inspect the label values of those through the series API).

## Reporting without leaking

Record pattern name, signal, source, count and a redacted example in which only the first two characters and the length are shown; the rest is masked. Store the raw sample in a restricted location and delete it when the audit closes.
