# Panel specification and replay

## Contents

- Panel template
- Example queries
- Replay worksheet
- Review checklist

## Panel template

Fill this in for every panel before building it; a panel that cannot complete it does not go on the overview.

| Field | Content |
| --- | --- |
| Question | The title, phrased as a question |
| Row | Broken, for whom, dependencies, saturation, changes |
| Query | The exact expression |
| Unit | Requests per second, seconds, percent of valid events |
| Threshold | The SLO or alert value drawn as a line, or "none, and why" |
| Split | The dimension and the cap on series shown |
| Next step | The link or the runbook section opened when it looks bad |
| Evidence | The incident in which this was needed |

## Example queries

These assume Prometheus-style metrics named `http_server_request_duration_seconds` with `route`, `status_code` and `version` labels; adapt names to your instrumentation.

SLI over five minutes, good over valid, where valid excludes client errors:

```promql
sum(rate(http_server_request_duration_seconds_count{service="checkout", status_code=~"2..|3.."}[5m]))
/
sum(rate(http_server_request_duration_seconds_count{service="checkout", status_code!~"4.."}[5m]))
```

Here good is 2xx and 3xx and valid is everything except 4xx, so a client error counts for neither. Use the definition in `slo-design`, not this example, and check the ratio by hand against a known period.

Error ratio split by route, top five, over five minutes:

```promql
topk(5,
  sum by (route) (rate(http_server_request_duration_seconds_count{service="checkout", status_code=~"5.."}[5m]))
  /
  sum by (route) (rate(http_server_request_duration_seconds_count{service="checkout"}[5m]))
)
```

Latency p99 by version from a histogram:

```promql
histogram_quantile(0.99,
  sum by (le, version) (rate(http_server_request_duration_seconds_bucket{service="checkout"}[5m])))
```

Burn rate against a 99.9 percent objective (error budget 0.001), short window. The denominator excludes 4xx so it matches the valid set of the SLI panel; both follow the slo-design definition:

```promql
(
  sum(rate(http_server_request_duration_seconds_count{service="checkout", status_code=~"5.."}[5m]))
  /
  sum(rate(http_server_request_duration_seconds_count{service="checkout", status_code!~"4.."}[5m]))
) / 0.001
```

A value of 1 spends the budget exactly over the full window; draw the paging thresholds from `alert-design` as lines. For latency histograms with poor bucket placement, see `latency-histogram-design` before trusting a percentile near an SLO.

## Replay worksheet

For each incident, with the dashboard set to the incident's time range:

| Question | Answer from the page alone | Time taken | Gap |
| --- | --- | --- | --- |
| Is something wrong? | | | |
| Since when? | | | |
| Which slice (route, version, region)? | | | |
| Is a dependency involved? | | | |
| Is a resource saturated? | | | |
| What changed nearby? | | | |
| Which link was used to get the cause? | | | |

A gap with a name goes to a split, a link or an instrumentation ticket. A row answered in seconds with no panel behind it is a sign the reader used knowledge that a newcomer lacks.

## Review checklist

- Every panel title ends in a question mark or names the question.
- Every panel with an SLO has the threshold line.
- No panel has two y-axes.
- Splits use the same labels and colours throughout.
- Each row has a link out with service, environment and range filled.
- Fewer than about twenty panels on the overview; the rest on linked pages.
- Dashboard stored as code with an owner.
