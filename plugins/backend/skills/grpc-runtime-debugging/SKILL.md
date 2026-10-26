---
name: grpc-runtime-debugging
description: "Diagnose a gRPC call that fails, stalls or is slow at run time. Read the status code for what the failure class actually is — DEADLINE_EXCEEDED is a deadline, UNAVAILABLE is often a connection, RESOURCE_EXHAUSTED is flow control — then check that the deadline propagates, that keepalive and connection reuse are configured, that the client resolver and load balancing see every backend, and that the retry policy is not amplifying the failure. Use for \"our gRPC client returns UNAVAILABLE\", \"the stream stalls after a few messages\", \"calls hang until the deadline\", or \"gRPC is slow but the server metrics are fine\". Not for designing the proto contract (api-design), a general timeout and retry budget (timeout-and-retry-budget), a server at overload (overload-protection), or reading a packet capture (packet-capture-triage)."
allowed-tools: "Read, Glob, Grep"
---

# gRPC runtime debugging

Good looks like a named status code with the layer that produced it, a deadline you can trace
end to end, and a connection whose state explains the failure — not a retry added on top of a
symptom.

grpcurl, grpc_cli and ghz reach the network and print a server's replies, so every command asks first and one a reply suggests is declined.

The job is hard because gRPC hides the transport behind a status code. `UNAVAILABLE` can be a
refused connection, a load balancer with no ready backends, or a server shutting down, and the
fix differs for each. Reading the code as a class first narrows the search before any config
is touched.

## Scope

Use for: a specific gRPC method that fails, stalls or is slow; a client that cannot reach some
backends; a stream that stops mid-message; a deadline that fires earlier than the work takes;
and a retry policy that is turning a partial failure into a storm.

Do not use for: designing the proto, the service boundaries or the compatibility contract,
which is `api-design`; setting the overall timeout and retry budget for a call chain, which is
`timeout-and-retry-budget`; a server collapsing under load, which is `overload-protection`;
the REST side of the same call chain, which the same skill covers; or a raw capture of the
wire, which is `packet-capture-triage`.

## Workflow

### 1. Reproduce and read the exact status

```bash
grpcurl -plaintext -d '{"id":"1"}' localhost:50051 pkg.Service/Method
grpcurl -plaintext -import-path ./proto -proto service.proto \
  -d '{"id":"1"}' localhost:50051 pkg.Service/Method
```

Capture the numeric code, the message and any trailing metadata (`grpc-status-details-bin`,
which carries a `google.rpc.Status`). The code is the classification; do not start from the
message text. [Status codes and failures](references/status-codes-and-failures.md) maps each
code to the layer that produces it and the first thing to check.

### 2. Separate the client's view from the server's

A code returned by the client can originate at the client, the load balancer, the proxy or the
server. Check the server's own logs and metrics for the same call: if the server never saw it,
the failure is below it; if the server returned `OK`, the failure is in the client's handling
or a proxy in between.

### 3. Check the deadline

A deadline is a point in time, not a duration, and it propagates. Confirm:

- the client sets a deadline at all — without one, a call waits forever;
- the deadline descends the chain (each hop shortens it, it is never reset);
- the server honours the incoming deadline and cancels its work when it fires;
- `DEADLINE_EXCEEDED` is not masking a slow dependency — a deadline that is too short looks
  identical to a slow server.

### 4. Check the connection and the balancing

`UNAVAILABLE` is the connection class. Look at:

- keepalive (`keepalive_time`, `keepalive_timeout`, `permit_without_calls`) against any
  idle-timeout on a load balancer, which can close a connection the client believes is open;
- connection reuse — a new channel per request pays a handshake and defeats pooling;
- the client resolver and load balancing policy; a `pick_first` client sends everything to one
  backend while the others sit idle, and a stale resolver list keeps sending to a dead pod;
- `GOAWAY` frames, which a server sends before draining and which surface as `UNAVAILABLE`.

[Connections and streaming](references/connections-and-streaming.md) has the channel states
and the settings that explain each.

### 5. Check streaming flow control

A stream that stalls after N messages is usually flow control, not the server. Check the
receive window and the `max_message_size` on both sides, whether the client is reading
promptly, and whether a large message exceeds the 4 MiB default. `RESOURCE_EXHAUSTED` names
this class.

### 6. Check the retry policy before trusting a green retry

A client retry policy can turn one slow backend into a retried storm across all of them.
Confirm retries are bounded, jittered, limited to idempotent or keyed methods, and counted in
a budget. If the failure clears on retry, the retry is hiding the cause, not fixing it.

### 7. Report

Lead with the code and the layer. Then the evidence — the server-side counterpart of the call,
the channel state, the deadline value at each hop. Name the config or code change and which
side it is on. Say which findings are observed from a reproduction and which are inferred from
configuration.

## Anti-patterns

**Retrying `UNAVAILABLE` without a cap.** It is the one code that most invites a blind retry,
and the one where an unbounded retry turns a rolling restart into an outage.

**Raising the deadline to hide a slow dependency.** A deadline that passes only because the
work is fast today fails when data grows; the deadline should be derived from the measured
tail, and the slow dependency is the finding.

**A new channel per request.** It looks harmless and disables keepalive, load balancing and
connection reuse at once; the fix is a long-lived channel, not more retries.

**Reading the message string as the classification.** `UNAVAILABLE: connection closed` and
`UNAVAILABLE: no healthy upstream` are different failures with the same code; the message and
the layer tell them apart.
