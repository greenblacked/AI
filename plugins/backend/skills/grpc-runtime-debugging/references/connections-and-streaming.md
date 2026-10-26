# Connections and streaming

Read this when the code is `UNAVAILABLE` or `RESOURCE_EXHAUSTED`, or a stream stalls. Both
live in the HTTP/2 transport that gRPC is built on, and both are configured, not guessed.

## The channel is the unit of failure

A gRPC channel is an HTTP/2 connection (or a set of subchannels under a load balancing policy).
Its states matter:

- `IDLE` — created but not connected; the first RPC connects.
- `CONNECTING` — a TCP and TLS handshake is in progress.
- `READY` — connected and able to carry RPCs.
- `TRANSIENT_FAILURE` — the last connection attempt failed; the channel backs off before
  retrying. This is what a client reports as `UNAVAILABLE` while it retries underneath.
- `SHUTDOWN` — the channel is closed; create a new one.

A new channel per request pays `CONNECTING` every time and never reuses a warm connection.
Create one channel per target and reuse it.

## Keepalive versus idle timeouts

Keepalive PINGs keep a connection alive through a NAT or load balancer that would otherwise
close an idle one. The classic mismatch:

- the client sends no keepalive, or `keepalive_time` is longer than the proxy's idle timeout;
- the proxy closes the connection silently;
- the next RPC on that channel fails `UNAVAILABLE: connection closed`.

Set `keepalive_time` below the shortest idle timeout on the path, and `keepalive_timeout` short
enough to detect a dead peer. `permit_without_calls` allows keepalive on a channel with no
active RPCs. Do not set the time so low that the server treats it as a PING flood and sends
`GOAWAY` with `ENHANCE_YOUR_CALM`.

## Load balancing and the resolver

- `pick_first` sends every RPC to the first backend that answers; a second backend sits idle
  and a draining first backend takes all the failures. `round_robin` spreads them.
- The resolver is where the client learns the backend list: DNS, a static list, or the
  `xds`/gRPC-LB control plane. A client resolving a Kubernetes Service ClusterIP gets one
  address and balances nothing; resolving headless pods (or using a service mesh / xDS) is
  what gives it the real set.
- `max_connection_age` and `max_connection_age_grace` on the server force clients to
  reconnect periodically so a long-lived connection picks up new backends; without them a
  client can hold one backend for hours.

## Streaming and flow control

HTTP/2 flow control is a window measured in bytes, per stream and per connection. Symptoms and
causes:

- **A stream stalls after N messages.** The receiver is not reading, so its window fills and
  the sender blocks. Check that the client consumes the stream rather than buffering it.
- **`RESOURCE_EXHAUSTED` on a large message.** The default `max_message_size` is 4 MiB on both
  sides. A message above it fails; raise the limit deliberately or split the message.
- **Backpressure looks like a hang.** Server-side streaming with a slow consumer is expected
  backpressure, not a bug; the fix is a faster consumer or a bounded buffer with a drop policy.
- **`ENHANCE_YOUR_CALM`** in a `GOAWAY` means the peer thinks you are misbehaving — usually a
  keepalive or PING rate that is too aggressive.

## Retries and hedging

Retries are configured in the service config (per method) or the mesh, and both default to
off. When they are on:

- retry only idempotent methods, or ones with an idempotency key;
- cap attempts and add jitter;
- hedge only for latency-sensitive, idempotent calls, and understand a hedge doubles the load;
- watch the retry ratio: a healthy system retries a small fraction of calls, and a rising ratio
  is the signal that a backend is failing, not that the retries are working.

## What this cannot prove

Channel state and configuration explain why a call failed; they do not prove which backend was
slow. That needs the server-side span or a capture. Say which of the two you had.
