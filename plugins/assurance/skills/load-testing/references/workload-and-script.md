# Workload and script

How to turn production logs into a script whose load looks like production, and how to express
an open arrival-rate model in the common tools.

## Contents

- [Deriving the route mix from logs](#deriving-the-route-mix-from-logs)
- [Sampling parameters](#sampling-parameters)
- [A k6 script with phases and thresholds](#a-k6-script-with-phases-and-thresholds)
- [Open-model settings by tool](#open-model-settings-by-tool)
- [Running it](#running-it)

## Deriving the route mix from logs

Pick the busiest hour of a representative week, or the hour of last year's equivalent event.
For structured JSON access logs (field names vary; adjust them to yours):

```bash
jq -r 'select(.ts >= "2026-10-14T18:00" and .ts < "2026-10-14T19:00")
       | "\(.method) \(.route)"' access.json \
  | sort | uniq -c | sort -rn > route-mix.txt
```

Use the route template the router logs (`/orders/{id}`), not the raw path, or every id becomes
its own route. If the logs carry only raw paths, collapse numeric and id-shaped segments first.

Divide each count by the hour's total for the share, and by 3,600 for the average rate during
that hour. The hour's peak minute is usually well above its average; take the target rate for
the test from the question, and use the logs only for the proportions.

Drop routes under roughly 0.5% of traffic into one bucket unless they are expensive. An
export or report endpoint at 0.1% of requests can still be the one that takes the database
down, so check per-route server time before dropping anything.

## Sampling parameters

Extract the parameters the requests used, not a synthetic range:

```bash
jq -r 'select(.route == "/orders/{id}") | .path_params.id' access.json \
  | shuf -n 50000 > order-ids.txt
```

Do the same for every parameterised route the mix includes (the script below also reads a
`product-ids.txt`). Sampling from the logs keeps the real skew: the hot products, the large tenant, the user with
an enormous basket. Check the sampled ids exist in the test environment's data, or the test
measures the 404 path. Mask or exclude anything personal before the file leaves the log host.

## A k6 script with phases and thresholds

```javascript
import http from 'k6/http';
import { check } from 'k6';
import { SharedArray } from 'k6/data';

const BASE = __ENV.BASE_URL;
const lines = (f) => open(f).split('\n').filter(Boolean);
const orderIds = new SharedArray('order ids', () => lines('./order-ids.txt'));
const productIds = new SharedArray('product ids', () => lines('./product-ids.txt'));

export const options = {
  summaryTrendStats: ['med', 'p(95)', 'p(99)', 'p(99.9)', 'max', 'count'],
  scenarios: {
    warmup: {
      executor: 'constant-arrival-rate', rate: 200, timeUnit: '1s',
      duration: '5m', preAllocatedVUs: 100, maxVUs: 500,
    },
    ramp: {
      executor: 'ramping-arrival-rate', startTime: '5m',
      startRate: 200, timeUnit: '1s', preAllocatedVUs: 300, maxVUs: 2000,
      stages: [
        { target: 600, duration: '1m' },  { target: 600, duration: '4m' },
        { target: 1200, duration: '1m' }, { target: 1200, duration: '4m' },
        { target: 1800, duration: '1m' }, { target: 1800, duration: '4m' },
      ],
    },
    steady: {
      executor: 'constant-arrival-rate', startTime: '20m',
      rate: 1800, timeUnit: '1s', duration: '30m',
      preAllocatedVUs: 600, maxVUs: 3000,
    },
  },
  thresholds: {
    'http_req_duration{scenario:steady}': ['p(99)<400'],
    'http_req_failed{scenario:steady}': ['rate<0.001'],
    'dropped_iterations': ['count<1'],
  },
};

function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

export default function () {
  const r = Math.random();
  if (r < 0.62) {
    const res = http.get(`${BASE}/products/${pick(productIds)}`,
      { tags: { name: 'GET /products/{id}' } });
    check(res, { 'status 200': (x) => x.status === 200 });
  } else if (r < 0.90) {
    http.get(`${BASE}/orders/${pick(orderIds)}`, { tags: { name: 'GET /orders/{id}' } });
  } else {
    http.post(`${BASE}/basket`, JSON.stringify({ sku: pick(productIds), qty: 1 }),
      { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /basket' } });
  }
}
```

What each part is for:

- `summaryTrendStats` drops the default `avg` and `min` from the end-of-test summary, so the
  headline is percentiles.
- The `name` tag groups every URL of one route template, so results are per route rather than
  per id, and the metric series count stays bounded.
- Thresholds filtered with `{scenario:steady}` judge only the hold phase; k6 tags every metric
  with the scenario that produced it.
- The `dropped_iterations` threshold voids the run if the executor could not start iterations
  on schedule.
- The ramp holds each step for four minutes so per-step numbers exist. Lengthen the holds if
  an autoscaler is in the loop.

The mix weights in the `if` chain come from `route-mix.txt`; keep them in one place so the next
person can update them from a fresh log hour.

## Open-model settings by tool

| Tool | Open-model setting | Note |
| --- | --- | --- |
| k6 | `constant-arrival-rate`, `ramping-arrival-rate` executors | The `constant-vus` and `ramping-vus` executors are closed |
| Gatling | `constantUsersPerSec`, `rampUsersPerSec` injection steps | `constantConcurrentUsers` is closed |
| JMeter | Open Model Thread Group (5.5 and later) | The standard Thread Group is closed |
| Vegeta | `vegeta attack -rate=... -duration=...` | Constant rate by design |
| wrk2 | `-R` (required); the built binary is still named `wrk` | Corrects latency for coordinated omission; `--latency` prints the distribution |
| Locust | User-based; `constant_throughput` paces each user | Still closed: a user whose request outlasts the pacing interval falls behind |

## Running it

```bash
k6 run -e BASE_URL=https://perf.internal.example --out json=raw.json script.js
echo "exit: $?"
```

Exit code 99 means a threshold failed. Keep the raw output with the report: the summary is
computed from it, and a percentile question asked later (per minute, per route, excluding one
host) can only be answered from the raw data.
