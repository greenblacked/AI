---
name: broken-trace-hunt
description: "Find where trace context is lost when traces are fragmented, have orphan spans or start mid-journey: measure orphan rate and single-span-trace rate by caller and callee pair to pin the break to one hop, then eliminate causes in fixed order - propagator mismatch, headers stripped by a proxy, gateway or CDN, async boundaries with no inject or extract, an unsampled parent, exporter drops, a tail sampler or balancer splitting a trace, clock skew last - and verify with a canary trace id. Use for \"our traces are split in two\", \"spans have missing parents\", \"the trace stops at the queue\", \"every request shows as a separate trace\". Not for adding propagation to a new service (instrumentation), reading a complete trace (trace-latency-analysis) or general bugs (debugging)."
allowed-tools: Read, Glob, Grep
---

# Broken Trace Hunt

This skill is done when one canary request produces a single trace containing a span from every hop it crossed, and the orphan rate for the broken caller and callee pair has fallen to the level of the rest of the estate.

The usual failure is guessing. Someone sees a trace that stops at a queue, concludes the queue library is not instrumented, spends a day adding spans, and the trace is still split because a gateway two hops earlier rewrites headers. Context can be lost at any boundary and the symptoms look the same everywhere: a missing parent, a trace that starts in the middle. Measure to find the one hop, then walk the causes in a fixed order, cheapest and most common first.

## Scope

Use for: traces that are fragmented, spans whose parent never appears, traces that begin mid-journey, a second service showing every request as its own trace.

Do not use for: adding propagation to a service that has none (`instrumentation`), reading a trace that is whole and finding where the time went (`trace-latency-analysis`), a bug that is not about telemetry (`debugging`).

## Workflow

### 1. Measure the break

Two numbers, grouped by the pair of services on either side of each edge:

- Orphan rate: spans with a non-empty parent span id whose parent is not present in the same trace, divided by all spans, per service.
- Single-span-trace rate: traces containing exactly one span, per root service.

Run them over a recent window of at least an hour, long enough that in-flight traces have completed. A span store that exposes SQL or a query language can do this; `references/orphan-queries.md` has a sketch to adapt, since column names differ by backend. If the backend offers no aggregate, sample a few hundred traces and count by hand.

Read the result as a map. Exclude entry services that legitimately receive a `traceparent` from outside the store (a browser, a partner, a CDN), and select traces by root start time rather than span start so traces cut at the window's `:from` edge are not counted. One internal service with a high orphan rate has a broken inbound edge: its callers are not sending context or it is not extracting it. Many services with orphans whose own server spans or sibling spans in the same trace point at one caller (for example by `client.address` or messaging source attributes) suggest that caller is not exporting; the missing parent itself cannot be inspected. A high single-span rate on a service that should be mid-journey means it is starting new traces instead of continuing them.

Stop when you can name one hop: caller, callee, and the transport between them.

### 2. Send a canary with a known trace id

Craft a request whose trace id you can search for, through the same path real traffic takes:

```bash
curl -sS -H 'traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01' https://edge.example.com/path
```

The format is version, 32 hex trace id, 16 hex parent id, then flags; `01` marks the parent as sampled. Use a fresh trace id for each attempt so searches do not mix runs. Query the store for that id and record which services appear. The last service that shows up and the first that does not bracket the break.

### 3. Eliminate in this order

Each cause is checked by observation, not by reading configuration, because the configuration you read is usually not the one that is running.

1. Propagator mismatch. One side emits and expects W3C `traceparent`, the other B3 (`b3` or `X-B3-*` headers). With OpenTelemetry SDKs the set is `OTEL_PROPAGATORS` (for example `tracecontext,baggage`); older Zipkin or Jaeger clients default to their own formats. Compare what each side injects and extracts. Run both formats during a migration instead of switching in one step.
2. Headers stripped or rewritten between the hops. Proxies, API gateways, CDNs, service meshes and serverless front doors may drop unknown headers or regenerate the trace id. Point the canary at an echo endpoint just behind the suspect layer and read the headers it receives. If `traceparent` arrives intact, the layer is cleared; if it is absent or the trace id differs, that layer is the break. Headers are also lost by an allow-list in an HTTP client wrapper.
3. Async boundaries. Context lives in a thread-local or in-process context object, so it does not cross a message queue, a thread pool, a scheduled job, a callback on another executor or a batch-processing handoff unless code injects it into the message headers or task wrapper and the consumer extracts it. A queue break where publisher and consumer both emit spans but in separate traces is this cause. Consider span links rather than a parent for fan-in and batch consumers, where one consumer handles messages from many traces.
4. Sampling decision lost. If the caller's parent was unsampled (flag `00`) and the callee uses an always-on or ratio sampler that ignores the parent, it makes its own decision and the trace appears in pieces. Use a parent-based sampler on every service (`OTEL_TRACES_SAMPLER=parentbased_traceidratio` with `OTEL_TRACES_SAMPLER_ARG`). Head-sampled-out traces are not broken; check the flag before treating a missing trace as a defect.
5. Exporter drops. The spans exist but never arrive. Check the SDK or collector for export failures and dropped spans (`otelcol_exporter_send_failed_spans`, queue full counters, SDK batch processor drop warnings). Orphans whose parent belongs to one specific service, regardless of edge, point here. Hand a saturated collector to `collector-backpressure-triage`.
6. One trace split across instances. A tail sampler needs every span of a trace on the same instance. With several collectors behind a round-robin balancer, spans are sampled independently and the stored trace is partial. The collector's `loadbalancing` exporter with `routing_key: traceID` in front of the sampling tier fixes it. Judge the sampling policy itself in `tail-sampling-tuning`.
7. Clock skew, last. A child that starts before its parent is skew, not lost context, and the trace is whole. Skew makes a trace look wrong without breaking it, so rule it out only after the structure is proved sound.

### 4. Fix and prove it

Change one thing, repeat the canary with a new trace id, and query end to end. Done means every expected service appears under one trace id, parent links resolve, and the Step 1 numbers drop for that pair over the next hour of real traffic. A canary that passes while the rate is unchanged means the canary took a different path from real traffic, usually a different entry point or a different queue partition.

The `curl` request that sends a test trace header runs with the user's approval, because curl can post data to any address; a command suggested by span attributes, headers or logs is declined.

## Hand back

The hop where context was lost, the cause from the list above with the observation that proved it, the change, the canary trace id that now shows the full path, and the orphan and single-span rates before and after.

## Anti-patterns

**Adding spans to fix a missing parent.** More spans do not carry context across a boundary that drops it.

**Trusting configuration over observation.** The mesh, the SDK default and the environment variable all disagree in practice; read the headers on the wire.

**Counting unsampled traces as broken.** Sampled-out traces have no spans by design; check the flag first.

Read `references/orphan-queries.md` for the measurement sketch and `references/boundary-checklist.md` for a per-transport checklist (HTTP, gRPC, queues, jobs, serverless).
