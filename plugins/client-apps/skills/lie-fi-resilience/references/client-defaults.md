# Client defaults, deadlines and retry rules

What each HTTP stack does when nobody configures it, and the setting that bounds a whole
call. Check the version in use against its documentation before relying on a default;
these are the documented behaviours at the time of writing, and the point of the table is
which knobs exist, not the numbers.

## Contents

- Timeout defaults by stack
- Retry classification
- Backoff and budgets
- Idempotency keys on the client

## Timeout defaults by stack

| Stack | What the default does | What bounds the whole call |
| --- | --- | --- |
| `URLSession` (and wrappers built on it) | `timeoutIntervalForRequest` is 60 seconds of idleness and resets whenever data arrives; `timeoutIntervalForResource` is seven days; `waitsForConnectivity` is off, so a task with no route fails at once | Set `timeoutIntervalForResource` on the configuration, or cancel the task from your own deadline. With `waitsForConnectivity` on, the task waits for a route and the resource timeout bounds that wait |
| OkHttp (and Retrofit on top of it) | Connect, read and write timeouts are 10 seconds each; `callTimeout` is 0, meaning none | Set `callTimeout`. Note that `retryOnConnectionFailure` is on by default and can silently repeat a request after a stale pooled connection, which is one more reason POSTs need idempotency keys |
| Browser `fetch` | No timeout | `signal: AbortSignal.timeout(ms)`; combine with a user-cancel controller through `AbortSignal.any([...])` where supported |
| Axios | `timeout` is 0, meaning none | Set `timeout` and pass a `signal` so navigation can cancel |
| Ktor client | No timeouts unless the `HttpTimeout` plugin is installed | Install it and set `requestTimeoutMillis`, `connectTimeoutMillis` and `socketTimeoutMillis` |
| Dart `http` | No timeout | Wrap the future with `.timeout(...)` and close the client on expiry, or use a client with explicit connect and receive timeouts |
| gRPC | No deadline unless the caller sets one | Set a deadline on every call; the server sees it and can stop work |

Two numbers per call class are enough: an idle or connect timeout that detects silence
(a few seconds on a user-facing read), and a total deadline that covers every retry and is
what the user waits for. Background syncs can have long totals; a tap that shows a spinner
cannot.

## Retry classification

| Outcome | Retry? | Notes |
| --- | --- | --- |
| DNS failure, connect failure, reset, TLS handshake failure | Yes | Counts toward the offline state |
| Idle or total timeout | Yes, if time remains in the total deadline | A timed-out POST may have succeeded; only the idempotency key makes the retry safe |
| `408`, `429`, `502`, `503`, `504` | Yes | Honour `Retry-After` when present, within the deadline |
| `500` | Usually, within the budget | Repeated `500` on one request is a bug, not a network condition |
| Other `4xx` | No | The same request fails the same way; surface it |
| `2xx` with an unexpected content type or unparseable body | Yes, as a network failure | Captive portal or proxy; count it toward the offline state and never cache it |

## Backoff and budgets

Capped exponential backoff with full jitter:

```text
delay(attempt) = random_between(0, min(cap, base * 2 ** attempt))
```

With `base` of a few hundred milliseconds and a `cap` of tens of seconds, clients that all
lost the same mast spread out instead of arriving together. Stop when either the attempt
limit or the total deadline is reached, whichever comes first.

A process-wide retry budget keeps a dead backend from receiving a multiple of its normal
load: allow retries only while they stay under a set fraction of recent requests, using a
token bucket that successes refill and retries drain. gRPC's retry throttling works this
way and is a usable model for any client.

## Idempotency keys on the client

- Mint the key when the user acts (taps Pay, sends the message), not when the request is
  built, so a rebuilt request after a crash carries the same key.
- Store it with the outbox row and send it unchanged on every attempt, usually as an
  `Idempotency-Key` header; the exact header and retention window are the server's
  contract.
- A new user action gets a new key even if the payload is identical. Two identical
  messages sent on purpose are two messages.
