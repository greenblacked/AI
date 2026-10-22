# Configuration and self-metrics

## Two-tier example (partial)

This is an excerpt, not a complete configuration: the `otlp` receiver, the `prometheusremotewrite` and `otlp` exporters, and the agent tier's `memory_limiter` and `batch` processors are not defined here and must be added before the collector will start.

Agent or gateway tier. The `spanmetrics` connector sees all spans, so RED metrics are independent of sampling.

```yaml
connectors:
  spanmetrics: {}

exporters:
  loadbalancing:
    routing_key: traceID
    protocol:
      otlp:
        tls:
          insecure: false
    resolver:
      k8s:
        service: otel-sampler.observability

service:
  pipelines:
    traces/in:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loadbalancing, spanmetrics]
    metrics/spanmetrics:
      receivers: [spanmetrics]
      exporters: [prometheusremotewrite]
```

Sampler tier:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 80
    spike_limit_percentage: 20
  tail_sampling:
    decision_wait: 40s
    num_traces: 100000
    expected_new_traces_per_sec: 2000
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 300 }
      - name: named-tenants
        type: string_attribute
        string_attribute: { key: tenant.id, values: [tenant-a, tenant-b] }
      - name: baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 1 }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [otlp]
```

Check field names against the processor README of the collector-contrib version you run; the policy schema has changed between releases.

## Self-metrics

| Metric | Reads as |
| --- | --- |
| `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early` | Traces evicted before a decision. Non-zero means `num_traces` or memory is too small |
| `otelcol_processor_tail_sampling_sampling_decision_latency` | Time taken to evaluate policies; a rising value means the policies are expensive |
| `otelcol_processor_tail_sampling_sampling_traces_on_memory` | Traces held now; compare with `num_traces` |
| `otelcol_processor_tail_sampling_new_trace_id_received` | Arrival rate of new traces |
| `otelcol_processor_tail_sampling_count_traces_sampled` | Kept and dropped counts per policy and decision |
| `otelcol_processor_tail_sampling_sampling_late_span_age` | Spans that arrived after the decision; high values mean `decision_wait` is short |

Metric names carry a prefix and suffix that depend on the collector version and the exporter's naming rules; confirm in the collector's own `/metrics` endpoint.

## Symptom to cause

| Symptom | Likely cause |
| --- | --- |
| Slow traces kept but missing their last spans | `decision_wait` below p99 duration; late spans metric non-zero |
| Traces appear as several fragments | Round-robin routing, or the pod set changed during the window |
| Dropped-too-early rises at peak only | `num_traces` below arrival rate times `decision_wait` |
| Collector OOM-killed | Memory limit below traces held times bytes per trace; limiter not first |
| Error traces missing | Status not set on spans; match on the HTTP status attribute as well |
| Rate panel moves after a policy change | RED computed from sampled traces; move it before the sampler |
