# Collector review checklist and reference settings

Contents: the annotated reference config, the findings table, the load-run script outline.

Values are starting points to size from your own traffic and container limits.

## Reference gateway pipeline

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  file_storage/queue:
    directory: /var/lib/otelcol/queue
    timeout: 10s

processors:
  memory_limiter:
    check_interval: 1s
    limit_percentage: 75        # of the container memory limit
    spike_limit_percentage: 20
  k8sattributes: {}
  tail_sampling:
    decision_wait: 10s
    num_traces: 50000
    policies:
      - name: keep-errors
        type: status_code
        status_code: { status_codes: [ERROR] }
  batch:
    send_batch_size: 8192
    timeout: 5s

exporters:
  otlp:
    endpoint: backend.example.com:4317
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000
      storage: file_storage/queue   # only for data that must survive a restart
    retry_on_failure:
      enabled: true
      max_elapsed_time: 300s

service:
  extensions: [health_check, file_storage/queue]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, k8sattributes, tail_sampling, batch]
      exporters: [otlp]
```

Container side: set `GOMEMLIMIT` to about 80 percent of the memory limit (for a 2GiB limit, `1600MiB`), and keep the limiter percentages below that fraction of the limit.

## Findings table

| Finding | Consequence | Smallest fix |
| --- | --- | --- |
| `batch` before a sampler | Sampler sees batches, not decisions on whole traces; wasted work | Move `batch` to the end |
| No `memory_limiter`, or not first | OOM kill, everything in memory lost | Add it as the first processor |
| `GOMEMLIMIT` unset | Kernel kills before the runtime collects | Set to about 80 percent of the limit |
| Queue on memory only for must-keep data | Restart loses the backlog | `file_storage` queue on a persistent volume |
| Unbounded retry | Queue stays full during an outage | Set `max_elapsed_time` |
| Tail sampler on a multi-replica tier with no `loadbalancing` stage | Partial traces judged on fragments | Add trace-ID-keyed load balancing in a front tier |
| App exports straight to the vendor | Credentials and retries in every service | Point apps at the agent or gateway |
| Full contrib image | Unused components, larger surface | Build with `ocb` |
| Health port in config differs from manifest | Probe fails or probes the wrong thing | Align the two |

## Load-run outline

1. Deploy the candidate config at the production container limit.
2. Point a trace generator at it at expected peak, then at twice peak.
3. Send to a backend you can switch to 429 or to silence.
4. Record peak memory, refused counts, queue size and capacity, restarts.
5. Kill the pod mid-run and check whether the queued data survived, if that was a requirement.
