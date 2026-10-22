# Configuration shapes

Read this when setting retries or budgets in gRPC, Envoy or an application client, and when checking amplification during the fault test.

## gRPC service config (retry policy and throttling)

```json
{
  "methodConfig": [{
    "name": [{"service": "orders.Orders"}],
    "timeout": "2s",
    "retryPolicy": {
      "maxAttempts": 3,
      "initialBackoff": "0.05s",
      "maxBackoff": "0.5s",
      "backoffMultiplier": 2,
      "retryableStatusCodes": ["UNAVAILABLE"]
    }
  }],
  "retryThrottling": {"maxTokens": 100, "tokenRatio": 0.1}
}
```

Throttling works as a token bucket: each failure removes a token, each success adds `tokenRatio`, and retries are suppressed when tokens fall to half of `maxTokens` or below. A `tokenRatio` of 0.1 approximates a 10 percent budget. gRPC applies full jitter itself. Maximum attempts is capped by the library.

## Envoy

On the upstream cluster, `circuit_breakers.thresholds[].retry_budget` takes `budget_percent` (for example 10) and `min_retry_concurrency`. On the route, `retry_policy` sets `retry_on` (for example `connect-failure,refused-stream,retriable-status-codes` with `retriable_status_codes: [503]` (or `5xx` if retrying any 5xx is acceptable)), `num_retries`, `per_try_timeout` and the retry back-off. Keep `per_try_timeout` times attempts below the route timeout. Check that the application is not also retrying the same call.

## Application clients

Look for the library's retry defaults in its documentation rather than assuming none. Typical settings to find: maximum attempts, retried status codes, whether non-idempotent methods are retried, backoff and whether it is jittered, and connect versus read timeout.

## Measuring amplification

Count requests arriving at the dependency and requests entering the caller during the fault window. The ratio is the figure to compare with 1.1. Use the dependency's own request counter, not the caller's attempt counter, because the caller may under-count retries made in a sidecar.

## Toxiproxy

`toxiproxy-cli create` defines a proxy; `toxiproxy-cli toxic add` attaches a toxic. A `timeout` toxic with timeout 0 holds connections open until the client gives up, which models a hang; to model a 503 storm, make the stub dependency return 503 or use a proxy that rewrites the response. Check `toxiproxy-cli --help` for the exact flags in your version.
