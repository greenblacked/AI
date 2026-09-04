---
name: api-design
description: "Design or review an HTTP or RPC interface that other people will depend on — resources modelled on the consumer's task rather than the storage schema, a machine-readable OpenAPI or protobuf contract verified against the implementation, errors with a machine-readable code, cursor pagination with a stated ordering guarantee, idempotency keys for unsafe operations, an explicit compatibility guarantee, and a deprecation process backed by usage telemetry. Use this skill whenever someone is designing a new endpoint or service interface, reviewing one before it ships, or asking \"is this a breaking change\", \"should this be a PATCH or an action endpoint\", \"how do we version this\", \"offset or cursor pagination\", \"how do we retire v1\", or \"can you review my OpenAPI spec\". Do not use it to scaffold the implementation, to record the decision between two designs, to roll a change out gradually, or to migrate a database schema."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(curl:*), Bash(jq:*), Bash(git:*)
---

# API Design

A good interface is one a competent stranger can integrate against from the schema alone, and one you can still change two years later without breaking them.

An API is a promise, and the cost of a design mistake is paid by everyone who integrated before you noticed. That asymmetry is what makes this hard: the design work is cheap and the correction is not, because the correction has to be coordinated with people you may not be able to contact. Two opposite failure modes dominate, and they are equally common. The first is the interface designed around the current database schema — every table becomes a resource, every column a field, and the API leaks internals that cannot survive the first refactor, so the schema change you wanted to make becomes a breaking API change instead. The second is the interface designed for imagined future consumers — five levels of generality, a filter grammar, an expansion syntax, all of it unused, all of it now permanently supported. The discipline in between is narrow: design from the tasks real callers actually have, then make the compatibility rules explicit before anyone integrates.

## Scope

Use for: designing a new HTTP or RPC interface; reviewing one before it ships or after it has; resource modelling and endpoint naming; error taxonomies and status code mapping; pagination, filtering and sorting; idempotency and retry semantics; deciding whether a change is breaking; choosing a versioning strategy; planning a deprecation.

Do not use for: writing the implementation or scaffolding a service (`code-scaffold`), recording the decision between two competing designs for posterity (`decision-record`), rolling a change out gradually behind a flag (`release-strategy`), or changing the database schema underneath it (`db-migration`).

## Workflow

### 1. Write the consumer's task before writing any endpoint

List the three to five things a caller actually wants to do, in their words: "show the customer their last ten orders with the item names", "cancel an order and refund it", "reconcile yesterday's payouts". Then design the resources that make each one a small number of requests.

The test is mechanical. If a caller must make four requests and join the results client-side to do one obvious thing, the resources are wrong — either the natural aggregate is missing, or you have exported the join table. Equally, if one endpoint serves six unrelated tasks through a mode parameter, it is a remote procedure call wearing a resource costume.

Where the storage model and the task disagree, the task wins. The database is an implementation detail you intend to change; the API is the part you cannot.

### 2. Name and shape the resources

- **Nouns, not verbs.** `/orders`, not `/getOrders`. The method carries the verb.
- **Consistent pluralisation.** Collections plural, members by id under them: `/orders`, `/orders/{orderId}`. Pick one convention and apply it to every resource, including the awkward ones.
- **Nesting one level, rarely two.** `/orders/{orderId}/items` is fine. `/customers/{id}/orders/{id}/items/{id}/refunds` is a URL nobody can build correctly; make `refunds` a top-level resource with an `orderId` filter.
- **Identifiers opaque to the caller.** A caller who parses your ids has coupled to your storage. Say in the schema that ids are opaque strings, and they may become so later.
- **Field names in one case convention**, matching the ecosystem the API lives in, applied everywhere including nested objects and query parameters.

State changes are the genuinely hard part. A change expressible as a field update should be one: `PATCH /orders/{id}` with `{"shippingAddress": ...}`. But a change with side effects, preconditions, or a meaning beyond the field it touches should be an explicit action: `POST /orders/{id}/cancel`, not `PATCH` with `{"status": "cancelled"}`.

The honest statement, which purists dislike: strict resource orthodoxy produces awkward interfaces for genuinely verb-shaped operations. Cancelling, refunding, retrying, publishing, and rotating a key are actions with rules, not attributes with values. Forcing them into a `PATCH` on a status field hides that a cancellation cannot be undone by setting the field back, hides that it triggers a refund, and gives you nowhere to put the cancellation reason. Use an action sub-resource and say why in the schema description.

### 3. Make the machine-readable contract the artefact

The deliverable is an OpenAPI document or a `.proto` file, not a wiki page describing the endpoints. Prose specifications diverge from the implementation silently: the first field renamed without a doc edit is invisible, and from then on the document is confidently wrong, which is worse than absent because callers trust it.

Bind the schema to the implementation in one of two directions and enforce it in CI:

- **Generated from the code**, with the generated file committed so a diff shows up in review. A PR that changes the API and does not change the schema file is then visibly wrong.
- **Written first and verified against the running service** by contract tests or a request/response validator in the test environment. This is the better direction when several teams consume the API, because the schema becomes reviewable before the code exists.

Either way, CI has to fail when they disagree. A schema nobody checks is a prose document with more punctuation.

Generate client libraries and the reference documentation from that file rather than hand-writing them. The point is not saving effort; it is that the schema being load-bearing is what keeps it true.

### 4. Design the errors as part of the interface

Errors are the part of the API that callers hit most and read least carefully, so the structure has to be uniform enough to handle generically.

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "The card was declined for insufficient funds.",
    "requestId": "req_01HQ8Z9K3M",
    "details": [
      {"field": "paymentMethodId", "issue": "declined_by_issuer"}
    ]
  }
}
```

- **A machine-readable `code`, distinct from the message.** Callers branch on the code. If the only distinguishing feature is the message text, every client ends up matching on strings and your next copy edit is a breaking change.
- **The message for a human**, in a log or a support ticket. Do not put display copy for end users in it — the caller's users speak a language you have not decided about.
- **Enough detail to act on.** Which field, which constraint, which of the three ids was unknown. "Invalid request" costs the caller a support ticket.
- **Nothing internal.** No stack traces, no SQL, no internal hostnames, no upstream vendor error verbatim. Carry a `requestId` instead so support can find it on your side.
- **The code set is versioned like anything else.** Adding a code is a compatible change only if callers were told to treat unknown codes as the generic class; say so in the schema.

Map to status codes deliberately: 400 for a malformed request, 401 unauthenticated, 403 authenticated but not permitted, 404 for a resource that does not exist or that this caller may not know exists, 409 for a state conflict, 422 for a well-formed request that fails a business rule, 429 rate-limited, 5xx for your fault. The distinction that carries the most weight is 4xx versus 5xx, because it tells a client whether retrying could possibly help.

Returning `200 OK` with an error in the body breaks that. Every HTTP client library, every service mesh retry policy, every dashboard and every alert keys on the status code; a 200 makes failures invisible to all of them, and the caller only discovers the convention by reading a document they did not know existed. `references/errors-and-limits.md` has the full status-code table and the retry classes that go with it.

### 5. Decide pagination, filtering and sorting up front

Retrofitting pagination onto a collection that shipped without it is a breaking change, so every collection endpoint is paginated from the first release, including the ones that "will only ever have a few rows".

- **Cursor over offset for anything that changes.** With `?offset=100`, a row inserted before the cursor while the caller pages shifts everything down: the caller sees one row twice and never sees another. Offset is acceptable only over a genuinely immutable or snapshot-consistent dataset.
- **A maximum page size, enforced server-side**, with a documented default. A caller asking for a million rows should get the maximum and a documented note, not a timeout.
- **A stated ordering guarantee.** An unordered paginated list is broken by construction. Order by a total key — a creation timestamp plus the id as a tiebreaker — and say in the schema that the order is stable.
- **The cursor is opaque.** Return it and take it back verbatim; document that its format may change. A caller who decodes it has coupled to your indexing strategy.
- **Filtering that maps to something you can serve.** Enumerate the filterable fields rather than accepting an expression language you will have to support against every future storage engine.

### 6. State idempotency and retry semantics

Clients retry whether or not you designed for it — a proxy timeout, a mobile network, a job runner with a `max_attempts` setting. The only question is whether the retry is safe.

`GET`, `PUT` and `DELETE` should be idempotent by definition; the work is making them genuinely so, including `DELETE` on an already-deleted resource returning success rather than 404. `POST` that creates something is not idempotent, and that is where duplicate orders come from. Accept an `Idempotency-Key` header on those operations, store the key with the response for a documented window, and return the original response on a repeat rather than creating a second resource. Say in the schema how long keys are retained and what happens when the same key arrives with a different body.

Document, per operation, whether it is safe to retry and with what backoff. Then make the answer visible in the errors: a 429 or 503 carrying `Retry-After` tells a client exactly what to do, and a client told nothing will hammer you.

### 7. Set the compatibility guarantee before anyone integrates

This is the section that does the real work, because it is the one people skip and then cannot recover from.

Write down, in the API's documentation, what you promise not to change and what callers must tolerate. The second half is what makes future change possible: state that clients must ignore unknown fields, must treat unknown enum values as a documented fallback, and must not depend on field order or on the absence of a field.

| Change | Compatible? | Why |
| --- | --- | --- |
| Adding an optional response field | Yes, if clients ignore unknown fields | Strict schema validation on the client turns this breaking, which is why the tolerance rule has to be stated |
| Adding an optional request field with a default | Yes | Existing callers keep the old behaviour |
| Adding a new endpoint or resource | Yes | Nobody is calling it |
| Adding a value to an enum | No, in practice | Generated clients often deserialise into a closed type and throw on an unknown value. Only compatible if you specified an unknown fallback from the start |
| Removing or renaming a field | No | Silent for you, a null dereference for them |
| Making an optional request field required | No | Every existing caller starts failing validation |
| Tightening validation on an existing field | No | Requests that worked yesterday now 400 |
| Changing a default value | No | The behaviour of an unchanged caller changes underneath them |
| Narrowing what an existing value means | No, and it is the sneakiest one | The schema is unchanged, so no tool flags it, and callers' business logic quietly becomes wrong |
| Changing a field's type, including int to string | No | Even widening breaks strict deserialisers |
| Adding a new error code | Depends | Compatible only under a documented unknown-code fallback |
| Making an error condition stricter | No | The caller's happy path shrinks without warning |

On versioning strategy there is no winner to declare, only trade-offs to state:

| Strategy | Buys you | Costs you |
| --- | --- | --- |
| URI versioning (`/v2/orders`) | Obvious, cacheable, trivially routable, easy to explain | Duplication across versions; callers upgrade in one big step; the version tends to leak into every internal name |
| Header negotiation (`Accept: application/vnd.acme.v2+json`) | Fine-grained, one URL per resource, per-endpoint evolution | Invisible in logs and browsers, easy to get wrong in caches and proxies, harder to test |
| No versioning, additive-only forever | No migration work, one implementation to run | Every mistake is permanent; the schema accumulates deprecated fields that must keep working |

Most services should default to additive-only evolution and reserve a version bump for a genuine change of model — not for tidiness. A new major version is a second production surface to run, secure and support, usually for years.

`references/versioning.md` has the full breaking-change catalogue, worked examples of compatible alternatives to each breaking change, and the mechanics of running two versions at once.

### 8. Deprecate as a process, not an announcement

You cannot deprecate what you cannot see. Before announcing anything, instrument usage per endpoint, per field where you can, and per caller identity — an API key, a client id, a service account. An API with no usage telemetry cannot be retired safely, so the telemetry is the first task, not the last.

Then run the process on dates:

1. **Announce with a sunset date**, in the changelog, the schema description, and directly to callers you can identify. Give a window proportional to how hard the migration is.
2. **Signal in the response**: `Deprecation: true` and `Sunset: Wed, 31 Dec 2026 23:59:59 GMT`, plus a `Link` header pointing at the migration guide. A machine-readable signal reaches the client authors who never read the changelog.
3. **Watch the usage curve.** It will flatten well above zero.
4. **Contact the remaining callers individually.** This is the step that actually works, and it is the step that gets skipped. The long tail is usually a handful of integrations, several of them internal.
5. **Brown-out before shutdown**: fail the endpoint for a scheduled hour, twice, before the sunset date. It surfaces the callers who never answered and it does so at a time you chose.
6. **Turn it off**, and keep returning a `410 Gone` with a link rather than a 404, so the remaining caller learns what happened.

## Reviewing an existing API

Read it as a caller, not as its author. Take the top consumer task and write the integration you would have to write — actually write it, including the error handling, the pagination loop and the retry.

The friction shows up immediately: the field you have to fetch from a second endpoint, the enum with a value the docs do not list, the list endpoint that returns everything, the error you cannot distinguish from another. Keep the list, then sort it by whether the fix is compatible. Compatible fixes ship now; breaking ones go in the compatibility guarantee's next revision, or into the deprecation process.

```bash
# Read it the way a caller does, including the failure paths.
curl -sS -D- --max-time 10 https://api.example.com/v1/orders?limit=2 | head -40
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://api.example.com/v1/orders/does-not-exist
```

## Output format

Report a design or a review in this shape:

```markdown
## Consumer tasks
[The three to five things callers actually do, in their words.]

## Resources and operations
[Path, method, purpose, and the task each one serves. Note any action sub-resources and why.]

## Schema
[The OpenAPI or protobuf artefact, and how it is kept true — generated, or verified in CI.]

## Errors
[The structure, the code list, and the status code each maps to.]

## Pagination and filtering
[Cursor or offset with the reason, page size default and maximum, the ordering guarantee.]

## Idempotency
[Which operations are safe to retry, where idempotency keys apply, the retention window.]

## Non-functional contract
[Rate limits and how they are communicated, auth and scopes, request size limits, timeouts.]

## Compatibility guarantee
[What is promised not to change, what clients must tolerate, and the versioning strategy with its trade-off.]

## Deprecation policy
[The usage telemetry that exists, the notice period, the signals sent, the brown-out plan.]

## Known compromises
[Where the design is awkward and why that was the better trade. State these rather than letting a reviewer find them.]
```

## Anti-patterns

**The database schema as the API.** One endpoint per table, join tables exported as resources, internal column names in the payload. It leaks the storage model to every caller, and the first refactor you wanted to do becomes a breaking API change, so it does not happen and the schema calcifies instead.

**Designing for imagined consumers.** A filter grammar, an expansion syntax and three levels of polymorphism for callers who do not exist. Every one of them is now a permanently supported feature that constrains the implementation, and the real consumer who arrives later needs something else anyway.

**200 with an error body.** Every retry policy, every client library's error handling, every dashboard and every alert keys on the status code. A 200 makes failures invisible to all of them, and the caller discovers the convention only by reading documentation they did not know to look for.

**Offset pagination over changing data.** A row inserted while the caller pages shifts the window: they see one record twice and never see another. The bug appears as a mysterious duplicate downstream, weeks later, and nobody connects it to pagination.

**A hand-written spec that drifts.** The document says the field is `customerId` and the service returns `customer_id`. Nothing fails; the schema simply becomes confidently wrong, and every new integration starts by discovering that it cannot be trusted.

**Breaking changes shipped as additive.** Tightening validation, narrowing an enum value's meaning, or changing a default. The schema diff looks harmless and no tool objects, and the failure lands in a caller's production two weeks later where nobody can connect it to your release.

**Deprecating without usage telemetry.** The announcement goes out, the window passes, the endpoint is switched off, and an integration nobody knew about breaks. Without per-caller usage you have no way to know when it is safe, so either the retirement never happens or it happens blind.

**A new version because the old one was untidy.** `/v2` that renames fields and reorders nesting, with no capability the old one lacked. Every caller pays a migration for your aesthetics, most of them do not migrate, and you now run two surfaces forever.

## Reference files

- `references/versioning.md` — read when deciding whether a change is breaking, or planning a version or a deprecation: the full breaking-change catalogue with a compatible alternative for each, the enum and default-value traps, how to run two versions at once, and the deprecation timeline with the headers and the brown-out schedule.
- `references/errors-and-limits.md` — read when designing errors, pagination or the non-functional contract: the status code table with retry classes, error code naming, the cursor pagination implementation and its ordering guarantee, idempotency key handling, and rate limit headers and quota design.
