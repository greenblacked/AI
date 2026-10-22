---
name: lie-fi-resilience
description: "Make a mobile or web client survive bad networks, not only no network: reproduce under conditioning at 3G, at 100% loss and on a link that is up but carries no data (captive portal, lie-fi), give every request a deadline, a capped retry budget with jittered backoff and an idempotency key, derive the offline banner from failed requests instead of the reachability flag, and queue writes durably so they survive a killed process. Use when someone says the app works on wifi but hangs on the train, the spinner never ends, hotel wifi breaks the app, a retry submitted an order twice, or asks what timeouts and retries a client should have. Not for the server's endpoint contract (api-design), server-side queue consumers (event-driven-reliability), cache freshness and keys (application-caching), or a slow cold start (mobile-startup-and-jank)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(adb emu network:*), Bash(adb reverse:*)
---

# Lie-Fi Resilience

Done means every network-backed screen, under each of four conditions, ends in one of
three states within a deadline you wrote down — content, cached content marked stale, or
an error with a retry — and no user action is applied twice or lost when the process is
killed mid-flight.

The usual failure is testing two conditions, "online" and "airplane mode", and shipping.
Airplane mode is the easy case: the OS knows there is no route and every call fails in
milliseconds. The hard case is a connection the OS believes is fine — a train between
masts, a captive portal answering every request with a login page, a congested venue
network that accepts the TCP handshake and then delivers nothing. There the reachability
flag says online, the HTTP stack's idle timer keeps resetting on a trickle of bytes or
never starts, and the spinner runs until the user gives up. Nothing crashes, so nothing
reaches crash reporting; it shows up only as one-star reviews saying the app "doesn't
load".

## Scope

Use for: a client that hangs, spins forever or duplicates actions on poor networks;
choosing timeouts, retries and backoff on the client; the offline indicator; an outbox for
writes made while offline; testing a flow under network conditioning.

Do not use for: the server's idempotency-key semantics, status codes and retry-after
contract, which is `api-design` — this skill consumes that contract; server-side queue
workers and dead-letter policy, which is `event-driven-reliability`; what to cache and for
how long, which is `application-caching`; a slow launch, which is `mobile-startup-and-jank`.

## Hard gates

1. No change to timeouts or retries until the flow has been reproduced under the four
   conditions in step 1. A fix tested only in airplane mode has not been tested against
   the bug.
2. No automatic retry of a non-idempotent request without an idempotency key minted once
   per user intent. Without one, a retry after a lost response is a second order.
3. No offline banner driven only by the reachability API. It reports a route, not a
   working internet connection.

## Workflow

### 1. Reproduce under the four conditions

Pick the three flows users care about most — usually first load, the main read, and the
main write — and run each under:

| Condition | What it simulates | What usually breaks |
| --- | --- | --- |
| Slow link (a 3G profile) | High latency, low bandwidth | Deadlines too short for big payloads; UI blocks on the response |
| 100% loss | Route exists, nothing arrives | Connect hangs to the OS default; spinner forever |
| Connected, no data | Handshake succeeds, then silence | Read timeout never fires or is minutes long |
| Captive portal | Every request gets `200` HTML or a redirect to a login page | JSON parse error shown as "something went wrong", or cached as a valid response |

Use the platform conditioner where one exists: on iOS the Network Link Conditioner
(device Developer settings, or the Mac tool in Additional Tools for Xcode) has `3G`,
`100% Loss` and `Very Bad Network` profiles; on the Android emulator use
`adb emu network speed umts` and `adb emu network delay umts`. The connected-but-silent
and captive-portal cases need a proxy or a stub server, because no OS profile produces
them. `references/conditioning-recipes.md` has the setup for each, including physical
Android devices and CI.

*Gate:* a table of flow × condition with what the user saw and after how long. That table
is the bug report and later the regression test.

### 2. Give every request a deadline

Find every call site and the HTTP client configuration behind it, then check what the
stack actually does by default rather than what people assume. The defaults are the bug
more often than the code: `URLSession`'s request timeout is an idle timer that resets
whenever any data arrives, OkHttp has no whole-call timeout unless `callTimeout` is set,
and `fetch` has no timeout at all. `references/client-defaults.md` lists the defaults and
the setting that bounds each stack.

Set two numbers per call class and write them down: a connect or idle timeout short
enough to detect silence, and a total deadline covering connect, TLS, request, response
and every retry. The total deadline is what the user experiences; the idle timeout is
what detects lie-fi. Cancel in-flight requests when the user leaves the screen, so a
response arriving late cannot overwrite newer state.

### 3. Retry within a budget, with jitter, only what is safe

Retry on connection failures, timeouts, `408`, `429`, `502`, `503`, `504`, and `500`
within the budget; do not retry other `4xx`, because the same request will fail the same
way. Honour `Retry-After` when the server sends it. Use capped exponential backoff with full jitter — sleep a random time
between zero and `min(cap, base × 2^attempt)` — so a thousand clients that lost the same
mast do not return in lockstep.

Bound retries twice: by attempts per request, and by the total deadline from step 2. A
retry loop with neither is how a client turns a degraded backend into an outage. If the
app makes many calls, add a process-wide budget as well, for example a token bucket where
retries may spend only a fraction of recent successes, so a dead backend does not get
three times the traffic.

GET, PUT and DELETE are idempotent by HTTP semantics and may be retried. A POST is
retried only with an idempotency key the client generates once when the user acts,
stores with the request, and sends unchanged on every attempt. Confirm the server
honours the key before relying on it; if it does not, that is an `api-design` change to
request, not something the client can paper over.

### 4. Classify responses before trusting them

A captive portal returns `200` with HTML. Check the `Content-Type` and that the body
parses before treating a response as data, and classify a mismatch as a network failure
rather than an application error, so it gets the offline treatment and is never written
to the cache. On Android the system marks a network it has validated with
`NET_CAPABILITY_VALIDATED` and a portal with `NET_CAPABILITY_CAPTIVE_PORTAL`; use those
as hints for the message, not as the gate.

### 5. Drive the offline state from outcomes

Show the offline or degraded state when requests fail — for example after one timeout on
a user-initiated call, or two consecutive failures in the background — and clear it on
the next success. Use reachability (`NWPathMonitor` on iOS, `ConnectivityManager`
callbacks on Android, `navigator.onLine` on the web) only to retry sooner when a route
comes back, never to decide that the network works. When there is cached content, show it
with its age instead of a blank error. Respect Low Data Mode and metered networks
(`NWPath.isConstrained`, `isExpensive`) by deferring prefetch, not user actions.

### 6. Queue writes durably

A write the user made while offline goes into an outbox table in the same local database
as the optimistic state it produced, in the same transaction, with its idempotency key,
payload, attempt count and next-attempt time. A queue held in memory is lost the moment
the OS reclaims the process, which on a phone is routine.

Flush the outbox on launch, on foreground, when a route comes back, and from the
platform's background scheduler — WorkManager with a `NetworkType.CONNECTED` constraint
and exponential backoff criteria on Android, `BGTaskScheduler` or a background
`URLSession` upload on iOS. Preserve order per entity. A permanent rejection (a `4xx`
other than `401`, `408` or `429`) leaves the queue and is shown to the user with what to do; it
is not retried until the end of time. A `401` pauses the queue until the user signs in
again, because dropping the write loses work that was valid when it was made.

*Gate:* kill the process with a write queued, relaunch, and confirm the write arrives
exactly once.

### 7. Re-run the table and keep it

Repeat step 1's table after the change. Every cell must end in content, stale content or
a retryable error within its deadline, with no duplicate writes on the server. Automate
the cheapest cells — a stub server that never responds and one that returns portal HTML
are enough for integration tests in CI — so the next HTTP client upgrade cannot quietly
restore an infinite default.

## Anti-patterns

**Testing only in airplane mode.** It is the one condition the OS reports truthfully.
Every hang users describe lives in the other three.

**A single long timeout as the fix.** Sixty seconds of spinner is still a hang to the
person holding the phone. Separate silence detection from the total deadline.

**Retrying everything three times.** Without idempotency it duplicates writes; without
jitter and a budget it synchronises clients against a struggling backend.

**Caching the portal page.** A `200` is not proof the body is yours. One cached login page
can break a screen until the cache expires.

**An outbox in memory or in preferences.** It survives a test run and not a phone at 4%
battery.

## Output

Hand back: the flow × condition table before and after; each client stack's configured
idle timeout and total deadline; the retry policy (which statuses, attempts, backoff,
budget) and where idempotency keys are minted; how the offline state is derived; the
outbox schema and flush triggers; the tests now in CI; and anything that needs a server
change, named for `api-design`.

## Reference files

- `references/conditioning-recipes.md` — read at step 1: how to produce each condition on
  iOS devices, the Android emulator, physical Android devices, browsers and CI, including
  stub servers for the silent and captive-portal cases.
- `references/client-defaults.md` — read at step 2: timeout defaults and the setting that
  bounds a whole call for URLSession, OkHttp, fetch and common wrappers, plus the backoff
  formula and a retry classification table.
