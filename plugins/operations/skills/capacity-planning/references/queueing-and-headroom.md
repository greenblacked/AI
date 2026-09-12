# Queueing and headroom

The arithmetic behind the numbers in a capacity plan, so that a headroom figure can be
defended rather than asserted.

## Contents

- Little's Law, and what to size with it
- Utilisation and the tail
- Why real systems are worse than the model
- The Universal Scalability Law
- Turning a ramp into a headroom decision
- What consumes headroom without asking
- Worked example

## Little's Law, and what to size with it

`L = λW` — the average number of items in a system equals the average arrival rate
multiplied by the average time each item spends there. It holds for any stable system
regardless of the arrival distribution or the service discipline, which is what makes it
worth reaching for first.

Concurrency in flight:

```text
λ = 2,000 requests/second
W = 0.100 seconds average latency
L = 2,000 × 0.100 = 200 requests in flight
```

That single number sizes several things at once:

- **Connection pool.** If each in-flight request holds a database connection for 40ms of
  its 100ms, the pool needs `2000 × 0.040 = 80` connections to avoid queueing on
  acquisition. A pool of 20 caps you at 500 rps regardless of CPU.
- **Worker or thread count.** For a blocking runtime, workers must exceed in-flight
  requests or requests queue before they start. For an asynchronous runtime the same
  arithmetic applies to whatever bounded resource the work holds.
- **Queue depth and its deadline.** A queue holding `L` items drains in `L/μ` seconds at
  service rate `μ`. If that exceeds the client's timeout, everything in the queue past
  that point is work you will do and nobody will read. Bound the queue at the depth that
  corresponds to your timeout, and drop by age.
- **Total connections across the fleet.** Replicas multiply pools. Twenty replicas with a
  pool of 30 is 600 connections against a `max_connections` of 200 — the horizontal scale
  itself becomes the outage. Size the per-replica pool from the fleet-wide limit divided
  by maximum replica count, including the extra replicas a rolling deploy creates.

Read it in the other direction too. If you know the pool is 100 connections and a query
takes 25ms, the ceiling is `100/0.025 = 4,000` queries per second, and no amount of CPU
will move it. That is a bottleneck derived on paper in one line, before any test.

## Utilisation and the tail

For an M/M/1 queue — Poisson arrivals, exponential service, one server — the average time
in the system is `W = 1/(μ - λ)`, and the average wait relative to service time grows as
`ρ/(1-ρ)` where `ρ` is utilisation:

| Utilisation | Wait, in service times | Total time vs unloaded |
| --- | --- | --- |
| 50% | 1.0 | 2x |
| 70% | 2.3 | 3.3x |
| 80% | 4.0 | 5x |
| 90% | 9.0 | 10x |
| 95% | 19.0 | 20x |
| 99% | 99.0 | 100x |

Two consequences worth internalising:

- The curve is a hyperbola, not a line. Between 80% and 90% utilisation the wait doubles
  for a 10-point move; between 90% and 95% it doubles again for a 5-point move. There is
  no gradual warning region — the system is fine, then it is not.
- The mean hides it. At 90% utilisation the average request looks tolerable while the tail
  has already gone, and the dashboard most teams watch shows the average.

Multiple servers help substantially: `M/M/c` with several servers sharing one queue
tolerates higher utilisation for the same wait, because a burst can be absorbed by
whichever server is free. That is an argument for a shared queue in front of many workers
rather than per-worker queues, and an argument against sticky routing when it is not
required — random assignment to N servers with individual queues is meaningfully worse
than one queue serving N servers.

## Why real systems are worse than the model

Treat the table as an optimistic bound.

- **Arrivals are burstier than Poisson.** Real traffic clusters — retries, cron jobs, push
  notifications, mobile clients waking on a schedule. Burstiness raises the wait at any
  given mean utilisation.
- **Service times vary more than exponentially.** One slow query class, one large tenant,
  one cold cache miss, and the variance term in the wait grows with the square of the
  coefficient of variation. High variance in service time is as damaging as high
  utilisation, and it is why one pathological endpoint degrades an entire shared pool.
- **Queues are coupled.** Saturating a thread pool backs up the connection pool, which
  backs up the load balancer, which trips client timeouts, which produce retries that
  raise arrivals. The model has one queue; you have six in series.
- **Garbage collection and background work** take the server away periodically, which is a
  service interruption the single-server model does not include.

## The Universal Scalability Law

Amdahl's Law says a serial fraction caps speedup. The Universal Scalability Law adds a
second term, and the second term is the one that surprises people:

```text
C(N) = N / (1 + α(N-1) + βN(N-1))
       α = contention  (the serial fraction: locks, a shared resource)
       β = coherency   (crosstalk: nodes coordinating with each other)
```

With `β = 0` throughput plateaus — you stop gaining but you do not lose. With `β > 0`
throughput **peaks and then falls**: adding nodes makes the system slower. Coherency cost
comes from anything that requires nodes to agree — distributed locks, cache invalidation
chatter, leader election, cross-shard transactions, a shared connection pool being
contended for.

This is why "we added replicas and throughput went down" is a real result rather than a
measurement error, and it is why a scale-out plan should be validated at the target
replica count rather than extrapolated from two nodes. Measure throughput at 2, 4, 8 and
16 replicas; if the increments shrink you have contention, and if throughput falls you
have coherency cost and more nodes is the wrong lever entirely.

## Turning a ramp into a headroom decision

The ramp in the workflow's step 2 gives you a table of utilisation against latency for
your actual system, which beats any model. Convert it:

1. Plot bottleneck utilisation against p99 latency, one point per ramp step.
2. Find the utilisation at which p99 crosses your SLO threshold. Call it `U_slo`.
3. Subtract what will be consumed by things that are not steady-state traffic (below).
4. The remainder is the steady-state target. State it with its reason:
   *"Run at 55%: p99 crosses 800ms at 78%, and an AZ loss consumes 33 points."*

If the curve has no knee inside the range you tested, you have not driven it far enough —
extend the ramp until you find one, because that knee is the number the plan is about.

## What consumes headroom without asking

Budget these before claiming any headroom figure. They compose, and they compose badly.

| Consumer | Typical cost | Note |
| --- | --- | --- |
| Loss of one zone of three | +50% load on the survivors | The classic sizing constraint: three zones means each runs at two-thirds of what it could |
| Rolling deploy | 10-25% of capacity unavailable | Depends on `maxUnavailable` and warm-up time; a slow-starting app costs more |
| Retry amplification | 2-3x on the affected path | With a retry budget. Without one, unbounded |
| Cold cache after deploy or failover | 2-10x backend load, for minutes | The most underestimated item here |
| Background and batch work | Whatever it is, at the hour it runs | Check it does not coincide with the peak; move it if it does |
| Autoscaling lag | The whole spike, if the spike is shorter than the lag | Measure the real end-to-end lag rather than the configured period |

Running at 60% is not conservatism when a zone loss takes you to 90% and a deploy during
recovery takes you past it.

## Worked example

A launch, expecting 8,000 rps peak against a mean of 1,400 — a peak-to-mean ratio of 5.7,
which already says autoscaling alone will not do it.

```text
Measured on the ramp:
  Bottleneck: Postgres connection pool. Saturates at 4,200 rps.
  p99 at 3,000 rps: 210ms.  At 3,800 rps: 480ms.  At 4,200 rps: 1,400ms.
  SLO: p99 < 500ms, so U_slo sits at about 3,800 rps.

Little's Law check:
  At 3,800 rps with 22ms average database time: 3800 × 0.022 = 84 connections needed.
  Current pool: 25 per replica × 6 replicas = 150 against max_connections 200.
  So the fleet-wide limit, not the per-replica pool, is the real ceiling.

Actions:
  1. PgBouncer in transaction mode: decouples replica count from backend connections.
     Lead time 3 days. Raises the ceiling to database CPU rather than connections.
  2. Re-run the ramp afterwards. The bottleneck moves; the plan's central claim changes.
  3. Pre-scale to 14 replicas 45 minutes before the launch window and hold for 3 hours.
     Measured autoscaling lag is 6 minutes; the spike is expected to last 4.
  4. Shed anonymous search above 7,000 rps, serving a cached result. Checkout unaffected.
  5. Quota increase requested from the payments provider: 400 to 1,200 tps, 5 working days.

Modelled, not measured:
  The payments provider's behaviour above 400 tps. Sandbox is rate-limited at 50 tps, so
  the figure comes from their published limit and our fan-out of 1 call per order.
  Falsified by: any observed latency increase from them above 300 tps during the ramp.
```

The last block is the one that makes the plan honest. Everything above it was measured;
that part was arithmetic, and it says so.
