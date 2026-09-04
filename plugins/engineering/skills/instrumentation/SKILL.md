---
name: instrumentation
description: "Add telemetry to a service so the next incident is diagnosable: start from the questions you will need answered at 3am, choose a metric, a span or a log per question, instrument with OpenTelemetry and the semantic conventions, keep high-cardinality identity off metric labels and on spans, propagate trace context across queues, batch jobs and thread pools, and set sampling and retention that keep the interesting traces. Use this skill whenever someone is adding metrics, spans, structured logging or OpenTelemetry to a service, asks what a new service should emit or what to add after an incident showed a gap, or is fixing a cardinality explosion or an observability bill — including \"we could not tell which customer was affected\", \"add a metric for this\", or \"our traces stop at the queue\". Not for deciding what should page a human, diagnosing a live incident, profiling a slow function, or choosing a monitoring vendor."
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(promtool:*), Bash(otelcol:*), Bash(curl:*)
---

# Instrumentation

Good instrumentation is the smallest set of signals that answers, in one query each, the questions a responder will actually ask while the service is broken. Everything beyond that set is a bill.

Instrumentation is almost never added calmly. It is added the week after the incident where its absence hurt, by the person who spent that night guessing, and it is shaped entirely by that one incident: a counter for the exact failure that happened, a dashboard of the mechanism that broke, a log line at the place the reasoning ran out. The next incident is a different one. So the estate grows — more data, more panels, a larger invoice — while the questions that matter stay unanswerable: which customer is affected, is it us or a dependency, how long has it been happening, did the deploy do it. Meanwhile the growth is not in the signals anyone chose. It is in cardinality: a label somebody added to be helpful multiplies against every other label, and the bill arrives a quarter later attached to a metric nobody queries. The discipline that fixes both is the same one — write the question down first, and make each signal earn its place by answering one.

## Scope

Use for: deciding what a new service should emit before it ships; adding the signals an incident proved missing; choosing between a metric, a span and a log for a given question; adopting OpenTelemetry, its SDK, collector and semantic conventions; fixing a cardinality explosion or an observability bill; getting trace context through a queue, a batch job or a thread pool; putting trace ids into log lines; designing sampling and retention.

Do not use for: deciding what should page a human or writing the alerting rule (that is `alert-design`), diagnosing an incident happening right now (that is `k8s-triage`), profiling a slow function or hunting an allocation, or choosing between observability vendors (that is `vendor-evaluation`).

## The gate

Every signal you add names the question it answers, in the pull request body and ideally in a comment beside it. Two tests, both cheap:

1. **Which question does this answer?** If the answer is "it might be useful", it is a cost with no benefit. Telemetry does not become valuable by accumulating.
2. **If this were deleted tomorrow, what becomes unanswerable?** If nothing, delete it now rather than paying for it for three years.

A signal that fails both is not neutral. It occupies attention on a dashboard, adds series to a query's fan-out, and makes the honest signals harder to find.

## Workflow

### 1. Write the questions before choosing any signal

Four or five, phrased the way the person on call would say them at 3am, not the way a metric is named:

- Is it us, or a dependency we call?
- Which tenant, customer or segment is affected — everyone, or one?
- Which operation or code path is failing, out of the dozen this service runs?
- Is it getting worse, holding, or already recovering?
- Did the deploy do it, and which one?

Add the one or two specific to this service — is the queue draining, is the ledger balanced, did the nightly reconciliation run. Then instrument backwards from each. This ordering is the whole method: it produces a small estate that answers questions, instead of a large one that reports facts.

### 2. Choose the signal per question

| Signal | What it is for | What it costs | Where it fails |
| --- | --- | --- | --- |
| **Metric** | Aggregate over time, and anything alerting reads. Rates, ratios, quantiles, saturation. | Per series, forever, whether or not anyone queries it. | No per-request detail. You can never go from a spike back to the requests that made it. |
| **Trace** | Causality and latency attribution across service boundaries. Where the time went, which dependency, what the call graph actually is. | Per span ingested, controlled by sampling. | Sampled by construction, so it cannot be a source of truth for a rate. |
| **Log** | The specific instance you have already decided you want to look at, with full detail. | Per byte ingested and per byte indexed — the most expensive of the three. | Hopeless for aggregate. Computing a rate from logs is computing it at query time over your priciest store. |

Two substitutions cause most of the waste.

**Logs used as metrics.** Counting matching log lines to get an error rate means the number changes when somebody edits a log message, the aggregation runs over the expensive store every time anyone asks, and log sampling or retention silently changes the answer without changing the query. Emit a counter; keep the log line for the detail.

**Metrics used as logs.** Attaching a request id, user id or error message to a metric so the detail survives creates one series per request and turns a bounded cost into an unbounded one. Identity belongs on the span and in the log line, which are priced per event rather than per distinct combination.

### 3. Instrument with OpenTelemetry, auto-instrumentation first

Instrument once against the OpenTelemetry API and export wherever you like. That is the point of it: the backend decision stays reversible, and a vendor switch becomes a collector configuration change instead of a re-instrumentation project.

Order of work:

1. **Auto-instrumentation.** An agent or SDK distro gets you inbound HTTP server spans, outbound HTTP and gRPC client spans, database client spans and queue producer and consumer spans, with correct parenting and standard attributes, usually in a day. This is the request path, free, and it is the right first step every time.
2. **Resource attributes.** Set `service.name`, `service.version`, `deployment.environment.name` and the deploy identifier at startup. Without `service.version` the question "did the deploy do it" is an argument; with it, it is a group-by.
3. **Manual spans for business operations.** Auto-instrumentation names transport, not meaning. It knows there was a `POST /v1/orders` and three database calls; it does not know one of them was reserving inventory. Add spans for the operations that have a business meaning and their own failure mode — `checkout.reserve_inventory`, `invoice.settle`, `payment.authorize` — not for every function, which produces trace noise and per-span cost with no new answers.

   ```python
   from opentelemetry import trace

   tracer = trace.get_tracer("checkout")

   def reserve_inventory(order_id: str, tenant_id: str, sku_count: int) -> None:
       with tracer.start_as_current_span("checkout.reserve_inventory") as span:
           # High-cardinality identity is safe here and only here: spans are priced per
           # event, so tenant and order ids cost nothing extra and answer "which customer".
           span.set_attribute("acme.tenant.id", tenant_id)
           span.set_attribute("acme.order.id", order_id)
           span.set_attribute("acme.order.sku_count", sku_count)
           ...
   ```

4. **A collector between the application and the backend.** It gives you batching, retry, redaction of anything that should not leave the estate, tail sampling, and one place to change destination. Applications exporting straight to a vendor endpoint have to be redeployed to change any of that.

`references/otel-setup.md` has the SDK and collector configuration, the per-language auto-instrumentation entry points, and the exporter pipeline. Read it when wiring OpenTelemetry up rather than deciding what to measure.

### 4. Use the semantic conventions, and namespace what they do not cover

Use the standard attribute names — `http.request.method`, `http.response.status_code`, `url.template`, `server.address`, `db.system.name`, `db.operation.name`, `messaging.destination.name`, `error.type` — even when a shorter local name is tempting. Standard names are what make a dashboard portable between two services written by two teams in two languages, and what let a vendor's or the community's prebuilt dashboards and queries work at all. `httpStatus` in one service and `status_code` in another means every panel is bespoke and every query has an `or` in it.

For attributes the conventions do not cover, use your own namespace: `acme.tenant.id`, `acme.order.sku_count`. A namespace prevents a collision when a convention later claims the bare name, and it makes it obvious in a query which attributes are yours.

### 5. Hold the cardinality line

The rule, and it is the one that decides the bill: **bounded, low-cardinality dimensions on metrics; high-cardinality identity on spans and logs.**

A metric's series count is the product of its label value counts, per process. Multiplication is what surprises people:

```text
route (12) x method (4) x status class (5) x pod (40)          =    9,600 series — fine
the same, plus tenant id (2,000)                                = 19.2M series — an incident
the same, plus raw path with an order id in it (unbounded)      = unbounded — the classic outage
```

The last line is the one that takes down an observability backend, and it is nearly always accidental: the label is the raw URL path rather than the route template, so `/orders/8a41` and `/orders/8a42` are separate series forever.

| Safe as a metric label | Not a metric label |
| --- | --- |
| Route template, operation name, method, status class, dependency name, queue name, region, availability zone, tenant *tier*, deploy version | User, tenant, order, session, request or trace id, email, raw path or full URL, raw SQL, formatted error message, container id or pod name on a high-churn deployment, timestamps, anything derived from user input |

Pod name deserves its own note: it is bounded on a stable deployment and unbounded on one that redeploys hourly, because every retired pod's series lives on until retention expires. Judge a label by how many distinct values it will have over the retention window, not by how many exist right now.

Spot a runaway before the bill does:

```promql
topk(20, count by (__name__)({__name__=~".+"}))    # which metric names own the series
topk(20, count by (job, __name__)({__name__=~".+"}))
sum(prometheus_tsdb_head_series)                    # total, as a trend, alerted on growth
topk(10, scrape_samples_scraped)                    # which target grew
```

Put a `sample_limit` on the scrape config and a label-value limit where the backend supports one. A bad deploy then fails its own scrape and pages its author, which is recoverable, instead of quietly growing the head series until the whole TSDB falls over, which is not.

Where you need a metric spike and the identity behind it, use **exemplars**: the metric stays bounded and each bucket carries a trace id you can click through to. That is the supported way to have both, and it is why the identity does not need to be a label.

### 6. Propagate context, and correlate the three signals

Correlation is what turns three separate stores into one investigation:

- **Trace id in every log line.** Emit `trace_id` and `span_id` as structured fields from the logging integration, not by hand. Then a suspicious span leads to its logs, and a log line leads to the whole request. Without it, correlating is timestamp arithmetic across clocks that disagree.
- **Baggage for the tenant.** Put the tenant or account identifier in baggage at the edge so every downstream service can attribute its own work without a lookup. Keep baggage tiny; it travels on every request, and anything sensitive in it crosses every boundary the request does.
- **Exemplars from metrics to traces**, as above.

Propagation is W3C `traceparent` over HTTP and gRPC, and it works by default in the request path. It breaks at four boundaries, and each one is where traces go to die — the trace ends at the producer, the downstream work becomes an orphan root, and "how long did the whole order take" becomes unanswerable:

- **A queue or topic.** Inject the context into message headers on publish and extract it on consume. Where a message is processed much later or in a batch, use a span *link* from the consumer's root span to the producer rather than pretending a four-hour delay is one long request.
- **A batch or cron job.** It has no inbound request, so it needs a root span of its own, plus links to whatever it is processing.
- **A thread pool, executor or async runtime.** Context is carried in thread-local or task-local storage. Handing work to another thread without capturing and restoring the context silently detaches it, and the symptom is spans that appear as roots with the right name and no parent.
- **A proxy, gateway or SDK that strips unknown headers.** Check that `traceparent` survives the edge before debugging your own code.

### 7. Cover RED and USE, and instrument the dependency call as well as the handler

RED — rate, errors, duration — for every request-driven endpoint and every queue consumer operation. USE — utilisation, saturation, errors — for every bounded resource the service owns: connection pools, thread pools, worker slots, in-memory queues, disk. These are coverage checklists for finding gaps, not lists of things to alert on; what pages is `alert-design`'s decision, not this one.

The gap that costs the most time is the dependency call. Instrument the **client side** of every outbound call with its own duration histogram and error counter, labelled by dependency and operation. Without it, an incident opens with twenty minutes of arguing about whose latency it is. With it, you can also see the difference between client-observed and server-reported duration, which is connection acquisition, DNS, queueing and retries — and that gap is frequently the actual finding.

Instrument retries and timeouts explicitly too: a counter for retries attempted and one for timeouts, per dependency. A service that is quietly retrying three times looks healthy on success rate and terrible on latency, and nothing else explains it.

### 8. Make errors structured, typed, counted, and separated by kind

Separate **expected failures** from **defects**:

- Expected: a 404 for a resource that does not exist, a validation rejection, an optimistic-lock conflict that the retry resolved, a payment declined by the issuer. These are the system working.
- Defects: unhandled exceptions, a dependency returning 500, a timeout, a serialization failure that escaped.

Count them as separate series, and set span status to error only for the second kind. An error rate that sums both moves when a customer's typo rate moves, and the first time somebody investigates a spike and finds it was validation rejections, the metric stops being trusted — after which it is decoration.

Use a stable, bounded `error.type`: an exception class or an internal error code, never the formatted message with an id in it. The message belongs in `error.message` on the span and in the log body, where free text is priced by the byte instead of by the distinct value.

### 9. Sample so that the interesting traces survive

**Head-based sampling** decides at the root, before anything is known. It is cheap and uniform, and it discards the rare slow trace before that trace exists — there is no recovering it later. It is fine for a service whose traffic is uniform and whose traces are interchangeable, which is rarer than it sounds.

**Tail-based sampling** buffers a complete trace in the collector and decides after seeing it. That is what makes the policy possible: keep every trace with an error, every trace above a latency threshold, every trace for a named tenant during an investigation, and a small percentage of the ordinary fast successes. It costs collector memory and imposes a routing constraint — all spans of a trace must reach the same collector instance, which is what the load-balancing exporter is for.

Two rules worth holding:

- **Errors and slow traces are not sampled away.** They are the population you are keeping traces for. If cost forces a cut, cut the fast successful traces first — to one percent or below; there are millions of them and they are the interchangeable ones.
- **Metrics are not sampled.** That is precisely why the rate lives in a metric. A sampled trace set must never be the source of your error rate, or the rate becomes a function of the sampling policy.

### 10. Set retention per signal, and expect the spend to live here

High resolution recently, downsampled after. A defensible default shape: metrics raw at 10-30 second resolution for around 15 days, rolled up to five-minute resolution for 13 months so year-on-year comparison survives; logs hot and searchable for 7-30 days, then compressed object storage; traces 7 days, because a trace older than the incident is almost never opened.

Retention is where observability spend grows quietly. Query volume is visible and gets discussed; retention silently multiplies every byte you already agreed to keep, and nobody proposes it — it is inherited from a default. Write a retention line per signal into the design, and revisit it against the invoice rather than against the last incident, because after an incident everybody wants everything kept forever.

### 11. A starter set for a new service

Ship with this, then let real questions add to it:

- RED metrics per endpoint and per consumer operation, labelled by route template, method and status class.
- Client-side duration and error metrics per dependency, plus retry and timeout counters.
- USE metrics for every pool and bounded queue the service owns, including queue depth and oldest-message age where it consumes.
- Auto-instrumented traces on the whole request path, with manual spans for the two or three business operations.
- Structured JSON logs at info and above, with `trace_id`, `span_id`, `service.name`, `service.version` and the tenant identifier on every line.
- Resource attributes including the deploy version, and a build-info metric carrying commit and build time.
- One freshness or correctness signal if the service owns data — replication lag, reconciliation result, queue age.

### 12. After an incident, add only what answers the question you could not answer

Write the unanswered question down first, in the postmortem, in the responder's words. Then add the one or two signals that answer it, and record the question beside them. Resist widening: the instinct after an incident is to instrument the entire mechanism that failed, which is exactly how an estate ends up shaped by one bad night. And use the same review to delete — the panels the responders scrolled past and the metrics nobody queried during the incident are evidence, and it is the only time you will get that evidence for free.

## Question to signal to instrument

| Question | Signal | Name and key attributes | Cardinality bound |
| --- | --- | --- | --- |
| Is the service failing for users? | Metric | `http.server.request.duration` histogram, plus a request counter by `http.route`, `http.response.status_code` class | routes x methods x status classes |
| Is it us or a dependency? | Metric plus trace | Client duration histogram and error counter per `server.address` and `db.operation.name`; spans on every outbound call | dependencies x operations |
| Which tenant is affected? | Span and log attribute | `acme.tenant.id` on the root span and in every log line; baggage from the edge | Unbounded, and safe there |
| Which operation is slow, and where did the time go? | Trace | Manual spans for business operations, parented under the auto-instrumented server span | Bounded by span count, not by attribute values |
| Is it getting worse or recovering? | Metric | The same RED metrics over a short window; a rate, not a count | Already bounded |
| Did the deploy do it? | Metric dimension | `service.version` as a resource attribute, and a `build_info` gauge with commit and build time | versions in the retention window |
| Which exact requests failed, with full detail? | Log, reached from a trace | Structured log with `trace_id`, `error.type`, tenant, and the request identifiers | Per byte, not per series |
| Why did this one request take nine seconds? | Trace, kept by tail sampling | Latency policy in the collector keeps every trace above the threshold | Policy-bound |
| Is the queue keeping up? | Metric | Consumer lag and oldest-unprocessed-message age per `messaging.destination.name` | queues x consumer groups |
| Are we retrying our way to a healthy-looking dashboard? | Metric | Retry and timeout counters per dependency | dependencies x outcomes |
| Did the nightly job run and produce the right total? | Metric | Last-success timestamp gauge and a result counter; alert on absence, not on failure | Single-digit series |

## Output format

Report an instrumentation plan in this shape:

```markdown
## Questions
[The four or five, in the responder's words. Any question you cannot answer even after
this work goes here, not in a footnote.]

## Plan
| Question | Signal | Name | Attributes | Cardinality bound | Retention |
[One row per signal. Every row traces back to a question above; a row that does not is
deleted before this ships.]

## Instrumentation
[Auto-instrumentation and what it covers; the manual spans and why each exists;
resource attributes including the deploy version.]

## Correlation
[Trace id in logs, baggage contents, exemplars, and each propagation boundary — queue,
batch job, thread pool — with how context crosses it.]

## Sampling
[Head or tail, the policy, and the explicit statement that errors and slow traces are
kept.]

## Cost
[Estimated series count with the multiplication shown, span volume after sampling, log
volume, and the retention tier per signal.]

## What this still cannot answer
[The honest list. A gap named here is cheaper than a gap discovered at 3am.]
```

## Anti-patterns

**Instrumenting the last incident.** The signals get shaped by one bad night: a counter for the exact failure that happened, a panel for the mechanism that broke. The next incident is a different one, and the estate has grown without becoming more diagnosable. Start from the questions, keep the list short, and let each incident add at most the one or two signals that answer what the responder could not answer.

**User id as a metric label.** It reads as helpful — now the dashboard can break down by customer — and it multiplies against every other label to create a series per customer per route per status per pod, forever. This is the single most common way a team takes down its own observability backend or receives a bill with an extra digit. Identity goes on spans and log lines, and exemplars carry you from the metric to the individual case.

**Logging what a metric should count.** Deriving a rate by counting log lines makes the number depend on log retention, log sampling, and whether somebody reworded the message. It also runs the aggregation over the most expensive store you own, every time anyone asks. Emit the counter; keep the log for the detail you read once you know which case you want.

**Auto-instrumentation only.** You get every HTTP and database call named after its transport and nothing named after the business. The trace shows a `POST /v1/orders` and eleven queries, and cannot say which of them was reserving inventory or settling payment, so latency attribution stops exactly where the domain begins. Auto-instrumentation is the floor, not the finish.

**A trace that stops at the queue.** The producer's trace ends at publish, the consumer starts a fresh root, and the end-to-end question the trace existed to answer is unanswerable — usually discovered mid-incident, which is the worst moment to learn it. Inject context into message headers, extract on consume, and use span links where the delay makes one trace dishonest. The same failure hides in thread pools, async executors and cron jobs.

**Sampling errors away.** A flat head-based rate discards the rare, slow, failing traces at exactly the ratio it discards the boring ones, so the trace you go looking for during an incident is statistically the one that was dropped. Tail-based sampling with keep-all-errors and keep-all-slow costs collector memory and buys the entire value of having traces.

**Dashboards nobody opens instead of questions somebody asks.** Forty panels of everything the exporter offers looks like coverage and functions as camouflage: the responder scrolls, sees no anomaly they can interpret, and goes back to reading logs. Build the panel that answers a written question, put the query for it in the runbook, and delete panels nobody looked at during the last three incidents.

## Reference files

- `references/otel-setup.md` — read when wiring OpenTelemetry up rather than deciding what to measure: SDK initialisation and resource attributes per language, what auto-instrumentation covers and how to enable it, the collector pipeline with batching, redaction, tail sampling and the load-balancing exporter, trace-to-log correlation, and context propagation across queues, batch jobs and thread pools.
- `references/cardinality-and-cost.md` — read when a bill jumped, a backend is struggling, or you are sizing a new metric: the series arithmetic worked through, the queries that find which metric and which target grew, the guard rails that make a bad deploy fail its own scrape, exemplars as the bounded alternative to an identity label, and retention and downsampling tiers per signal.
