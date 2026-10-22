---
name: rate-limiter-design
description: "Design the limiter itself, not only its headers. Start from the failure being prevented (abuse, cost, fairness, downstream protection), key on the authenticated tenant plus an endpoint cost class, pick the algorithm (a fixed window admits up to 2x across a boundary; use a sliding-window counter or GCRA, a token bucket for legitimate bursts, a concurrency limit for a slow downstream), make check-and-decrement atomic using the store's clock, decide fail-open or closed, and roll out in shadow mode before enforcing. Use whenever someone says \"add rate limiting to our API\", \"one customer is hammering us\", \"per-user limit across 12 pods\" or \"is our Redis rate limiter racy\". Not for the 429 response contract (api-design), capacity-driven shedding regardless of caller (overload-protection), who may call (authorization-design)."
allowed-tools: Read, Grep, Glob, Edit
---

# Rate Limiter Design

Done means the limiter has a stated purpose, a key and limit derived from data, an algorithm matched to the traffic, atomic behaviour across instances with a documented worst-case overshoot, a decided failure mode, and a shadow-mode record before it blocks anyone. The usual failure is a counter per pod with a round-number limit, which is wrong by the number of pods and blocks the wrong people.

## 1. Name the failure being prevented

Pick one primary purpose, because it determines the key, the limit and the algorithm:

| Purpose | Typical key | Typical shape |
| --- | --- | --- |
| Abuse or scraping | IP or account, strict | Low limit, short window |
| Cost control | Tenant, per expensive operation | Weighted, longer window |
| Fairness between tenants | Tenant | Generous limit with burst |
| Protecting a downstream | None or global, plus per tenant | Concurrency limit |

If the real concern is the service collapsing under total load whoever calls, that is overload-protection, not this.

## 2. Choose the key

Key on the authenticated tenant or API key combined with an endpoint cost class (cheap reads, normal writes, expensive exports). Use IP only for unauthenticated traffic, and remember that many users share one NAT address, and that an IPv6 client can rotate through a whole /64, so key on the prefix rather than the single address. A key that is easy to vary (a header the client sets) is not a limit.

## 3. Set the limit from data

Take the measured p99 of legitimate per-customer request rate over a representative period, then add headroom. A limit invented before measurement either blocks real customers or never triggers. Weight expensive calls: an export that costs fifty times a read should consume fifty units.

## 4. Choose the algorithm

- **Fixed window** is simple, but a client can send the full limit at the end of one window and again at the start of the next, up to twice the limit across the boundary.
- **Sliding-window counter** (weighted previous and current window) or **GCRA** (generic cell rate algorithm, a single stored timestamp per key) give smooth behaviour with small state.
- **Token bucket** when bursts are legitimate: capacity is the burst, refill rate is the sustained rate.
- **Concurrency limit** when the thing to protect is a slow downstream: bound simultaneous in-flight requests rather than rate.

## 5. Make it correct across instances

- Check and decrement in one atomic operation. With Redis, that means a Lua script run with `EVAL`/`EVALSHA`, or a single-key GCRA update, never a GET followed by a SET from the application, which two pods interleave.
- Take time from the store (Redis `TIME`), not from application hosts, whose clocks differ.
- Give every key a TTL that covers every window the algorithm reads, so abandoned keys expire without losing state still in use: one window for a fixed window, two for a sliding-window counter, and the computed theoretical-arrival-time expiry for GCRA.
- If a round trip per request is too costly, use local token caches that refill from the shared store periodically. This permits overshoot; write the bound down. The worst case is the leased batch size times the number of pods, plus the tokens spent between syncs; state it as a design number. Limit times pods is the bound only when there is no shared store at all.

Read `references/redis-patterns.md` for a GCRA script outline and the checks for racy implementations.

## 6. Decide the failure mode

The limiter store will be slow or down at some point. Decide per endpoint: fail open (admit) for ordinary reads where blocking is worse than overshoot, fail closed (reject) where the limit protects something costly or sensitive. Give the store call its own timeout of a few milliseconds so the limiter cannot become the slow dependency, and alert on limiter errors.

## 7. Roll out in shadow mode

Run the limiter in shadow mode first: compute the decision, log would-have-limited per tenant, and admit anyway. After about a week look at the top offenders, contact them, and adjust limits. Then enforce with HTTP 429 and `Retry-After`. The header and body contract belong to api-design.

Keep billing quotas separate from rate limits: a quota is a business entitlement that must be exact and auditable; a rate limit is protective and may be approximate.

## 8. Test

- A boundary-burst test: send the limit at the end of a window and again at the start of the next; admission must not exceed the limit plus the documented overshoot.
- An N-instance concurrent test: run the same key from every instance at once; total admitted must be no more than the limit plus the documented overshoot.
- Store failure: stop the store and confirm the chosen open or closed behaviour within the timeout.

## Hand back

The purpose, key, limit with its data, algorithm and why, the atomic mechanism and clock source, the documented overshoot, fail-open or closed per endpoint, the shadow-mode plan and results, and the three tests.

## Anti-patterns

**An in-memory counter per pod.** With twelve pods the effective limit is twelve times the intended one and varies with load balancing.

**GET then SET in Redis.** The window between them admits more than the limit under concurrency.

**IP-keyed limits for authenticated APIs.** They punish shared offices and are dodged by anyone with more addresses.
