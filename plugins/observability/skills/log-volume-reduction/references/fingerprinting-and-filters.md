# Fingerprinting and filters

## Fingerprint recipe

Normalise the message, then count. Replace, in this order:

1. UUIDs (case-insensitive): `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` becomes `<uuid>`
2. ISO timestamps become `<ts>`
3. IP addresses and hex strings of 8 or more characters containing at least one letter a-f (case-insensitive) become `<ip>` and `<hex>`
4. any remaining run of digits, epoch timestamps included, becomes `<n>`

Quoted strings are not normalised by the script below; if messages embed long quoted payloads, add a pattern for them or cut the message at a fixed length.

A short script over a one-hour sample is enough. It reads raw bytes so that one invalid byte does not abort the run, and it counts the length of each line as it was on disk:

```python
import re, sys, collections

I = re.IGNORECASE
pats = [
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", I), "<uuid>"),
    (re.compile(r"\d{4}-\d\d-\d\dT[\d:.]+Z?"), "<ts>"),
    (re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{8,}\b", I), "<hex>"),
    (re.compile(r"\d+"), "<n>"),
]
bytes_by = collections.Counter()
for raw in sys.stdin.buffer:
    key = raw.decode("utf-8", errors="replace")
    for p, r in pats:
        key = p.sub(r, key)
    bytes_by[key.strip()[:200]] += len(raw)
for k, v in bytes_by.most_common(25):
    print(v, k)
```

Multiply each template's daily bytes by the retention days of its index to rank.

## Query shapes

Loki, bytes per service per day:

```logql
sum by (service) (bytes_over_time({env="prod"}[1d]))
```

Loki, one service's volume by level:

```logql
sum by (level) (bytes_over_time({env="prod", service="checkout"} | json [1h]))
```

Elasticsearch, largest indices:

```text
GET _cat/indices?v&s=pri.store.size:desc&bytes=b
```

Hosted vendors expose the same through usage attribution by tag; group by service and by index, then drill into the top service's log explorer grouped by message pattern.

## Count-only, then drop

Tag first. In an OpenTelemetry Collector the `transform` processor can add an attribute on matching records; in other shippers use the equivalent field add. Example intent:

- match: `severity_text == "DEBUG"` or the health-check path
- action in count-only: set attribute `would_drop` to `true`
- action in enforce: drop the record with the `filter` processor, or exclude it at the agent

Sampling rule intent: for success records, keep 1 in N by hashing a stable field (request id) so a request's lines are kept or dropped together, and set `sample_rate` to N on every kept record.

Confirm field names and processor options against the version of the collector or shipper you run before deploying.

## Dependence search

Search checked-in definitions for the message text or field:

```bash
grep -rn "payment declined" alerts/ dashboards/ runbooks/
```

Then list saved searches and log-based monitors in the backend's UI or API for the same text, and ask the owning teams about anything not in version control.
