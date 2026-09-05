# Load test design

How to build a test whose result you can act on: the four shapes, the load model, the
data, the dependencies you cannot drive, and the ways a test lies to you.

## Contents

- The four shapes, with scripts
- Open versus closed load models
- Data: volume, cardinality and skew
- The generator is a system too
- Dependencies you cannot drive
- Testing against production, safely
- Reading the result

## The four shapes, with scripts

`k6` is used below because its stages express the shape directly; Locust, Gatling, JMeter
and `vegeta` all do the same work with different syntax. The shape is the part that
matters.

**Average-load.** Does the system behave at expected peak?

```javascript
export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',   // open model: rate does not depend on latency
      rate: 1200, timeUnit: '1s',
      duration: '45m',
      preAllocatedVUs: 500, maxVUs: 3000,
    },
  },
  thresholds: {
    'http_req_failed': ['rate<0.001'],
    'http_req_duration{expected_response:true}': ['p(99)<800'],
  },
};
```

**Stress.** Where does it break, and how?

```javascript
scenarios: {
  ramp: {
    executor: 'ramping-arrival-rate',
    startRate: 200, timeUnit: '1s',
    preAllocatedVUs: 1000, maxVUs: 8000,
    stages: [
      { target: 400,  duration: '10m' },
      { target: 800,  duration: '10m' },
      { target: 1200, duration: '10m' },
      { target: 1800, duration: '10m' },
      { target: 2400, duration: '10m' },   // keep going past the plateau
    ],
  },
}
```

Hold each step long enough for queues, caches, autoscalers and garbage collection to
settle. Five minutes is a floor; ten is better if an autoscaler is in the loop. A ramp
that rises continuously produces a smooth graph and no usable per-step numbers.

**Soak.** Does it survive the duration? 70-80% of peak for 4-24 hours. Watch the
derivatives, not the levels: memory per hour, open file descriptors per hour, connection
count per hour, disk per hour, and p99 drift across the run. A flat p99 over eight hours
is the result you want; anything with a slope is a leak whose slope tells you how long
you have.

**Spike.** Does it survive the arrival shape? Idle to full peak in under ten seconds,
hold for the width of your real spike, back to idle, then do it a second time. The second
spike is the interesting one — it arrives with a cold cache after the autoscaler has
scaled back down, which is the shape of a real repeated event.

## Open versus closed load models

The single most common way a capacity test misleads.

- **Closed model** (a fixed number of virtual users, each looping request-then-think): the
  offered rate is a function of your latency. As the system slows, the generator sends
  less, so the system stabilises at whatever it can do and reports no errors. It cannot
  produce a queue, so it cannot show you saturation. It models a fixed population of users
  waiting for responses — a call centre, an internal tool with 200 known staff.
- **Open model** (a fixed arrival rate, independent of responses): load keeps arriving
  while the system degrades, queues build, and saturation appears as it would in
  production. It models the internet, where nobody's clicking slows down because your
  server is busy.

Use the open model for capacity work — `constant-arrival-rate` and `ramping-arrival-rate`
in k6, `constantUsersPerSec` in Gatling, arrival-rate mode in Locust. State in the report
which model you used, because the same system under the two produces different numbers
and the difference is not small.

Note the retry interaction: real clients retry, which makes the offered load rise exactly
when the system is struggling. If your clients retry, model that in the generator or you
have tested a friendlier world than the one you operate in.

## Data: volume, cardinality and skew

Three properties, and getting the first without the other two is the usual half-measure.

- **Volume** changes query plans. An index seek becomes a scan; a hash join spills to disk;
  a full-table operation that took 40ms takes eleven minutes.
- **Cardinality** changes cache behaviour and index selectivity. Ten tenants fit in every
  cache; ten thousand do not, and the hit rate you measured is meaningless.
- **Skew** is where the timeouts live. Production has a tenant with 400x the median row
  count, a product with a million reviews, and a user with 50,000 saved items. Uniform
  generated data has none of these and will never produce the pathological query.

Preferred sources, in order:

1. A restored production snapshot with sensitive fields masked in place. Best fidelity;
   the masking has to preserve cardinality and length distribution or it destroys the
   thing you restored it for.
2. Generated data fitted to production statistics — row counts per table, distinct counts
   per column, and the top-N frequency distribution, all of which you can pull from the
   database's own statistics tables without exporting any data.
3. Synthetic uniform data. State plainly that plan-dependent results are not to be trusted.

Match the request parameters to the data as well: request ids drawn from the real
distribution, not a sequential walk that is perfectly cache-friendly and perfectly unlike
a user. A test that reads keys 1..N in order measures your readahead.

## The generator is a system too

A load test that plateaus may have found your bottleneck or may have found the
generator's. Distinguish them before reporting anything:

- Watch the generator's own CPU, memory and network. A single box saturates its NIC or its
  ephemeral port range long before most services saturate.
- Check ephemeral ports and connection reuse. Without keep-alive you will exhaust ports at
  a few thousand connections per second and measure `TIME_WAIT` rather than your service.
- Place the generator where the network path resembles the real one. Testing from inside
  the VPC skips the load balancer, TLS termination, and the WAF — often the actual limit.
- Distribute when one node is not enough, and confirm the aggregate rate is what you asked
  for rather than what the slowest node achieved.
- Check the DNS and load-balancer path: a generator that resolves once and pins one IP
  tests one node of your fleet.

The tell is simple — if adding a second generator increases total throughput, the first
one was the bottleneck and every earlier number is wrong.

## Dependencies you cannot drive

For each third party in the path, choose one deliberately and record which:

| Approach | When | What it costs |
| --- | --- | --- |
| Drive the real thing | You have a quota and permission, and the cost per call is small | The truest signal available; coordinate the window with them |
| Sandbox | Their test environment exists and is documented | It is slower and differently limited than production. Useful for correctness, misleading for capacity |
| Local stub with modelled latency | Neither of the above | You measure your system's behaviour under a distribution you chose. Give the stub a realistic latency distribution including its tail, and a failure rate |
| Arithmetic only | The dependency cannot be exercised at all | Legitimate, and labelled "modelled". State per-call latency, fan-out and quota, and what would falsify the result |

A stub that answers in 1ms with no errors turns a test of your system under a real
dependency into a test of your system under a perfect one, which is the version of the
system that was never going to fail.

Enumerate the quotas separately from the test: per-second and per-day limits, burst
allowances, concurrency caps, and the lead time to raise each. Request increases before
the test, not before the event.

## Testing against production, safely

Sometimes the only environment with the real data, the real network path and the real
scale is production. That is a defensible choice with guards, and reckless without them:

- Announce the window, and tell whoever is on-call. A load test that pages people is an
  incident with extra steps.
- Tag synthetic traffic at the edge — a header, a flag on the context — and propagate it,
  so it can be excluded from business metrics, billing and machine learning training data.
- Have an abort: a switch that stops the generator immediately, tested before you start,
  and a named person watching whose only job is to use it.
- Set abort thresholds in advance on real-user metrics, not on the test's own.
- Never generate side effects: no payments, no emails, no webhooks to third parties, no
  writes to shared state that a real user can read. This is the part people get wrong, and
  it is the part that turns a test into an incident with customer impact.
- Prefer a shadowed or mirrored path where the read-only shape allows it.

## Reading the result

Record per step, not per run: offered rate, achieved throughput, p50/p95/p99 latency,
error rate by type, and the utilisation of each candidate resource. The bottleneck is the
resource pinned at the step where achieved throughput stops tracking offered rate.

Three things to check before believing a number:

- **Errors first.** Latency percentiles computed over successful requests only will look
  excellent at the exact moment the system is failing, because the slow requests became
  errors and left the sample.
- **Percentiles do not average.** Do not average p99 across nodes or across intervals; use
  a histogram and compute the percentile over the merged distribution.
- **Look at the shape, not the summary.** A bimodal latency distribution — most requests
  fast, a cluster at exactly the timeout — is a different diagnosis from a uniformly
  degraded one, and both produce the same p99.
