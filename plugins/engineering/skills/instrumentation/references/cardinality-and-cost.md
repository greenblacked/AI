# Cardinality, and what observability actually costs

Read this when a bill jumped, a metrics backend is struggling, or you are sizing a new
metric before it ships. The arithmetic is simple and the surprise is always the same:
labels multiply, and nobody did the multiplication.

## Contents

- The arithmetic
- Which label is which
- Finding the runaway
- Guard rails that fail loudly
- Exemplars instead of an identity label
- Retention and downsampling
- What each signal costs

## The arithmetic

A metric's series count is the product of the distinct values of its labels, counted
over the retention window rather than at this instant, and multiplied by the number of
processes reporting it.

```text
http_server_request_duration_seconds
  route            12
  method            4
  status class      5
  pod              40
  histogram bucket 12 (a histogram is one series per bucket, plus sum and count)
  ------------------------------------------------------------------
  12 x 4 x 5 x 40 x 14 = 134,400 series for one metric
```

That is already large, and it is the version with no mistakes in it. Now add one label:

```text
+ tenant id (2,000 tenants)         =  268,800,000 series
+ raw path containing an order id   =  unbounded — grows for as long as orders exist
```

The second line is the classic self-inflicted outage. It happens when the label is the
request path instead of the route template, so `/orders/8a41` and `/orders/8a42` are
distinct series that live until retention expires — and they are never queried again
after the second they are written.

Do this multiplication in the pull request that adds the metric. It takes a minute and
it is the only moment anybody will.

## Which label is which

| Bounded, safe on a metric | Unbounded, keep it on spans and logs |
| --- | --- |
| Route template (`/orders/{id}`) | Raw path, full URL, query string |
| HTTP method, status class, gRPC code | Formatted error message |
| Dependency name, database, queue, topic | User, tenant, order, session, request, trace id |
| Region, availability zone, cluster | Customer email or any user-supplied string |
| Tenant *tier* (free, pro, enterprise) | Raw SQL text |
| Deploy version | Timestamps, durations, byte counts as labels |
| Job or consumer group name | Container id, pod name on a high-churn deployment |

Two habitual mistakes hide in that right-hand column. **Pod name** is bounded on a
weekly-deploy service and effectively unbounded on one that redeploys hourly, because
retired pods keep their series until retention expires — judge by distinct values over
the window, not by how many exist now. **Error message** looks bounded until one message
interpolates an id; use a stable `error.type` for counting and keep the text in the log.

## Finding the runaway

```promql
# Which metric names own the series
topk(20, count by (__name__)({__name__=~".+"}))

# Which job, for the worst metric
topk(20, count by (job) ({__name__="the_offending_metric"}))

# Which label is doing it
count(count by (suspect_label) ({__name__="the_offending_metric"}))

# Head series over time — the trend is the alert, not the absolute number
sum(prometheus_tsdb_head_series)

# Which scrape target grew
topk(10, scrape_samples_scraped)
```

For a hosted backend, the equivalents are the vendor's cardinality or usage explorer and
per-metric billing breakdown. Look at growth rate rather than the total: a metric that
doubled last week is the story, and a large but flat one has already been paid for.

Run this on a schedule, not only after a bill. The gap between a bad deploy and its
invoice is usually a month, which is a month of the wrong shape of data.

## Guard rails that fail loudly

A limit that stops a bad metric at the source is worth more than a dashboard nobody
watches, because it fails at deploy time, in front of the person who caused it:

```yaml
# Prometheus scrape config: this target's scrape fails rather than growing the TSDB
scrape_configs:
  - job_name: checkout
    sample_limit: 20000
    label_limit: 30
    label_value_length_limit: 128
    target_limit: 200
```

Pair it with an alert on head-series growth and on `scrape_samples_post_metric_relabeling`
approaching the limit, so the failure is visible before it is total. Where the backend
supports per-metric or per-tenant limits, set them; the failure mode of no limit is that
one team's mistake degrades everyone's queries.

Relabelling is the escape hatch when a bad label ships and cannot be reverted quickly:

```yaml
metric_relabel_configs:
  - source_labels: [user_id]
    action: labeldrop     # stop ingesting it now; fix the instrumentation properly after
```

## Exemplars instead of an identity label

The reason people add a user id to a metric is to get from a spike back to a specific
case. Exemplars do that without the multiplication: each histogram bucket carries a
sample trace id, so the spike links to a real trace that carries the identity as span
attributes.

```text
http_server_request_duration_seconds_bucket{route="/orders/{id}",le="1.0"} 4231 # {trace_id="4bf92f..."} 0.93 1757000000
```

Enable exemplar storage in the backend and exemplar emission in the SDK, and confirm the
click-through works before deleting whatever identity label prompted the question. The
answer "which customer" then comes from the trace and the log, where identity is priced
per event.

## Retention and downsampling

| Signal | Hot tier | Warm or rolled up | Notes |
| --- | --- | --- | --- |
| Metrics | Raw 10-30s for ~15 days | 5m rollup for 13 months | The 13 months is what makes year-on-year comparison possible; the raw tier is what makes an incident debuggable |
| Traces | 7 days, fully searchable | Optionally keep sampled-interesting traces 30 days | A trace older than the incident is opened by almost nobody |
| Logs | 7-30 days indexed | Compressed object storage for the compliance period | Indexing is most of the cost; storage without an index is cheap |
| Events, deploys, audit | 13 months | Longer if compliance requires | Tiny volume, disproportionate value during an investigation |

Downsample rather than delete where trend matters. A five-minute rollup answers capacity
and seasonality questions at a fraction of the cost, and the raw tier only ever gets read
inside the window where someone is actively investigating.

## What each signal costs

Rough shape, useful for deciding where to look first when a number surprises you:

- **Metrics** are priced by active series and by how long each is kept. Cost is driven by
  label combinations, not by traffic — a service at ten requests per second and one at
  ten thousand cost the same if their labels match.
- **Traces** are priced per span ingested, so cost is driven by traffic times sampling
  rate times spans per trace. Reducing spans per trace by not wrapping every function is
  as effective as changing the sampling rate, and loses less.
- **Logs** are priced by bytes ingested and bytes indexed. Cost is driven by verbosity
  and by structure — a stack trace on every expected 404 is a large, avoidable bill, and
  debug logging left on in production is the usual cause of a sudden jump.

Retention is where spend grows without a decision. Nobody proposes a retention increase;
it is inherited from a default and then multiplies every byte the team already agreed to
keep. Put the retention line in the design, review it against the invoice quarterly, and
expect to defend it after each incident, when the instinct is to keep everything forever.
