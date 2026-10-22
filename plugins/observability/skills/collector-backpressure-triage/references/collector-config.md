# Collector settings that govern backpressure

Values are starting points to size from your own traffic, not recommendations.

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 1600        # hard limit; keep well under the container limit
    spike_limit_mib: 400   # soft limit = limit_mib - spike_limit_mib
  batch:
    send_batch_size: 8192
    send_batch_max_size: 8192
    timeout: 5s

exporters:
  otlp:
    endpoint: backend.example.com:4317
    compression: zstd      # if the destination accepts it; gzip otherwise
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp]
```

## Notes

- Put `memory_limiter` first and `batch` last among processors.
- `limit_percentage` and `spike_limit_percentage` can replace the MiB values so the limiter follows the container limit.
- The unit of `queue_size` is batches of requests in older versions and may be items or bytes in newer ones through a sizer setting; read the version's documentation before comparing it with a span count.
- A persistent queue uses a `file_storage` extension referenced from `sending_queue.storage`.
- Bounded retry (`max_elapsed_time`) trades data loss for queue health; unbounded retry does the opposite.

## Checklist before declaring it fixed

- Queue size stays below half of capacity at peak.
- No refusals at the receiver or processor over a full peak cycle.
- Enqueue-failed counter flat.
- Memory below the soft limit at peak, with `GOMEMLIMIT` below the container limit.
- The destination's own rejection counters are quiet.
