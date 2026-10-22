# Measurement and claims

## Contents

- Client-side queries
- Composite worked example
- Attributing bad events
- Claim evidence template

## Client-side queries

Assume client metrics named `http_client_request_duration_seconds` (histogram) with `dependency` and `status_code` labels; adapt to your instrumentation. For connection failures with no status, make sure the client records an error class, because those calls have no status code.

Good over valid for one dependency over 30 days, where good means a 2xx or 3xx response within 2 seconds, so connection failures, client timeouts (empty status) and rate-limit rejections never count as good. The denominator below counts every call as valid, which is conservative: self-caused 4xx count against the dependency unless you add a matcher on a label that separates them from vendor 429s, which only works if the client records that distinction.

```promql
sum(increase(http_client_request_duration_seconds_bucket{dependency="payments", le=~"2(\\.0)?", status_code=~"2..|3.."}[30d]))
/
sum(increase(http_client_request_duration_seconds_count{dependency="payments"}[30d]))
```

The `le` matcher accepts both `2` and `2.0` because backends and clients differ in how they spell the bound. The bucket must exist in the histogram; pick a threshold that matches a bucket boundary. Timeouts enforced by the client must be recorded as calls in the count, or the ratio overstates availability. A 30-day `increase` over a high-cardinality histogram is expensive; use a recording rule evaluated every few minutes and sum it.

Retry rate, as retries per first attempt, if the client labels attempts:

```promql
sum(rate(client_request_attempts_total{dependency="payments", attempt!="1"}[1h]))
/
sum(rate(client_request_attempts_total{dependency="payments", attempt="1"}[1h]))
```

Compare with the vendor's published monthly figure over the vendor's window (calendar month, measured at their edge); keep both numbers in the ledger.

## Composite worked example

| Dependency | Hard | Measured |
| --- | --- | --- |
| Identity provider | yes | 99.95 percent |
| Payments | yes | 99.82 percent |
| Search | soft | 99.5 percent |
| Database | yes | 99.97 percent |
| Own service code | yes | 99.93 percent |

Hard factors: 0.9995 x 0.9982 x 0.9997 x 0.9993 = about 0.9967. Allowed failure over 30 days is 0.0033 x 43,200 minutes, about 142 minutes. Search is soft, so it removes a feature, not the request; it appears in the dashboard and degraded-mode budget, not in this product. Promising 99.9 (43 minutes) on these measurements has no support; promising 99.5 does.

With a fallback for payments (a second provider, independent, availability 99.7 percent, exercised last quarter), the payment factor becomes 1 - (1 - 0.9982)(1 - 0.997) = 0.99999, and the product rises to about 0.9985. State the independence assumption next to the number.

Arithmetic check for the headline case: 0.999 to the fifth power is 0.99501.

## Attributing bad events

For each user-facing bad request in the window, take its trace and attribute it to the first failing dependency span on the critical path, or to the service itself if none failed. Count per dependency; divide by total bad requests. A request with two failing dependencies is attributed to the one that failed first and noted. Where traces are sampled, use the SLI's own event counts for totals and the trace sample only for the proportions, and say that sampling was used.

## Claim evidence template

| Field | Content |
| --- | --- |
| Contract and clause | Reference to the SLA section and the version in force |
| Window | Start and end in UTC as the contract defines them |
| Their stated availability | From their report, with the link or attachment |
| Our measured availability | The ratio, the query and the period |
| Bad calls | Count, with a sample of request ids, UTC timestamps, endpoints, statuses or error classes, latencies |
| Exclusions considered | Maintenance windows, customer-caused errors removed, and how |
| Impact | User-facing bad events attributed, in minutes of budget |
| Remedy requested | Credit, root cause report, or both |
| Claim deadline | Date from the contract, and the date filed |

Keep the evidence export and the query alongside the claim so the figures can be reproduced. Have the person who owns the contract review the claim before it is sent.
