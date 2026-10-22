---
name: webhook-integration
description: "Receive third-party webhooks reliably, or send your own to customers. Receiving: verify the HMAC over the raw request bytes before parsing, compare in constant time, bound replay with a timestamp tolerance, store the raw event and return 2xx fast, dedupe on the provider's event id, and re-fetch current state, since order is not guaranteed. Sending: stable event ids, signed headers, backoff over days, per-endpoint timeouts, auto-pause, secret rotation, a delivery log and SSRF defence. Use whenever someone says \"our Stripe webhook handler times out\", \"the event was processed twice\", \"the webhook arrived before our write committed\", \"verify the signature\" or \"a customer endpoint is down\". Not for queue consumers behind your own broker (event-driven-reliability), resource contracts (api-design), general signature or SSRF review (security-review), who may call (authorization-design)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Webhook Integration

Done means a webhook is acknowledged quickly, applied exactly once in effect, safe against forgery and replay, and recoverable from stored raw events when your own code was wrong. The usual failure is a handler that parses first, does the work inline, and trusts arrival order: it times out under load, the provider retries, the work runs twice, and an old event overwrites a newer state.

Decide the direction first. Receiving and sending have different failure modes; do the half you were asked for.

## Receiving a webhook

### 1. Verify before you parse

Compute the HMAC over the exact bytes received, using the signing secret and the construction the provider documents (usually timestamp plus a separator plus body). Frameworks that parse JSON and re-serialise change whitespace and key order, which breaks the signature, so capture the raw body before any body parser runs and verify that.

- Compare with a constant-time function (`hmac.compare_digest`, `crypto.timingSafeEqual`), never `==`.
- Reject a timestamp outside a tolerance of about five minutes. The signature alone does not stop an attacker replaying a captured request; the timestamp bound does.
- Where the provider supports two secrets during rotation, accept either until the old one is retired.
- Return 400 or 401 on failure and log the event id only; do not echo the body.

Prefer the provider's own verification helper when it has one, and still feed it the raw bytes.

### 2. Persist, acknowledge, process later

Write the raw event (headers needed for verification, body, received time, provider event id) to durable storage, then return 2xx. Providers time out after a few seconds and treat a slow response as a failure, which triggers the retry that causes the duplicate. Process from the stored row on a worker.

Put a unique constraint on the provider's event id. A second delivery of the same id hits the constraint and is acknowledged without being processed again. The constraint, not an in-memory check, is what holds under two concurrent deliveries.

### 3. Never trust order or freshness

Providers retry, and different event types for one object arrive in any order. Treat the payload as a notification and read the current state:

- Fetch the object from the provider API and apply that, or compare the object's version or `updated` timestamp with what you hold and ignore the stale one.
- A webhook can arrive before your own write has committed (for example, the payment event lands before the order row exists). When the referenced object is not there yet, retry the event with backoff rather than dropping it, and dead-letter it after a bounded time.
- Make the apply step idempotent on the business effect as well as the event id, because the provider can also emit two distinct events for one change.

### 4. Keep a replay path and watch for silence

Because raw events are stored, a bug fix can be followed by re-running the affected range from storage. Build that command before you need it. See `references/receiving-checklist.md` for the replay procedure and the failure table.

Providers disable an endpoint after consecutive failures, and the symptom is that nothing arrives, which no error alert catches. Alert when an event type that normally arrives every hour has not arrived for several hours, and reconcile against the provider's event list on a schedule.

## Sending webhooks to customers

Design these before the first customer subscribes; each is expensive to retrofit.

1. **Envelope.** Deliver at least once. Every event has a stable id that is identical on every retry, a type, a timestamp and a version. Send id, timestamp and signature as headers; the Standard Webhooks layout (`webhook-id`, `webhook-timestamp`, `webhook-signature`) is a good default because customers can use existing verification libraries. Document that consumers must dedupe on the id.
2. **Retry schedule.** Back off with jitter over one to three days, then mark the delivery failed. A customer outage over a weekend should be survivable without them asking for a replay.
3. **Isolation.** Give every endpoint a timeout of 5 to 10 seconds and a concurrency cap. One slow customer otherwise holds the whole worker pool and delays everyone else.
4. **Auto-pause.** When an endpoint has failed continuously for a defined period, pause it, stop spending retries, and notify its owner. Resume by explicit action, then redeliver what was missed.
5. **Rotation.** Support two active signing secrets so a customer can rotate without dropping events; sign with the new one and include both signatures during the overlap.
6. **Delivery log.** Record each attempt with status code, latency and a truncated response snippet, and expose it to the customer with a manual redeliver button. Most support tickets are answered by this log.
7. **SSRF defence.** The customer supplies the URL, so your servers make the request. Require https, resolve the host and block loopback, private, link-local (including the cloud metadata address) and unique-local ranges after resolution, connect to the resolved address to avoid DNS rebinding, and do not follow redirects. Send from an egress path with no access to internal services where you can.

Read `references/sending-checklist.md` for the endpoint state machine and the schedule table.

## Verify

- Send a body with different whitespace than the original and confirm verification fails; send the original and confirm it passes.
- Send the same event id twice concurrently and confirm one effect.
- Send an event with a timestamp ten minutes old and confirm rejection.
- Deliver the "updated" event before the "created" event and confirm the final state is correct.
- Make the handler's downstream slow and confirm the endpoint still answers within a couple of seconds.
- For sending: point an endpoint at a host that resolves to a private address and confirm it is refused; hang an endpoint and confirm other endpoints are unaffected.

## Hand back

The verification construction and tolerance, the dedupe key and where it is enforced, how stale and early events are handled, the replay command, the silence alert, and for senders the envelope, schedule, pause rule, rotation and SSRF policy.

## Anti-patterns

**Verifying the parsed body.** It passes in tests that build the body from the same object and fails in production, which tempts people to disable verification.

**Processing inline.** It works until the first slow database moment, then every retry doubles the load.

**Acknowledging with 200 on any error to stop retries.** It converts a recoverable failure into silent data loss. Return non-2xx for failures you want retried and dead-letter the ones you do not.
