# Wiring up OpenTelemetry

Read this once you know what you want to measure and need the mechanics: SDK setup,
what auto-instrumentation actually covers, the collector pipeline, correlation between
signals, and getting context across the boundaries where it is usually lost.

## Contents

- Resource attributes
- Auto-instrumentation per language
- Manual spans worth writing
- The collector pipeline
- Tail sampling configuration
- Trace and log correlation
- Context propagation across queues, batch jobs and thread pools
- Verifying it works

## Resource attributes

Set these once at startup; they are attached to every span, metric and log the process
emits, and every later group-by depends on them.

| Attribute | Value | Why it matters |
| --- | --- | --- |
| `service.name` | `checkout` | The single most important one. An unset value becomes `unknown_service`, and everything from that process is unattributable. |
| `service.version` | The build's git SHA or semver | Turns "did the deploy do it" into a group-by. |
| `service.namespace` | `payments` | Disambiguates two teams' `api` services. |
| `deployment.environment.name` | `production` | Keeps staging traffic out of production dashboards. |
| `service.instance.id` | Pod name or instance id | Useful on spans; think twice before it becomes a metric label on a high-churn deployment. |

Most of this can come from the environment rather than code, which keeps it correct
without a redeploy:

```bash
OTEL_SERVICE_NAME=checkout
OTEL_RESOURCE_ATTRIBUTES=service.version=${GIT_SHA},deployment.environment.name=production,service.namespace=payments
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability:4317
OTEL_TRACES_SAMPLER=parentbased_always_on   # sample at the collector, not in the app
```

`parentbased_always_on` in the application plus tail sampling in the collector is the
combination that lets the sampling decision be made after the trace is complete. A head
sampler in the application throws the trace away before anything knows whether it was
interesting.

## Auto-instrumentation per language

| Language | How | Covers |
| --- | --- | --- |
| Java | `-javaagent:opentelemetry-javaagent.jar`, no code change | Servlet and framework endpoints, JDBC, HTTP clients, JMS and Kafka, thread-pool context |
| Python | `opentelemetry-instrument python app.py` | WSGI and ASGI frameworks, `requests`, `httpx`, database drivers, Celery |
| Node.js | `--require @opentelemetry/auto-instrumentations-node/register` | HTTP, Express and Fastify, database and gRPC clients |
| .NET | Auto-instrumentation package or `AddOpenTelemetry()` | ASP.NET Core, `HttpClient`, `SqlClient` |
| Go | No runtime agent; add the `otelhttp`, `otelgrpc` and database wrappers explicitly | Whatever you wrap — Go's compile model means this is a code change, so budget for it |

Auto-instrumentation is a floor. It names transport — `GET /v1/orders`, `SELECT`,
`publish` — not meaning.

## Manual spans worth writing

Write a span when all three hold: the operation has a name a product person would
recognise, it can fail on its own, and its duration is worth attributing separately.

```go
ctx, span := tracer.Start(ctx, "checkout.reserve_inventory")
defer span.End()
span.SetAttributes(
    attribute.String("acme.tenant.id", tenantID),   // identity is safe on a span
    attribute.Int("acme.order.sku_count", skuCount),
)
if err := reserve(ctx, order); err != nil {
    span.RecordError(err)
    // Error status marks a defect, not an expected rejection. An out-of-stock
    // response is a business outcome and belongs in an attribute instead.
    span.SetStatus(codes.Error, "reserve failed")
    return err
}
```

Do not wrap every function. Per-span cost is real, and a trace with 400 spans is read by
nobody.

## The collector pipeline

```yaml
receivers:
  otlp:
    protocols:
      grpc: {endpoint: 0.0.0.0:4317}
      http: {endpoint: 0.0.0.0:4318}

processors:
  memory_limiter:            # first in the chain, so overload sheds instead of OOMs
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20
  batch:
    timeout: 5s
    send_batch_size: 8192
  attributes/redact:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: acme.customer.email
        action: delete
  resourcedetection:
    detectors: [env, system, gcp, ec2]

exporters:
  otlp/backend:
    endpoint: ${BACKEND_ENDPOINT}
    retry_on_failure: {enabled: true, max_elapsed_time: 300s}
    sending_queue: {enabled: true, queue_size: 5000}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, attributes/redact, batch]
      exporters: [otlp/backend]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/backend]
```

`memory_limiter` goes first for a reason: without it a backend outage backs pressure up
into a collector that grows until it is killed, and you lose the telemetry for the
incident you are having.

## Tail sampling configuration

Tail sampling needs every span of a trace at the same collector instance. Run two
layers: a load-balancing exporter keyed on trace id, then the sampling collectors.

```yaml
processors:
  tail_sampling:
    decision_wait: 30s        # longer than your slowest normal trace
    num_traces: 100000
    policies:
      - name: keep-errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: keep-slow
        type: latency
        latency: {threshold_ms: 1000}
      - name: keep-tenant-under-investigation
        type: string_attribute
        string_attribute: {key: acme.tenant.id, values: [tenant-example-0001]}
      - name: sample-the-rest
        type: probabilistic
        probabilistic: {sampling_percentage: 1}
```

`decision_wait` shorter than a slow trace truncates exactly the traces the latency
policy exists to keep. Size `num_traces` against traces per second times
`decision_wait`, and watch collector memory after any change to either.

## Trace and log correlation

Use the logging bridge or instrumentation for your language rather than reading the
context by hand; both `trace_id` and `span_id` then appear on every line emitted inside
a span.

```json
{"ts":"2026-09-04T02:14:07Z","level":"error","service.name":"checkout",
 "service.version":"9f2c1ab","trace_id":"4bf92f3577b34da6a3ce929d0e0e4736",
 "span_id":"00f067aa0ba902b7","acme.tenant.id":"tenant-example-0001",
 "error.type":"InventoryTimeout","msg":"reserve failed after 3 attempts"}
```

`error.type` is a bounded field you can count by. The free text stays in `msg`.

## Context propagation across queues, batch jobs and thread pools

**Queues.** Inject on publish, extract on consume:

```python
from opentelemetry.propagate import inject, extract

headers = {}
inject(headers)                      # producer: traceparent into message headers
publish(topic, body, headers=headers)

ctx = extract(message.headers)       # consumer: continue the trace
with tracer.start_as_current_span("orders.process", context=ctx):
    ...
```

Where the message is consumed much later, or a batch consumes thousands at once, start
a fresh root span for the consumer and attach span **links** to the producing contexts.
A link expresses "caused by" without pretending a four-hour delay was one request.

**Batch and cron jobs.** No inbound request, so no context to continue: start a root
span for the run, put the schedule name and run id on it, and link to whatever the run
processes.

**Thread pools and async runtimes.** Context lives in thread-local or task-local
storage. Capture it at submission and restore it in the worker — Java's agent does this
for you, Python's `contextvars` propagate into `asyncio` tasks but not across a raw
thread handoff, and Go requires passing `ctx` explicitly. The symptom of getting it
wrong is correctly named spans that all appear as roots.

## Verifying it works

- Send one request through the edge and confirm a single trace contains a span from
  every service it touched, including the queue consumer.
- Grep a log line from that request and check the `trace_id` matches.
- Confirm the metric series count for the new metrics matches the arithmetic you
  predicted, before it runs for a week.
- Kill the backend for five minutes and confirm the collector queues and recovers rather
  than dying, since that is the state you will be in during a real incident.
