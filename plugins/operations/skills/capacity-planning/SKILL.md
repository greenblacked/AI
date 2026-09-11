---
name: capacity-planning
description: "Work out whether a system will survive an expected load — a launch, a migration, a seasonal peak — and what to change if it will not: build a demand model with a peak-to-mean ratio before opening a load-test tool, drive load up until one resource saturates and name it, size headroom from the latency tail you are willing to accept rather than a rule of thumb, design average-load, stress and soak tests against realistic data volumes, and decide the scaling actions with their lead times and the defined behaviour past capacity. Use this skill whenever someone asks if a system can handle a launch, a Black Friday peak, a migration or a large tenant, wants a load test designed or interpreted, is sizing instances, connection pools, autoscaling or pre-scaling, or asks things like \"will this hold at 10x\", \"how many replicas do we need\", or \"what breaks first\". Not for a live incident, a reliability drill, cutting a cloud bill, or adding telemetry."
allowed-tools: "Read, Write, Edit, Grep, Glob, Bash(k6:*), Bash(kubectl:*), Bash(aws:*), Bash(psql:*), Bash(curl:*), Bash(jq:*)"
---

# Capacity Planning

A capacity plan is good when it names one bottleneck, states the load at which that bottleneck saturates, and says what the system does when the load goes past it anyway.

The work goes wrong before any measurement happens. Someone reaches for a load-test tool first, generates uniform traffic at the average rate, watches it pass, and reports that the system handles the launch — when the launch is a five-minute spike at eight times the mean and the average was never the number that mattered. Someone else scales the tier that was easiest to scale rather than the one that saturates, spends the budget, and moves the failure by nothing. A third runs the test against a seeded database of ten thousand rows and measures the performance of an empty database, which is a real measurement of a system nobody will ever run. And almost everyone plans to run at high utilisation, because it looks efficient on a spreadsheet, and then discovers that queueing does not degrade gracefully: the tail goes from acceptable to unusable across a few percent of extra load, with no warning in the mean. The procedure below is ordered to make each of those hard to do by accident.

## Scope

Use for: sizing a system for a launch, a marketing event, a seasonal peak, a large tenant onboarding or a migration that doubles traffic; finding which resource actually constrains throughput; designing a load, stress or soak test and interpreting what it produced; choosing between vertical and horizontal scaling; setting autoscaling parameters and pre-scaling for a known event; deciding what the system does when demand exceeds capacity.

Do not use for: a live incident or a workload that is failing now, which is `k8s-triage`; a deliberate failure-injection exercise or DR drill, which is `game-day`; reducing a cloud bill on a system that already copes, which is `cost-review`; adding metrics, spans or logs, which is `instrumentation`; the rollout mechanics of a change, which is `release-strategy`.

## Hard gates

1. A demand model exists before a load generator is opened, and every number in it has a stated source.
2. The bottleneck is measured, not assumed. One resource saturates first; find it before proposing any change.
3. The test data resembles production in volume and in cardinality. A test against an empty database measures an empty database.
4. Headroom is chosen from the latency tail you will accept, and stated as a decision rather than as a convention.
5. The plan says what happens beyond capacity. A system with no defined behaviour past its limit fails in whatever way it happens to fail.
6. A number that was modelled rather than measured is labelled as modelled, everywhere it appears.

## Workflow

### 1. Build the demand model first

Capacity is a question about arrivals, and a load generator cannot tell you what the arrivals will be. Write the model down before touching a tool.

- **Population and rate.** How many users or tenants, doing what, how often. Convert to requests per second per endpoint, not one aggregate number — the endpoints have wildly different costs and the expensive one is rarely the popular one.
- **Shape over time.** The daily curve, the weekly one, and any batch or cron that lands on top. Draw it or tabulate it hourly.
- **Peak-to-mean ratio.** This is usually the number that decides the architecture. A system at 1.5x peak-to-mean is sized by its average; one at 20x is sized by an event that lasts four minutes, and everything about the plan changes — autoscaling stops being sufficient, queueing and pre-scaling become the answer.
- **Arrival pattern within the peak.** A thousand requests per second arriving smoothly and a thousand arriving in three bursts are different systems. Launches, push notifications, email sends, market opens and scheduled jobs produce the bursty kind.
- **Work per request.** Fan-out to downstreams, database queries, bytes in and out. A 2x traffic increase is a 2x traffic increase for you and possibly a 20x one for the service you call in a loop.
- **Growth beyond the event.** What the steady state is afterwards, since that is what you will be paying for.

Every number gets a source: measured from production telemetry, taken from last year's event, given by the marketing team, or estimated by you. Label the estimates. A plan where a guess and a measurement look identical is a plan whose review cannot work.

If the event has a precedent — last Black Friday, last launch — start from its measured traffic and apply a growth factor. That is the highest-quality input available and it is usually sitting in a dashboard nobody thought to open.

### 2. Find the bottleneck before scaling anything

Throughput is set by one resource. Everything else has slack, and money spent on the parts with slack buys nothing at all — which is what makes "we scaled it and it did not help" such a common and expensive report.

The method is to drive load up in steps and watch which resource saturates first:

```text
Ramp: 10% → 25% → 50% → 75% → 100% → 125% of modelled peak, holding each step
      long enough for queues and caches to settle (5-10 minutes minimum).
At each step record: throughput achieved, p50/p95/p99 latency, error rate,
      and the utilisation of every candidate resource.
Stop when throughput stops rising with offered load. The resource that is pinned
      at that moment is the bottleneck.
```

Candidate resources, in roughly the order they turn out to be the answer:

| Candidate | What saturation looks like | How to see it |
| --- | --- | --- |
| Connection pool | Latency rises with zero CPU movement; time is spent waiting to acquire | Pool wait-time and in-use metrics; `pg_stat_activity` counts against `max_connections` |
| Downstream service or quota | Your utilisation is flat, their latency or 429 rate is not | Per-dependency latency and error rate, and the provider's quota console |
| Database CPU or IO | Query time rises with concurrency; lock waits appear | Database CPU, IOPS versus provisioned, `pg_stat_statements` total time |
| A lock or single-threaded section | Throughput plateaus while CPU sits well below full on every core | Contention profile; flame graph showing one hot mutex |
| Thread or worker pool | Queue depth grows, workers all busy, CPU has room | Runtime queue-depth metric, worker-busy ratio |
| CPU | Utilisation approaches full, run queue grows | Standard CPU and load metrics, per-core |
| Memory | Garbage-collection time rises, or the process is killed | GC pause time and frequency, RSS trend, `OOMKilled` |
| Network or egress path | Throughput plateaus at a round number; NAT or load-balancer limits | Interface throughput, NAT gateway and load-balancer metrics |

Name the bottleneck explicitly in the plan, with the number: "the Postgres connection pool saturates at 4,200 rps, at which point p99 goes from 180ms to 1.4s". That sentence is the plan's central claim, and everything else follows from it. Once you relieve it, the bottleneck moves to something else — re-measure rather than assuming the new ceiling.

### 3. Size headroom from the tail you will accept

The reason to leave headroom is not caution, it is queueing. Two relationships do most of the work here, both worth understanding rather than memorising.

**Little's Law**: the number of requests in the system equals the arrival rate multiplied by the average time in the system — `L = λW`. Practically: at 2,000 rps with 100ms average latency you have 200 requests in flight, so a pool of 50 connections is already the constraint and no amount of CPU will change that. Use it to size pools, worker counts and queue depths from first principles before testing, then check the test agrees.

**Utilisation and the tail**: as utilisation approaches saturation, waiting time grows without bound. In the simplest model, waiting scales with `ρ/(1-ρ)` — at 50% utilisation a request waits about as long as it takes to serve, at 90% about nine times, at 95% nineteen. That is why the last few percent of a resource is not usable capacity: the mean is still fine while the tail has already left the building, and the mean is what most dashboards show.

Real systems are worse than that model, not better, because arrivals are bursty rather than smooth and because contention adds a term that makes throughput fall after a peak rather than plateau.

So the useful headroom number is a decision about the tail: "we will run steady state at 60% of the bottleneck resource, because at 75% our p99 doubles and our SLO has no room for that". Not "we leave 30% because that is the rule". Derive it from your own ramp data in step 2 — you already have latency at each utilisation step, which is exactly the curve this decision needs. Then account for what consumes headroom without asking: a lost availability zone, a rolling deploy running at reduced capacity, and a retry storm during a partial failure.

`references/queueing-and-headroom.md` has the worked calculations — Little's Law applied to pool sizing, the utilisation-to-latency table, the Universal Scalability Law and what its contention and coherency terms mean for horizontal scaling, and how to convert a ramp result into a headroom decision. Read it when you need to defend a number.

### 4. Design a test that produces a usable answer

Four test types, four different questions. Running one and reporting it as the others is the most common way a load test misleads.

| Test | Question it answers | Shape |
| --- | --- | --- |
| Average-load | Does the system behave at expected load? | Modelled peak, held 30-60 minutes |
| Stress | Where does it break, and how? | Ramp past peak until throughput falls or errors climb; keep going a little past that |
| Soak | Does it survive the duration? | 70-80% of peak, held 4-24 hours |
| Spike | Does it survive the arrival shape? | Idle to peak in seconds, held minutes, back to idle — twice |

The soak test is the only one that finds a leak. Memory growth, file-descriptor and connection leaks, log-volume-driven disk exhaustion, cache growth without eviction, and a slow database bloat all need hours of steady load to become visible, and every short test in the world will miss them. If you run exactly one test before a launch, and the system has been changed recently, the soak is often the one with the highest yield.

What makes the results real:

- **Data volume and cardinality.** Query plans change with table size and with the distribution of values. A query that seeks on an index at 10,000 rows scans at 50 million; a cache that holds every tenant at ten tenants holds 2% of them at a thousand. Restore a production-shaped dataset, or generate one with the same cardinality and skew — including the outlier tenant who has 400 times the median data, because that tenant is where the timeouts live.
- **Think time and session shape.** Real users pause. A closed-loop generator with no think time produces a request rate that depends on your latency, which means the load falls as the system degrades and the test quietly stops testing the thing you wanted. Prefer an open-loop generator with a fixed arrival rate for capacity work, and say which model you used.
- **Cache state.** Run the same test warm and cold, and report both. Warm is your steady state; cold is your recovery after a deploy, a failover or a cache flush, and it is a different and usually much worse system.
- **Traffic mix.** Endpoint proportions from production, not a uniform spread across the API. And real payload sizes: the p99 request body matters more than the median.

`references/load-test-design.md` has the test scripts and shapes, open versus closed models, data generation with realistic skew, distributed generation and how to tell whether the generator itself became the bottleneck, and the checklist for testing safely against production.

### 5. Handle the dependencies you do not control

Your plan is a claim about a system whose parts belong to other people.

- **Rate limits and quotas.** Enumerate them for every third party and every cloud service in the path, with the current limit, the current usage and the lead time to raise it. Quota increases can take days, and finding that out during the event is the standard way a launch fails on something nobody thought was a component.
- **Sandboxes do not behave like production.** A payment provider's test environment is typically slower, differently rate-limited and backed by nothing like the same infrastructure. A load test against a sandbox measures the sandbox.
- **Shared infrastructure moves under you.** A managed database shared with another workload, a NAT gateway shared across a VPC, an internal platform team's ingress — their headroom is part of yours, and it changes without telling you.
- **Say when you modelled rather than measured.** Where a dependency cannot be driven at the required rate, you can still reason: known per-call latency, published quota, fan-out per request, and arithmetic. That is a legitimate input and a weaker one. Label it "modelled", state the assumption, and name what would falsify it. Presenting a model as a measurement is the failure to avoid — it is what makes the eventual surprise land on someone who had no reason to doubt the number.

Where you can, arrange a joint test with the dependency's owner during the window they are staffed for it.

### 6. Choose the scaling actions, with lead times

| Lever | Where it stops working | Lead time |
| --- | --- | --- |
| Vertical: a bigger instance | The largest instance is a hard ceiling; single-threaded sections do not benefit at all; failure domain grows and restarts get slower | Minutes to hours, plus a restart |
| Horizontal: more replicas | State in the process, sticky sessions, a shared bottleneck downstream that more replicas make worse | Minutes, if the image and configuration are ready |
| Caching | Only helps read-heavy skewed workloads; adds stampede and staleness failure modes | Days to build and validate |
| Sharding or partitioning | The correct answer for a database bottleneck and the most expensive; hard to do under time pressure | Weeks |
| Asynchrony: move work off the request path | Only works for work the user does not need synchronously; adds a queue you now have to size | Days |
| Quota increase | Someone else's process | Hours to weeks; ask early |

Two things decide whether horizontal scaling is available at all: state and the shared bottleneck. In-process session state, a local cache holding correctness-critical data, a leader-elected background job, or a singleton connection to a downstream all mean adding replicas changes little or makes things worse — twenty replicas each opening thirty database connections is six hundred connections against a limit of two hundred, and the extra capacity is what causes the outage.

**Autoscaling lag is a first-class problem.** The chain from load arriving to capacity serving is: metric scrape interval, plus controller evaluation period, plus stabilisation window, plus instance or pod start, plus image pull, plus application warm-up, plus load-balancer health checks and connection draining. Two to five minutes is typical and ten is common. Compare that with the width of your spike. If the spike is four minutes, autoscaling arrives after it is over, which is not capacity — it is a bill for capacity you needed earlier.

So for a known event, pre-scale on a schedule and hold, then let autoscaling handle only the variation around it. Scale up on a fast, aggressive rule and down on a slow, conservative one, because being wrong in one direction costs money and in the other costs the event. And confirm that the thing you are scaling can actually start that fast: an application with a ninety-second warm-up has a ninety-second floor no autoscaler can beat.

### 7. Decide what happens past capacity

Every system has a limit. The choice is between failing in a way you designed and failing in whatever way falls out — and the undesigned failure is reliably the worse one, because it arrives as total collapse rather than partial service.

- **Load shedding.** Reject early, cheaply, at the edge, before the request consumes the resource that is scarce. Shed by priority: health checks and paying customers before anonymous browsing; writes before reads, or the reverse, depending on what the business needs. A shed request should cost a fraction of a served one, or shedding becomes the load.
- **Queueing.** Converts a latency problem into a wait, which suits work that need not be synchronous. Bound the queue and set a deadline: an unbounded queue is a memory leak with extra steps, and requests served after the user has left are pure cost. Drop by age, not just by depth.
- **Rate limits.** Per tenant and per endpoint, so one caller's mistake is not everyone's outage. This is also your defence against the retry storm your own clients will generate.
- **Graceful degradation.** Name the features that turn off, in order, and the switch that turns each one off. Recommendations, personalisation, non-essential enrichment, expensive search — the parts a user can lose without losing the transaction. Cross-reference `release-strategy` for how those kill switches are stored and exercised, because a switch that has never been pulled is a hypothesis.
- **A stated worst case.** "Beyond 12,000 rps we shed anonymous read traffic and serve a cached catalogue page; checkout stays available to 18,000 rps." Written down, agreed with the business before the event, and visible to on-call during it.

### 8. Know the failure modes that only appear under load

These do not show up at 10% of peak, and each has a specific fix.

| Failure mode | What it looks like | Fix |
| --- | --- | --- |
| Connection-pool exhaustion | Latency climbs, CPU flat, errors are acquisition timeouts | Size from Little's Law, cap total connections across all replicas, fail fast on acquisition |
| Thread or worker starvation | Queue depth grows, everything slows together, one slow dependency takes the whole service | Bulkhead per dependency, bound the queue, separate pools for slow and fast work |
| Retry storms | A brief downstream blip becomes a sustained multiple of normal load; recovery never happens because the retries prevent it | Exponential backoff with jitter, a retry budget as a fraction of requests, circuit breakers, and no retries at more than one layer of the stack |
| Cache stampede | A popular key expires and thousands of requests hit the origin simultaneously | Jittered TTLs, request coalescing, serve-stale-while-revalidate |
| Cold cache after deploy | The system is fine, then a deploy makes it fall over at unchanged traffic | Warm on start, roll slowly enough for the cache to refill, or keep the cache external to the process |
| Downstream degrading rather than erroring | Your timeouts never fire, threads accumulate, you fail while they report success | Aggressive timeouts, latency-based circuit breaking, and deadlines propagated across calls |
| Autoscaler oscillation | Capacity sawtooths, latency spikes on each scale-down | Longer stabilisation on scale-down, and scale on a metric that leads rather than lags |
| Log and metric amplification | Observability cost and disk grow superlinearly under load, and the logging becomes the bottleneck | Sample under load, keep cardinality bounded — `instrumentation` covers this |

### 9. Price the plan

A capacity plan is a spending decision, so give it a number. Provisioning permanently for a peak you meet twice a year is a legitimate choice and an expensive one; so is the alternative, which is accepting degraded service for those two days. Present both with costs and let the business choose rather than choosing silently.

State the steady-state cost, the event cost, and the cost per unit of demand — per thousand requests, per tenant, per order. Unit cost is what makes the plan comparable to the revenue the event is supposed to produce, and it is the number that keeps a capacity conversation from becoming an argument about instance sizes. Hand the optimisation itself to `cost-review`; what belongs here is the price of the capacity you are asking for and the reliability it buys.

### 10. Instrument the model so you learn whether it was right

Before the event, make sure you can see the model's own variables in production: arrival rate per endpoint, the bottleneck resource's utilisation, queue depth, the saturation-adjacent latency percentile, and the shed or rejected count. Set an alert on the bottleneck crossing the headroom threshold you chose, since that is the earliest honest warning you have.

Afterwards, compare predicted against actual for each: peak rate, peak-to-mean, bottleneck utilisation, latency at peak. That comparison is what makes the next plan better, and it is the step that is always skipped because the event is over and everyone is relieved.

## Output format

```markdown
## Expected load
| Quantity | Value | Source |
[Peak rps per endpoint, peak-to-mean ratio, arrival shape, duration. Measured, given or
estimated — labelled per row.]

## Bottleneck
[The one resource, the load at which it saturates, and the latency at that point.
The measurement that establishes it.]

## Headroom
[The utilisation we will run at, the tail that decision buys, and what consumes headroom:
AZ loss, rolling deploy, retry amplification.]

## Beyond capacity
[Shedding, queueing, rate limits, degradation order. The stated worst case, agreed with
whoever owns the business outcome.]

## Scaling actions
| Action | Lever | Lead time | Owner | Cost |
[Including quota increases requested, and pre-scale schedule for the event.]

## Modelled, not measured
[Every number that came from arithmetic rather than a test, and what would falsify it.]

## Verification
[The monitoring that proves the model was right, and the predicted-versus-actual review
after the event.]
```

## Anti-patterns

**A load test with uniform traffic.** Generating the mean rate smoothly tests a system nobody operates. The failures worth finding — pool exhaustion, autoscaler lag, cache stampede, retry amplification — are all properties of burst and shape, so the test that omits shape passes for exactly the reason it is worthless.

**Testing against an empty database.** Query plans, cache hit rates and lock contention are all functions of data volume and cardinality. A test on a seeded 10,000-row schema is a measurement of a system that does not exist, and it is confidently wrong rather than merely uninformative.

**Scaling the thing that is not the bottleneck.** Money spent, nothing gained, and the plan now carries an implicit claim that the capacity problem is addressed. The next test either is not run or is read charitably, and the ceiling is discovered at the event.

**Planning to run at saturation.** 90% utilisation looks like efficiency on a spreadsheet and is a tail-latency disaster in a queue. Utilisation that high leaves no room for an AZ loss, a rolling deploy or a retry burst, each of which is normal rather than exceptional.

**Autoscaling as a plan for a spike.** The scale-up that lands after the spike is over is not capacity, it is a bill. Measure your actual end-to-end scaling lag, compare it against the width of the spike, and pre-scale when the arithmetic says autoscaling cannot arrive in time.

**No defined behaviour past capacity.** Without shedding, limits and a degradation order, exceeding capacity produces collapse instead of partial service — every request slow, every retry making it worse, and recovery impossible while the load continues. Designed degradation turns that into a smaller, boring outage.

**A number with no stated source.** "We expect 50,000 concurrent users" travels through a plan, a review and a budget without anyone asking where it came from, and the whole plan inherits its confidence. Cite every input, and mark the estimates as estimates so they can be challenged.

**Never running a soak test.** Leaks, unbounded caches, log-driven disk exhaustion and slow degradation are invisible to any test measured in minutes. The system passes every short test and falls over six hours into the event, which is the moment with the least slack and the fewest people.

## Reference files

- `references/load-test-design.md` — read when designing or running the test: the four test shapes with concrete scripts, open versus closed load models, generating data with realistic volume, cardinality and skew, distributed generation and detecting a saturated generator, mocking uncontrollable dependencies, and testing safely against production.
- `references/queueing-and-headroom.md` — read when you need to defend a number: Little's Law applied to pool and worker sizing, the utilisation-to-latency table and where it comes from, the Universal Scalability Law's contention and coherency terms, converting a ramp result into a headroom decision, and the arithmetic for AZ loss, deploy capacity and retry amplification.
