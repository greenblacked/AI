---
paths:
  - "**/otel-collector*.{yml,yaml}"
  - "**/{otel,otelcol}*/**/*.{yml,yaml}"
---

# Collector configuration

Loads when an OpenTelemetry collector configuration is read or edited. The order of the
processors in a pipeline decides what survives overload, so keep it deliberate.

- Put `memory_limiter` first in every pipeline's `processors:` list, so data is refused
  before any other processor allocates for it. A pipeline with processors and no limiter is
  killed by the kernel instead of refusing.
- Set the limiter against the container memory limit, preferably with `limit_percentage` and
  `spike_limit_percentage`, and set `GOMEMLIMIT` near 80 percent of that limit in the manifest.
- Put `batch` last, after enrichment and any sampler, so batches are formed from what is
  exported.
- Give each exporter a `sending_queue` and a bounded `retry_on_failure`; a queue that must
  survive a restart needs `storage` on a volume that outlives the pod.
- Review a whole configuration with the `otel-collector-pipeline-review` skill, and record the
  result in its `collector-review-record.md` template. A collector already dropping data is
  `collector-backpressure-triage`.
