# Compatibility, versioning and deprecation

Read this when deciding whether a change is breaking, choosing a versioning strategy, or
planning to retire something.

## Contents

- The breaking-change catalogue, with a compatible alternative for each
- The three traps that pass review
- Running two versions at once
- The deprecation timeline
- What to do when a caller will not migrate

## The breaking-change catalogue

Assume the strictest plausible client: one using a generated model with closed enums and
required-field validation, deserialising into a typed language. Most published clients
are stricter than the people who wrote your API expect, and "our clients are lenient" is
an assumption that stops being true the moment someone generates a client from your own
schema.

| Change | Breaking | Compatible alternative |
| --- | --- | --- |
| Remove a response field | Yes | Deprecate it in the schema, keep returning it, remove at the next major version |
| Rename a field | Yes | Add the new name, populate both, deprecate the old one with a sunset date |
| Change a field's type | Yes, including int to string and string to enum | Add a new field with the new type alongside |
| Make an optional request field required | Yes | Keep it optional; reject the missing case with a specific error code and a documented deadline first |
| Add a required request field | Yes | Add it optional with a default that preserves current behaviour |
| Tighten validation on a field | Yes | Log the violations first, publish the rate, then enforce on a date, having contacted the callers producing them |
| Change a default value | Yes | Add a new explicit value; leave the default alone. If it must change, treat it as a version bump |
| Add a value to an enum | Usually | Only safe if the schema documented an unknown-value fallback from the beginning. Otherwise ship it behind an opt-in field or a new version |
| Remove an enum value | Yes | Stop producing it, keep accepting it, deprecate on a date |
| Narrow the meaning of an existing value | Yes, and it is invisible | Introduce a new value with the new meaning; leave the old one as it was |
| Change pagination defaults or maximums | Yes for the maximum, usually safe for the default | Callers that relied on the old maximum start truncating silently |
| Change a resource's identifier format | Yes | Ids are opaque only if you said so before shipping. If you did not, this is a version bump |
| Add a new endpoint | No | — |
| Add an optional response field | No, under the tolerance rule | Requires that the rule was stated |
| Relax validation | No | — |
| Add a new error code | Depends on the fallback rule | Under a documented unknown-code fallback, safe; otherwise callers hit an unhandled branch |
| Change an error's status code | Yes | Callers branch on status before they branch on code |
| Make an operation slower | Not a schema change, but breaking in practice | Client timeouts are part of the contract even though they are not in the schema |

## The three traps that pass review

**The enum addition.** A protobuf or OpenAPI enum generated into a closed type throws on
an unknown value. The producer sees an additive one-line diff; a consumer sees a
deserialisation exception on every message carrying the new value. This is the most
common way a team ships a breaking change believing it is additive. The prevention is
stated up front: define an `UNKNOWN`/`UNSPECIFIED` member as the zero value, and put in
the compatibility guarantee that clients must map anything unrecognised onto it. After
callers have integrated, it is too late to add that rule retroactively.

**The narrowed meaning.** `status: "pending"` used to mean "not yet charged"; after a
refactor it means "not yet authorised", and a new `authorised` state now covers part of
what `pending` covered. The schema diff is empty. Every caller whose business logic
branched on `pending` is now quietly wrong, and there is no signal anywhere. Treat a
change of meaning as a change of name: introduce a new value.

**The default change.** A caller that never sent the field gets different behaviour after
your deploy without changing a line. It looks like a bug in their code and it is
extremely hard for them to trace back to you. If a default genuinely must change,
announce it with a date, and where possible require the field explicitly for a period so
the change is visible.

## Running two versions at once

Only do this when the model genuinely changed. When it does:

- Implement one of them in terms of the other rather than forking the handlers. Usually
  the old version becomes a translation layer over the new one, so bug fixes land once.
  A forked implementation drifts, and then "v1 behaves differently" becomes true in ways
  nobody documented.
- Share the storage and the business logic. If v1 and v2 can disagree about the state of
  the same order, you have two products.
- Version the whole surface, not individual endpoints. Callers cannot reason about a
  mixture, and `/v1/orders` calling into a `/v2/customers` shape is how inconsistency
  gets in.
- Put a shutdown date on the old version at the moment you launch the new one. A version
  with no end date never ends; it accumulates callers for years and every future change
  has to be made twice.
- Instrument per-version, per-caller usage on day one. Retirement depends entirely on it.

Header negotiation instead of a URI prefix trades visibility for granularity. It is a
reasonable choice for an API with sophisticated consumers and a strong test story; it is
a poor one when people debug with `curl` and browser tools, or when caches and proxies
sit in the path and will need `Vary` handled correctly everywhere.

## The deprecation timeline

A workable default for an external API. Compress it for internal callers you can reach
directly; extend it where the migration requires the caller to change data models.

| When | Action |
| --- | --- |
| T-0 | Announce: changelog, schema `deprecated: true` with a description naming the replacement, an email to identified callers, a migration guide with a worked before-and-after |
| T-0 | Start returning `Deprecation: true`, `Sunset: [date]`, and `Link: [migration guide]; rel="sunset"` on every response from the deprecated surface |
| T+30d | First usage review. Segment the remaining callers by volume and identity |
| T+60d | Contact each remaining caller individually. This is the step that actually moves the curve |
| T+90d | First brown-out: return 410 for one hour at a time you choose and have announced |
| T+120d | Second brown-out, two hours, at a different time of day so a different timezone notices |
| T+150d | Final notice to anyone still calling, naming the shutdown date and the ticket |
| T+180d | Shut down. Return `410 Gone` with a body carrying the migration link, not a 404 |

Two details that matter more than the schedule. Brown-outs must be announced and must be
short — an unannounced one is an outage you caused. And `410 Gone` rather than `404`
after shutdown is what tells the last caller's engineer what happened; a 404 sends them
hunting for a typo in their own code.

## What to do when a caller will not migrate

The long tail is usually a small number of integrations with no maintainer, an internal
service whose team disbanded, or a customer whose contract predates the API programme.

- If it is internal and unowned, adopting the migration yourself is usually cheaper than
  the coordination. Do it and move on.
- If it is a customer with commercial weight, an extension is a business decision, not an
  engineering one. Escalate it as such, with the cost of holding the old surface open
  stated in engineering time, and get a dated commitment rather than an open extension.
- If nobody can identify the caller at all, that is a finding about authentication rather
  than about deprecation: an API where traffic cannot be attributed to a principal cannot
  be operated safely. Fix the attribution first; `access-review` covers the identity side.

What does not work is extending the date without changing anything else. The remaining
callers did not miss the deadline because it was too soon; they missed it because nothing
compelled them, and another ninety days of the same produces the same result.
