# Measuring orphans and single-span traces

Column names differ by backend; the shape of the query is what matters. Assume a span
table with `trace_id`, `span_id`, `parent_span_id` (empty for a root), `service`,
`start_time`. Treat these as sketches to adapt, not as syntax for any one store.

## Orphan rate per service

```sql
SELECT s.service,
       count(*) AS spans,
       sum(CASE WHEN s.parent_span_id <> '' AND p.span_id IS NULL THEN 1 ELSE 0 END) AS orphans
FROM spans s
LEFT JOIN spans p
  ON p.trace_id = s.trace_id AND p.span_id = s.parent_span_id
WHERE s.trace_id IN (
  SELECT trace_id FROM spans
  WHERE parent_span_id = '' AND start_time BETWEEN :from AND :to
)
GROUP BY s.service
ORDER BY orphans DESC;
```

Restrict `:to` to at least a few minutes before now so late-arriving parents are present.

## Which service the missing parents belonged to

The missing parent is absent, so its service cannot be read from it, and its client span
(where `peer.service` would live) is the span that is missing. Identify the caller from
what does exist: attributes on the orphan's own server span such as `client.address` or a
messaging source, or the other spans sharing its `trace_id`. Orphans clustered under one
callee with varied callers say the callee is the break. Orphans that all trace back to one
caller say that caller is not exporting. A trace whose root is absent too is not selected by
the queries above; sample those by hand.

## Single-span traces per root service

```sql
SELECT service, count(*) AS single_span_traces
FROM (
  SELECT trace_id, min(service) AS service, count(*) AS n
  FROM spans
  WHERE trace_id IN (
    SELECT trace_id FROM spans
    WHERE parent_span_id = '' AND start_time BETWEEN :from AND :to
  )
  GROUP BY trace_id
) t
WHERE n = 1
GROUP BY service
ORDER BY single_span_traces DESC;
```

Compare the count with total traces for the same service. A health-check endpoint or a
cron job legitimately produces single-span traces; exclude them by route before judging.

## Without a query language

Take 200 recent traces that include the suspect callee. For each, record whether the
callee's server span has a parent present. A rate above a few percent, concentrated in
one calling service, is enough to name the hop.
