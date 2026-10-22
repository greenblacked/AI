# Diagnostics and relabel snippets

## Is it cardinality

- `prometheus_tsdb_head_series` — active series in memory.
- `rate(prometheus_tsdb_head_series_created_total[5m])` — creation rate; a sustained high
  value with churn (series also removed) points at short-lived label values.
- `rate(prometheus_tsdb_head_samples_appended_total[5m])` — samples per second.
- `process_resident_memory_bytes{job="prometheus"}` against the container limit.

## Which job

- `topk(10, scrape_series_added)` — series first seen on the most recent scrape, per target.
- `topk(10, scrape_samples_post_metric_relabeling)` — samples kept after relabelling.

## Which metric, without the status endpoint

`topk(10, count by (__name__)({__name__=~".+"}))` touches every series and is itself
expensive on a server that is already struggling. Use the status endpoint first.

## Relabel snippets

Drop a metric:

```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    regex: http_request_duration_seconds_bucket
    action: drop
```

Drop a label:

```yaml
metric_relabel_configs:
  - regex: user_id
    action: labeldrop
```

Guards on a job:

```yaml
scrape_configs:
  - job_name: checkout
    sample_limit: 50000
    label_limit: 30
    label_value_length_limit: 200
```

Pick `sample_limit` from the job's normal sample count with room for growth; a limit set
at the current value fails scrapes on the first deploy that adds a metric.

## Record template

| Field | Value |
| --- | --- |
| Metric | |
| Label | |
| Distinct values | |
| Series before / peak / after | |
| Started / stopped | |
| Stopped by | |
| Owner | |
| Source fix | |
| Guard added | |
