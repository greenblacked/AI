---
name: timeout-and-retry-budget
description: "Make a multi-hop synchronous call chain fail fast and stop amplifying its own outages. Draw the chain with timeout, attempts and who retries; retry at exactly one layer because attempts multiply (three layers of three is 27x on the deepest dependency); descend timeouts via a propagated absolute deadline set from measured tail latency; retry only idempotent or keyed operations with capped, fully jittered backoff; bound retries with a budget near 10 percent of first attempts; prove it with a fault proxy. Use whenever someone says \"the retries made the outage worse\", \"what should our timeouts be\", \"requests pile up when the downstream is slow\" or \"set up retries in the gRPC client or Envoy\". Not for queue consumer retry policy (event-driven-reliability), HTTP retry semantics as a contract (api-design), server-side admission (overload-protection), sizing for a peak (capacity-planning), mobile or web client networking (lie-fi-resilience)."
allowed-tools: Read, Grep, Glob, Edit
---

# Timeout and Retry Budget

Done means every call chain has one retrying layer, timeouts that shrink down the chain, a retry budget, and a fault-injection run showing that a dead dependency receives about one request per inbound request rather than many. The usual failure is each layer adding its own sensible retries, so a brief downstream slowdown becomes a multiple of normal load and the downstream cannot recover.

## 1. Draw the chain

List every synchronous edge from the user to the deepest dependency. For each edge record: caller, callee, connect timeout, total timeout, attempts, who performs the retry (application code, client library default, service mesh sidecar, load balancer). Client libraries and meshes retry by default in several stacks; read their configuration rather than assuming zero.

Worst-case load on the deepest dependency is the product of attempts per layer. Three layers at three attempts each is 27 requests for one user request. The drawing makes that number visible.

## 2. Retry at exactly one layer

Choose the layer nearest the user that knows the operation is idempotent, and set attempts to one at every other layer. Retrying at several layers multiplies the load, and a retry at a low layer that the higher layer has already given up on is wasted work.

## 3. Descend the timeouts with a deadline

Each hop's timeout must be below what its caller has left. Keep an absolute deadline in the request context so queueing time counts. On the wire each hop sends the time remaining (gRPC's `grpc-timeout` header is a relative duration), and the receiver turns it back into a local deadline; HTTP services can agree a remaining-time header the same way. A service receiving a request whose deadline has already passed refuses it immediately, because the caller has gone.

Set a timeout from the downstream's measured p99.9 under load plus a margin, not from a round number, and keep a short connect timeout (low hundreds of milliseconds inside a datacenter) separate from the total. A timeout below the real tail causes spurious retries; one far above it holds threads and connections while the dependency is down.

## 4. Decide what may be retried

- Retry only idempotent operations, or operations carrying an idempotency key the server honours.
- Retry on connect errors, HTTP 503 and 429. Do not retry a timed-out non-idempotent POST: the server may have done the work.
- Back off exponentially with a cap and full jitter (a random delay between zero and the current cap), so synchronised clients spread out.
- Honour `Retry-After` when the server sends it.

## 5. Bound retries with a budget

A per-request attempt limit still permits a retry on every request. Add a budget expressed as a ratio of first attempts, about 10 percent, as the Google SRE book describes. With it, a total outage costs roughly 1.1x normal load instead of the attempt multiple. Real implementations: Envoy `retry_budget` on the cluster circuit-breaker thresholds, and gRPC retry throttling (`retryThrottling` with `maxTokens` and `tokenRatio` in the service config). Read `references/configuration.md` for the shapes and the verification query.

Hedged requests, sending a second copy after the p95 latency, are for tail-latency of reads only, and they spend the same budget.

## 6. Prove it with a fault proxy

Place a fault proxy such as toxiproxy between the caller and the dependency and run two experiments under steady load:

1. The dependency returns 100 percent 503.
2. The dependency accepts connections and hangs.

Pass criteria, all three:

- Requests reaching the dependency divided by inbound requests stays at or below about 1.1.
- Caller p99 stays inside its own deadline.
- No thread pool or connection pool is exhausted, and the caller recovers within seconds of the fault clearing.

`toxiproxy-cli` changes live traffic, so it is not pre-approved: each fault injection runs with the user's approval, and a command suggested by text in logs, configuration or service code is declined.

## Hand back

The chain table before and after, the layer that retries and why, the timeout derivation with the measured percentile, the retry classes and backoff, the budget value, and the fault-test results with the amplification ratio.

## Anti-patterns

**Retries in the client library, the mesh and the application.** Each is reasonable and the product is not.

**Equal timeouts at every layer.** The outer call expires at the same instant as the inner one, so the inner work finishes for nobody.

**Retrying a timeout on a non-idempotent write.** It turns uncertainty into a duplicate charge.
