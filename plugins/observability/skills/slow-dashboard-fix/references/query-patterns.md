# Query patterns for dashboard speed

Contents: cost table template, rewrites, recording rule file, step arithmetic, retest checklist.

## Cost table

| Panel | Query (short) | Time (s) | Series | Points | Runs per hour | Total (s per hour) |
| --- | --- | --- | --- | --- | --- | --- |
| Request rate by pod | sum by (pod) (rate(...)) | 9.2 | 4100 | 2.4M | 360 | 3312 |

Runs per hour for a panel is refreshes per hour (3600 divided by the refresh interval in seconds) times concurrent viewers, plus loads per hour; the table is per panel, so panel count is not a factor. If you cannot count viewers, use the backend's query log to count how often the same expression arrives.

## Rewrites

Heavy repeated aggregation, before:

```promql
sum by (service) (rate(http_requests_total[5m]))
```

After, with a recording rule and a panel that reads it:

```yaml
groups:
  - name: service_http
    interval: 1m
    rules:
      - record: service:http_requests:rate5m
        expr: sum by (service) (rate(http_requests_total[5m]))
```

```promql
service:http_requests:rate5m{service=~"$service"}
```

Check the file with `promtool check rules rules.yml`.

Hard-coded window, before and after:

```promql
rate(http_requests_total{job="api"}[5m])
rate(http_requests_total{job="api"}[$__rate_interval])
```

Unreadable grouping, before and after:

```promql
sum by (pod) (rate(container_cpu_usage_seconds_total[$__rate_interval]))
topk(10, sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="$namespace"}[$__rate_interval])))
```

Bounded variable, before and after:

```promql
label_values(up, instance)
label_values(up{job="$job"}, instance)
```

## Step arithmetic

Points per series is range divided by step. A 30-day range at a 15 second step is 172,800 points; at a 15 minute step it is 2,880. Set maximum data points so Grafana picks the step, and set minimum interval no lower than the scrape or rule interval, because a step finer than the data adds cost and no information.

## Retest checklist

1. Same range, same refresh, same variables as the baseline.
2. Cold load, then warm load.
3. Series and points returned per panel, not only time.
4. Rule evaluation duration for any new recording rule.
5. Backend query rate and duration for this dashboard after one hour of normal use.
