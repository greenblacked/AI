# Rollout mechanics

Read this when implementing the mechanism rather than choosing it: how to bucket users
so assignment is stable, how to split traffic on the platforms you are likely to have,
the parts of blue/green that are not the traffic swap, how to run shadow traffic without
side effects, and the automated-analysis shape that Argo Rollouts and Flagger express.

## Contents

- Sticky bucketing
- Splitting traffic
- Blue/green
- Shadow traffic
- Automated analysis and progressive promotion
- Statistics for a canary comparison

## Sticky bucketing

A user must see one behaviour for the whole of a session, and ideally for the whole
rollout. Assignment therefore has to be a pure function of a stable identifier, computed
identically in every service that reads the flag.

```text
bucket = hash(flag_salt + subject_id) mod 10000
enabled = bucket < percentage * 100
```

Details that decide whether this works:

- **The subject id.** Prefer a stable account, tenant or device identifier. A session id
  re-buckets on every login; a request id re-buckets on every request and produces a user
  experience that alternates mid-flow.
- **Salt per flag.** Without a per-flag salt, every flag at 5% selects the same 5% of
  users, who then absorb every risky change in the system. With it, exposure spreads.
- **Same hash everywhere.** Two services computing the bucket with different hash
  functions will disagree about the same user, which shows up as an inconsistent state
  in a single request path. Either share one implementation, or evaluate once at the edge
  and propagate the decision as a header or a context value for that request.
- **Monotonic increase.** Ramping from 5% to 10% should keep the original 5% enabled
  rather than reshuffling the whole population, or your ring 2 evidence describes users
  who are no longer in ring 2. The modulo form above is monotonic; a re-randomised
  assignment per step is not.
- **Overrides before percentages.** Explicit allow-lists for the internal ring and for
  named debugging accounts are checked first, then the percentage.

For a tenant-scoped product, bucket by tenant, not by user. Half a company's employees
seeing a new workflow is worse for that customer than all of them seeing it.

## Splitting traffic

### Kubernetes without a mesh

Two deployments behind one service, split by replica count. Crude but universally
available: 1 canary pod against 19 stable pods is roughly 5%, assuming even load
balancing and similar pod capacity.

```bash
kubectl scale deployment/api-canary --replicas=1
kubectl scale deployment/api-stable --replicas=19
```

The granularity is bounded by replica count, so a fine split needs many pods, and the
assignment is per-connection rather than per-user, which breaks stickiness. Adequate for
an infrastructure-shaped change; not adequate when the change is user-visible.

### Ingress-level weighting

NGINX ingress and most cloud load balancers support a weight annotation or a weighted
target group, which gives percentage control independent of replica count:

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "5"
    # Header or cookie variants pin a cohort rather than sampling per request,
    # which is what makes the split sticky.
    nginx.ingress.kubernetes.io/canary-by-cookie: "canary"
```

Prefer the cookie or header form for user-visible changes and the weight form for
infrastructure changes.

### Service mesh

Istio, Linkerd and equivalents split by subset with explicit weights, and can match on
headers, which is how a ring-1 cohort is expressed:

```yaml
http:
  - match:
      - headers:
          x-cohort:
            exact: ring-1
    route:
      - destination: {host: api, subset: canary}
  - route:
      - destination: {host: api, subset: canary}
        weight: 5
      - destination: {host: api, subset: stable}
        weight: 95
```

A mesh also gives per-subset telemetry for free, which is what makes the per-cohort
guardrails in the main procedure cheap to compute.

### Flags at the edge

The most flexible option is to evaluate the flag once, as early in the request path as
possible, and propagate the decision. It gives per-user stickiness, tenant targeting and
an instant kill, at the cost of the branch existing in the code.

## Blue/green

The traffic swap is the easy part. What decides whether blue/green works:

- **Warm the green side before the swap.** Cold JIT, cold connection pools, cold caches
  and unprimed autoscalers make a healthy deployment look like a latency regression for
  the first few minutes, which is exactly when people are deciding whether to swap back.
  Send synthetic or mirrored traffic until the tail settles.
- **Shared state is not duplicated.** The database, the cache, the queues and any
  external service with rate limits are shared by both sides. Blue/green protects you
  from a bad binary; it does not protect you from a bad write, which is why a schema
  change underneath a blue/green swap still needs expand/contract.
- **Keep blue warm through the bake.** The old side is the rollback plan. Terminating it
  at the swap converts a two-minute rollback into a redeploy, which is the property you
  paid double capacity to avoid.
- **Drain rather than cut.** In-flight requests and keep-alive connections on the blue
  side finish; the load balancer stops sending new ones. Set deregistration delay to
  slightly more than the longest normal request.
- **Sticky sessions and in-memory state** are the usual reason a swap is not clean. If
  either side holds per-user state in memory, the swap logs users out or loses work.

## Shadow traffic

Mirroring production requests to a new implementation and comparing responses without
serving them. It is the only mechanism that establishes correctness rather than absence
of alarm, and the only one whose main risk is entirely self-inflicted.

The rule: **the shadow path must not do anything observable.** Before mirroring a single
request, enumerate and block every side effect.

- Writes: point the shadow at a replica or a copy, or run its persistence layer in a
  read-only or discard mode. A shadow writing to the production database is not a shadow.
- Outbound calls: payments, emails, push notifications, webhooks, SMS, analytics events,
  audit log entries. Each needs a stub or a hard block, not a promise that the code does
  not reach them.
- Idempotency and dedupe keys shared with the real path: a shadow that consumes a
  one-time token breaks the real request.
- Metrics and logs: tag them so they are separable, or the shadow's errors pollute the
  real service's error rate and, worse, its alerting.

Then compare. Response-diffing at the field level, with a tolerance list for fields that
are legitimately non-deterministic (timestamps, ids, ordering of unordered collections),
and a sample of full diffs for a human to read. The diff rate is the interesting number;
the individual diffs are what tell you whether the rate is benign.

Capacity: mirroring doubles load on every downstream the shadow touches. Mirror a
percentage rather than everything, and check the downstream's quota before starting.

## Automated analysis and progressive promotion

Argo Rollouts and Flagger both express the same idea: a rollout is a sequence of weight
steps, each followed by an analysis run against metric queries with success conditions,
where a failed analysis aborts and reverts automatically.

```yaml
# Argo Rollouts, illustrative
strategy:
  canary:
    steps:
      - setWeight: 5
      - pause: {duration: 24h}
      - analysis:
          templates: [{templateName: canary-guardrails}]
      - setWeight: 25
      - pause: {duration: 24h}
      - setWeight: 100
---
# AnalysisTemplate: the gate expressed as a query and a condition
metrics:
  - name: error-rate
    interval: 5m
    failureLimit: 2          # two consecutive failures abort, so one blip does not
    successCondition: result[0] <= 0.005
    provider:
      prometheus:
        query: |
          sum(rate(http_requests_total{job="api",subset="canary",code=~"5.."}[5m]))
          / sum(rate(http_requests_total{job="api",subset="canary"}[5m]))
```

Three things people get wrong in these templates:

- **No control comparison.** The condition above compares the canary against a constant.
  Comparing against the concurrently measured stable subset removes an entire class of
  false aborts caused by things happening to the whole service.
- **`failureLimit` of zero.** One scrape blip aborts the rollout, and after two of those
  the team disables the analysis. Require consecutive failures.
- **No minimum sample.** A ratio computed over eleven requests will breach or pass at
  random. Gate the analysis on a request-count query as well as the ratio.

## Statistics for a canary comparison

You do not need a full experimentation platform, but you do need to avoid the two errors
that make canary metrics misleading.

- **Sample size.** Detecting a 0.5pp change in a 2% error rate takes tens of thousands of
  events per arm. If the canary window will not produce that, either widen the window,
  raise the percentage, or accept honestly that the ring can only catch large breakage.
- **Multiple comparisons.** Watching twenty guardrails at a 95% threshold means roughly
  one of them alarms by chance every run. Rank the guardrails: two or three are abort
  conditions, the rest are investigate-and-hold.

For ratio metrics compare rates over the same window on both arms rather than absolute
counts, because the arms have different traffic volumes by construction. For latency
compare the same percentile on both arms; comparing a canary p99 against a whole-service
p99 mixes the canary into its own control and hides small regressions.
