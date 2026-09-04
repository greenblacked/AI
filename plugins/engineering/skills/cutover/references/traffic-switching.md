# Moving traffic between two systems

DNS, load balancers, meshes and CDNs — what each mechanism actually guarantees, where the
caching lives, and how to verify a shift rather than assume it. Load this when designing the
traffic step of a cutover.

## Contents

- [Prefer a shift you can stop halfway](#prefer-a-shift-you-can-stop-halfway)
- [DNS and TTL mechanics](#dns-and-ttl-mechanics)
- [Clients that ignore TTLs](#clients-that-ignore-ttls)
- [Verifying a DNS change](#verifying-a-dns-change)
- [Load balancer and target group shifting](#load-balancer-and-target-group-shifting)
- [Service mesh and gateway splits](#service-mesh-and-gateway-splits)
- [CDN origin switches](#cdn-origin-switches)
- [Connection draining](#connection-draining)
- [Serving from both sides at once](#serving-from-both-sides-at-once)
- [What to watch during a shift](#what-to-watch-during-a-shift)

## Prefer a shift you can stop halfway

Ranked by how reversible each is, best first:

| Mechanism | Granularity | Time to reverse | Notes |
| --- | --- | --- | --- |
| Service mesh / gateway weighting | 1% steps, per route | Seconds | Best available. Config change, no client involvement. |
| Load balancer target group weights | 1% steps | Seconds to a minute | Reverses as fast as it applies. |
| CDN origin or edge rule | Per path or per header | Seconds to minutes | Purge behaviour matters; see below. |
| Application-level dual routing (proxy or feature flag) | Per request, per tenant | Seconds | Needs code, but gives per-tenant control, which nothing else does. |
| Weighted DNS (Route 53, NS1, and similar) | Percentage, coarse in practice | The TTL, plus clients that ignore it | The weight applies at resolution time only. |
| Plain DNS record change | All or nothing | Unbounded | Least reversible. Use only when nothing above is available. |

If the only available mechanism is a plain DNS change, put a proxy in front of the old
hostname first and do the shift there. Adding one hop is usually cheaper than running a
cutover whose reversal time cannot be stated.

## DNS and TTL mechanics

The TTL is a promise about how long a resolver *may* cache an answer. It applies from the
moment the resolver fetched the record, so:

- **Lower TTLs days ahead.** A record with a 24-hour TTL, changed to 60 seconds at T-1h, is
  still being served from caches with the old 24-hour lifetime for most of the next day.
  Lower it, wait at least one full old-TTL period, then treat the low TTL as effective.
- **Lower it on every record in the path**, including CNAME targets and the NS records if
  you are also moving nameservers. The effective TTL of a chain is set by its longest link.
- **Negative caching matters too.** The SOA minimum field caps how long an NXDOMAIN is
  cached. Creating a record that someone already queried and got NXDOMAIN for means waiting
  that out.
- **Raise TTLs back afterwards**, once the bake period ends. A permanent 60-second TTL is a
  permanent load and a permanent dependency on your DNS provider's availability.

## Clients that ignore TTLs

Assume a meaningful share of traffic never re-resolves:

- **JVM.** With a security manager installed, `networkaddress.cache.ttl` defaults to caching
  a successful lookup forever; without one it is typically 30 seconds. Either way it is a
  JVM-wide setting many applications never touch, so long-lived Java clients are the usual
  reason the old system keeps serving hours later.
- **Connection pools and keep-alive.** An HTTP client with an established connection does
  not resolve at all until the connection closes. A pool with a long idle timeout and no max
  lifetime holds the old address indefinitely.
- **Resolvers with their own policy.** Some public and corporate resolvers clamp very short
  TTLs upward, some serve stale answers when the authoritative server is slow, and some
  prefetch popular records on their own schedule.
- **Embedded and mobile clients** may cache at the application layer with no way to flush.
- **Anything with a hardcoded IP** — partner allowlists, firewall rules, a monitoring probe
  someone set up in 2019.

The conclusion is the same in every case: a DNS cutover has no completion event. Plan for
both sides serving correctly, and treat residual old-side traffic as normal.

## Verifying a DNS change

Query the authoritative servers directly; your resolver only tells you what it cached.

```bash
dig +short NS example.com                                   # who is authoritative
dig +norecurse @ns1.example.net api.example.com A           # what is actually published
dig +trace api.example.com A                                # the full delegation path
dig @1.1.1.1 api.example.com A                              # what one public resolver holds
dig @8.8.8.8 api.example.com A +ttlid                       # remaining TTL at that resolver
```

Check from several networks — a public resolver, a corporate one, and a mobile connection —
because they disagree and the disagreement is the point. Then measure the real thing:
request rate arriving at the old system. That is the only figure that says how much traffic
has actually moved, and it is the one that decides when the old side can stop serving.

## Load balancer and target group shifting

The general shape, AWS ALB as the example:

```bash
# 90/10 across two target groups on one listener.
aws elbv2 modify-listener --listener-arn "$LB_LISTENER_ARN" --default-actions '[{
  "Type":"forward",
  "ForwardConfig":{"TargetGroups":[
    {"TargetGroupArn":"'"$TG_OLD"'","Weight":90},
    {"TargetGroupArn":"'"$TG_NEW"'","Weight":10}]}}]'
```

Keep the weight files as artefacts in the repository — `weights-100-0.json`,
`weights-90-10.json`, `weights-0-100.json` — so each step is a one-line command with no
JSON assembled at 03:00.

Before shifting anything:

- Confirm the new target group is **healthy**, not merely registered. A target group with
  zero healthy targets accepts a weight and blackholes that share of traffic.
- Match the health check to a real dependency check, not a static 200. A new stack that
  cannot reach the database still passes `GET /`.
- Check that sticky sessions, if enabled, do not pin users to the old side and mask the
  effect of the shift.
- Watch per-target-group metrics, not aggregate ones. At 10%, a total error rate hides a
  new-side error rate ten times higher.

## Service mesh and gateway splits

Istio, Linkerd, an API gateway or an ingress controller all offer weighted routing. The
advantages over DNS and load balancer weights are per-route granularity and the ability to
mirror.

```yaml
# Istio: 90/10 with the split expressed per route.
spec:
  http:
    - route:
        - destination: {host: api, subset: old}
          weight: 90
        - destination: {host: api, subset: new}
          weight: 10
```

**Traffic mirroring** is the strongest pre-cutover tool available: send a copy of live
production requests to the new stack, discard the responses, and compare. It exercises the
new system with real traffic shapes before any user depends on it. Two cautions — mirrored
requests must not perform writes against shared external systems (payment providers, email,
webhooks), and the mirror doubles load on any dependency both sides share.

## CDN origin switches

Switching the origin behind a CDN is often the least disruptive mechanism available: clients
keep talking to the same edge, only the origin fetch moves.

- Cached objects continue to serve from the edge regardless of the origin change, so the
  visible switch is gradual and follows cache expiry.
- Do not purge everything at the moment of cutover. A full purge sends every request to the
  new origin at once — a thundering herd onto a stack that has never taken full load.
- Check that origin request headers, host rewriting and TLS validation match on the new
  origin. A hostname mismatch on origin TLS shows up as 502s at the edge and nowhere in the
  new stack's own logs.
- Where the CDN supports it, split by path or by a header first — static assets before API
  routes — which gives a low-risk rehearsal with real traffic.

## Connection draining

Cutting connections is not switching traffic; it is an error budget spent for no reason.

- Set deregistration delay / drain timeout to slightly more than the longest normal request,
  not to the default.
- Stop accepting new connections before terminating existing ones. The old side should fail
  its health check first, then keep serving what it already has.
- Long-lived connections — WebSockets, gRPC streams, SSE — do not drain on their own. Either
  set a maximum connection lifetime well before the cutover so clients reconnect naturally,
  or accept that they need an explicit disconnect and that clients must reconnect cleanly.
- Do not shut the old system down at the end of the window. Stop it accepting new work and
  leave it running through the bake period.

## Serving from both sides at once

For any window longer than a few minutes, both systems will serve real traffic
simultaneously. That is the plan, not a failure, and it requires:

- **A shared or replicated data layer**, or a strict rule that only one side accepts writes.
  Two sides accepting writes to separate stores is split brain, and reconciling it after the
  fact is far more expensive than the freeze would have been.
- **Consistent behaviour on both sides** for anything a user can observe across requests:
  session storage, idempotency keys, rate limit counters, feature flag state.
- **Distinguishable telemetry.** Tag metrics, logs and traces with the stack identity from
  the start, or the dashboards during the window show one blended line that hides which side
  is failing.

## What to watch during a shift

Per side, never aggregated:

| Metric | Why |
| --- | --- |
| Request rate per stack | The only real measure of how much traffic has moved |
| Error rate per stack | At 10%, the aggregate hides a 10x error rate on the new side |
| p50 and p99 latency per stack | Cold caches and pools raise p99 first; a raised p50 is a different problem |
| Saturation on the new stack (CPU, connections, pool waits) | The new side is usually sized from estimates, not measurements |
| Dependency error rates from the new side | New egress paths mean new firewall, DNS and TLS failures |
| Old-side request rate after the switch | How much is still pinned, and therefore when the old side can stop |

Hold at each weight long enough to see a full cycle of the slowest thing that matters —
cache fill, a cron tick, a batch job. Shifting again as soon as the graph looks fine at
one minute is how a problem is discovered at 100% rather than at 10%.
