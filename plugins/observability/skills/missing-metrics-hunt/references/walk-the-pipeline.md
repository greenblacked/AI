# Walking the pipeline

Stop at the first row whose check fails.

| Stage | Check | Healthy | If not |
| --- | --- | --- | --- |
| Exposed | `curl` the target's metrics path and grep the metric name | Present with expected labels | Source change: rename, lazy registration, wrong registry |
| Discovered | Targets page, or `up{job="x"}` has a series | One series per target | Discovery selector, port, annotation, namespace |
| Scraped | `up == 1`; `scrape_duration_seconds` well under timeout | 1 and fast | Network policy, auth, slow endpoint, timeout too low |
| Kept at ingest | `scrape_samples_scraped` vs `scrape_samples_post_metric_relabeling` | Equal, or the difference is intended | Relabel drop rule |
| Within limits | Scrape not failing on `sample_limit` or `label_limit` | No failures | Raise the limit or remove the offender |
| Stored | Raw selector `x[10m]` on the local server | Samples at the scrape interval | Previous rows |
| Shipped | Highest timestamp scraped vs highest sent | Difference of a few seconds | Remote write queue, endpoint, auth, backend limits |
| Queried | Same selector against the remote store | Same samples | Tenant, retention, data source |
| Calculated | `rate` range at least four scrape intervals | Non-empty result | Lengthen range; initialise counters |
| Drawn | Panel query vs the raw selector | Same values | Panel transform, step, unit, data source choice |

## Choosing the rate range

Four scrape intervals leaves room for one missed scrape while still holding two samples.
At a 15-second interval that is one minute; at 60 seconds it is four minutes. A panel
step coarser than the range skips data, so keep the step no larger than the range.

## Initialising a counter

For each known combination of label values, increment by zero or register the child at
startup. Most client libraries provide a way to touch a labelled child so it exports a
zero value from the first scrape.
