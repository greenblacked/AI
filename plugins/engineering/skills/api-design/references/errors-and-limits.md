# Errors, pagination, idempotency and limits

Read this when designing the parts of the contract callers hit constantly and read
least: the error taxonomy, the pagination model, retry semantics, and the
non-functional promises.

## Contents

- Status codes and what each tells a client to do
- Naming error codes
- Cursor pagination, end to end
- Idempotency keys
- Rate limits and quotas
- Auth, scopes and size limits

## Status codes and what each tells a client to do

The status code is the only part of the error a proxy, a retry policy or a dashboard can
read. Choose it for what you want the client to do, then let the body explain.

| Status | Means | Client should | Retry? |
| --- | --- | --- | --- |
| 400 | Malformed: bad JSON, wrong type, unparseable | Fix the request | Never |
| 401 | Not authenticated, or the credential expired | Re-authenticate, then retry once | Once, after refresh |
| 403 | Authenticated, not permitted | Stop. Surface to a human | Never |
| 404 | No such resource, or the caller may not know it exists | Stop | Never |
| 405 | Wrong method on a real path | Fix the request | Never |
| 409 | State conflict: already exists, version mismatch | Re-read and decide | Only after re-reading |
| 410 | Existed, permanently gone — a retired endpoint | Migrate | Never |
| 413 | Body too large | Split the request | Never |
| 422 | Well-formed but violates a business rule | Fix the data | Never |
| 429 | Rate limited or over quota | Back off per `Retry-After` | Yes, with backoff |
| 500 | Unexpected fault on your side | Retry with backoff, then escalate | Yes, bounded |
| 502 / 504 | Upstream or timeout | Retry with backoff and jitter | Yes, bounded |
| 503 | Deliberately unavailable: shedding, maintenance | Back off per `Retry-After` | Yes |

Two boundaries carry most of the value. 4xx versus 5xx tells a client whether retrying
can possibly help — misclassifying a caller error as a 500 produces retry storms against
a request that will never succeed. And 400 versus 422 separates "I could not read this"
from "I read it and it is not allowed", which is the difference between a client bug and
a data problem.

Use 409 for optimistic concurrency, with the current version in the body so the caller
can re-read cheaply. Prefer 404 over 403 when confirming existence would leak
information about resources the caller cannot see.

## Naming error codes

- Lowercase, snake or kebab, stable forever. The code is an identifier, not prose.
- Specific enough to branch on: `card_declined`, `insufficient_funds`,
  `idempotency_key_reused`, not `payment_error`.
- Not a restatement of the status: `not_found` adds nothing to a 404;
  `order_not_found` and `customer_not_found` let a client tell the caller which id was
  wrong.
- Namespaced when the surface is large: `orders.already_cancelled`.
- Documented in the schema as an enumeration, with the status code each maps to. A code
  list that lives only in the implementation cannot be handled exhaustively.

State the fallback rule at the same time: clients must treat an unrecognised code as the
generic error for its status class. Without that stated up front, adding a code later is
a breaking change.

## Cursor pagination, end to end

```http
GET /v1/orders?limit=50&cursor=eyJjIjoiMjAyNi0wOC0xNFQxMDoxMjozM1oiLCJpIjoib3JkXzkifQ
```

```json
{
  "data": [ ... ],
  "pagination": {
    "nextCursor": "eyJjIjoiMjAyNi0wOC0xNFQxMDowOToxMVoiLCJpIjoib3JkXzQifQ",
    "hasMore": true
  }
}
```

The rules that make it correct:

- **Order by a total key.** A timestamp alone is not unique; two rows sharing a
  microsecond will be returned twice or skipped. Order by `(createdAt DESC, id DESC)`
  and seek on the pair.
- **Seek, do not skip.** `WHERE (created_at, id) < ($cursorTime, $cursorId) ORDER BY
  created_at DESC, id DESC LIMIT $limit + 1`. Fetching one extra row is how you know
  whether `hasMore` is true without a second count query.
- **The cursor is opaque and self-describing.** Encode the sort key values and, if you
  support multiple orderings, the ordering itself, so a caller cannot page with a cursor
  from a different sort. Document that its contents may change; do not sign a promise
  about its format.
- **`hasMore`, not a total count.** An exact total over a large changing table is an
  expensive query for a number that is stale on arrival. Offer it as an opt-in parameter
  if callers genuinely need it.
- **A maximum enforced server-side.** Default 25 to 50, maximum 100 to 200 for a typical
  payload. Clamp rather than erroring, and document the clamp.
- **Say what a cursor from three days ago does.** Either it still works, or it returns a
  specific error code. Both are acceptable; silence is not.

Offset pagination remains fine over an immutable dataset — an exported report, a
snapshot, a static reference list. Say in the schema which one the endpoint uses, because
a caller cannot tell from the parameter names alone what the consistency guarantee is.

## Idempotency keys

```http
POST /v1/payments
Idempotency-Key: 00000000-0000-4000-8000-000000000001
```

- The client generates the key, one per logical operation, and reuses it across retries
  of that operation only.
- Store the key with the request fingerprint and the full response. On a repeat with a
  matching fingerprint, return the stored response, including its original status code.
- On a repeat with a *different* body, return 422 with `idempotency_key_reused` rather
  than silently serving the old response or creating a second resource. Both silent
  options are worse than an error.
- Handle the concurrent case: a second request arriving while the first is still in
  flight gets 409, not a duplicate. A unique constraint on the key is the simple
  implementation.
- Document the retention window — 24 hours is a common choice — and what happens after
  it, which is that the operation would execute again.
- Scope keys per caller, so two customers cannot collide.

Also state, per operation, the recommended retry policy: exponential backoff with full
jitter, a bounded number of attempts, and a total time budget. A client library that
retries a 500 twenty times without jitter is a load test aimed at a service that is
already unwell.

## Rate limits and quotas

Communicate the limit on every response, not only on rejection, so a well-behaved client
can slow down before it is rejected:

```http
RateLimit-Limit: 1000
RateLimit-Remaining: 42
RateLimit-Reset: 30
```

And on a 429, `Retry-After` with a number of seconds, plus an error code that
distinguishes a short-term rate limit from an exhausted quota — they call for different
client behaviour, one being "wait a moment" and the other "wait until the billing period
resets or buy more".

Design the limits themselves against the consumer tasks from step 1 of the skill. A limit
that makes the normal integration pattern impossible will be worked around with parallel
API keys, which is worse for you than a higher limit would have been. Publish the limits,
set them per principal rather than per IP, and document how a caller requests an
increase.

## Auth, scopes and size limits

- **Authentication mechanism, stated once**, with token lifetimes and the refresh flow.
  Do not accept credentials in query strings; they land in access logs and browser
  history.
- **Scopes granular enough to be useful, coarse enough to be understood.** Read and write
  per resource family is the usual sweet spot. A scope per endpoint is unmanageable; one
  scope for everything means every integration holds full authority.
- **Say what a caller sees without permission**: 403, or 404 where existence itself is
  sensitive. Being inconsistent about this leaks exactly what the 404 was protecting.
- **Maximum request body size**, returned as 413 with the limit in the message, plus the
  maximum array length for batch endpoints. An unbounded batch endpoint is a denial of
  service with a friendly interface.
- **Server-side timeout, published.** The client's timeout should be longer than yours,
  and it cannot be set sensibly against an unpublished number. Say what happens to work
  in flight when the timeout fires — whether the operation may still have committed —
  because that decides whether the client can retry.
