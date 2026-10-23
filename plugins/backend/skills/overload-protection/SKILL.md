---
name: overload-protection
description: "Keep a service producing useful work at twice its capacity instead of collapsing. Find the first resource to saturate, cap in-flight work at the entrance with Little's law (throughput times latency, not a default pool of 200 threads), bound queues by waiting time and drop requests older than the caller's deadline, reject fast with 503 and Retry-After, shed by priority class, and plan for metastable failure where backlog keeps the system down. Proven by an open-loop step test at 1x, 1.5x, 2x and 5x. Use whenever someone says \"latency spikes and never recovers after the burst\", \"the queue grows and everything times out\", \"add load shedding\" or \"falls over when traffic doubles\". Not for sizing for a peak (capacity-planning), caller-side behaviour (timeout-and-retry-budget), consumer backpressure (event-driven-reliability), per-caller quotas (rate-limiter-design)."
allowed-tools: Read, Grep, Glob, Edit
---

# Overload Protection

Done means that at twice its capacity the service still completes about as much useful work as at its peak, rejects the rest quickly, and returns to normal soon after the load drops. The usual failure is accepting everything: queues grow, every request waits past its caller's timeout, and the service spends all its capacity on answers nobody is waiting for, which is why it does not recover after the burst.

## 1. Find what saturates first

Under rising load identify the first resource to hit its limit: CPU, a database connection pool, a thread pool, memory, a downstream's rate. Everything past that point queues. Use a ramp test or production graphs for utilisation, queue depth and latency by component. The protection goes in front of that resource; protecting a later stage leaves the saturated one unguarded.

## 2. Cap in-flight work at the entrance

Set the concurrency limit from Little's law: in-flight = throughput x latency. If the service sustains 500 requests per second at 40 ms, a limit near 20 in flight keeps it busy; more only adds waiting. A default of 200 threads is a number about the runtime, not the resource.

When the right limit moves with a downstream's health or with request mix, use an adaptive limiter instead of a fixed one: the Envoy adaptive concurrency filter, the Netflix concurrency-limits library, or an AIMD loop (increase slowly while latency is flat, cut multiplicatively when it rises).

## 3. Bound queues by time, not length

A queue's length says nothing about how long a request has waited. Bound it by waiting time:

- Drop any request that has waited past the caller's deadline. The client has given up, so serving it is wasted goodput.
- Under sustained overload serve newest first (LIFO): old requests are the most likely to have timed out, and the fresh ones can still succeed.
- Or use a CoDel-style target on queue sojourn time, dropping when the minimum wait stays above target for an interval.

## 4. Reject fast and cheaply

Reject at the edge before parsing bodies, authenticating against a database or doing any real work: HTTP 503 with `Retry-After`, or 429 where the cause is the caller's own rate. A rejection that costs as much as a success does not protect anything. Make the response small and the code path short.

## 5. Shed by priority

Define classes and shed the lowest first: health checks and control traffic highest, then authentication and flows already in progress (a user halfway through checkout), then interactive reads, then bulk and background work. The class must be assigned at the entrance from something cheap, such as a header, a route or the caller identity.

## 6. Plan for metastable failure

After the trigger ends (a spike, a deploy, a brief dependency outage), retries, cold caches and accumulated backlog can keep the system overloaded indefinitely. The recovery lever is to shed until the backlog drains, not to wait. Write down the manual or automatic action: lower the limit, drop bulk traffic, pause background jobs, warm caches before readmitting. Pair this with caller-side retry budgets, covered by timeout-and-retry-budget; both halves are needed.

## 7. Prove it

Run an open-loop step test (arrival rate fixed regardless of response time, so slow responses do not slow the generator) at 1x, 1.5x, 2x and 5x the measured capacity. Pass criteria:

- Goodput (successful responses within the caller's deadline) at 2x and 5x stays at or above about 90 percent of the 1x peak.
- p99 latency of admitted requests stays bounded, near the 1x figure.
- Rejections are fast, an order of magnitude cheaper than successes.

Then remove the load and time the return to baseline latency and queue depth. Read `references/step-test.md` for the plan, the table to fill in and the failure patterns.

## Hand back

The saturating resource, the limit and its derivation, queue bounds and drop rule, the rejection path, the priority classes, the adaptive choice if any, the recovery action, and the step-test table with recovery time.

## Anti-patterns

**Closed-loop load tests.** A generator that waits for responses slows down when the service does, hiding the overload.

**A bigger queue.** It converts rejections into timeouts, which cost more.

**Shedding after the work.** Rejecting a request after reading the body and querying the database has already spent the capacity you were saving.
