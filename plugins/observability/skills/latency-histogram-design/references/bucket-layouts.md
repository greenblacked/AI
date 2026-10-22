# Bucket layouts and unit checks

Boundaries are in seconds for a metric named `*_seconds`. Always add the SLO threshold if it is not already listed.

## Starting layouts by route class

| Class | Typical range | Boundaries (seconds) |
| --- | --- | --- |
| Cache or health-style | under 20 ms | 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 1 |
| Typical API | 20 ms to 1 s | 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 2.5, 5 |
| Slow or batch-like | 1 s to minutes | 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300 |

Edit each layout so the SLO threshold, the client timeout and any retry-trigger value appear as boundaries. The timeout boundary matters: it separates slow from failed.

## Library defaults to recognise

| Source | Default boundaries | Unit |
| --- | --- | --- |
| Prometheus client libraries | 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10 | seconds |
| OpenTelemetry SDK explicit histogram | 0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000 | milliseconds |

Verify both against the version you run; defaults and the semantic-convention advice for seconds-based metrics have changed across releases. The mismatch to hunt for is the second row applied to a seconds metric: every request below 5 seconds falls in the 0 to 5 bucket. In OpenTelemetry SDKs, set explicit bucket boundaries through a view or the instrument's advisory boundaries rather than relying on the default.

## Checks

Distribution for one route over an hour:

```promql
sum by (le) (increase(http_server_request_duration_seconds_bucket{route="/checkout"}[1h]))
```

Cumulative buckets: divide each by the `+Inf` bucket to see the share at or below each boundary; the floor, `+Inf` and interpolation checks below use that cumulative share. Flag the histogram when:

- one bucket holds over about 95 percent of observations, judged on per-bucket counts (each `le` cumulative count minus the one below it), not on the cumulative share
- the lowest bucket already holds over 50 percent (floor too high)
- more than 1 percent falls in `+Inf` (ceiling too low)

Interpolation width for a quoted p99: find the first `le` whose cumulative share reaches 0.99 and the one before it; the difference is the width within which the value is uncertain.

Percentile over a longer window from recorded buckets:

```promql
histogram_quantile(0.99, sum by (le) (increase(http_server_request_duration_seconds_bucket[1h])))
```
