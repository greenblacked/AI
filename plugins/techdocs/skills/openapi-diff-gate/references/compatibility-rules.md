# Compatibility rules by direction

Read this when a finding is graded as potentially breaking, when you think the differ's
grade is wrong, or when the change is one a spec diff cannot see. The organising rule:
the request is what the client sends and the server must keep accepting; the response is
what the server sends and the client must be able to handle. Narrowing the first breaks
clients, and so does widening the second.

## Contents

- [Request side](#request-side)
- [Response side](#response-side)
- [Cases that depend on how clients were built](#cases-that-depend-on-how-clients-were-built)
- [Shared schemas](#shared-schemas)
- [What a spec diff never shows](#what-a-spec-diff-never-shows)

## Request side

Parameters (path, query, header, cookie) and request bodies.

| Change | Verdict | Why |
| --- | --- | --- |
| Operation or path removed | Breaking | Every caller of it fails |
| Path parameter renamed or path template changed | Breaking | The URL the client builds no longer matches |
| New required parameter or required body property | Breaking | Existing requests lack it and are rejected |
| Optional parameter or property made required | Breaking | Same, for callers that omitted it |
| Parameter moved between query, header and path | Breaking | The server no longer reads it where the client puts it |
| Type changed, such as integer to string | Breaking | Previously valid values fail validation or parse differently |
| Enum value removed | Breaking | Callers sending it are rejected |
| Constraint tightened: lower `maxLength` or `maxItems`, higher `minimum`, new `pattern`, stricter `format` | Breaking | Previously valid input is rejected |
| Optional property removed from the body | Breaking in effect | Rejected where unknown properties are refused; otherwise silently ignored, which changes behaviour without an error |
| Request media type removed | Breaking | Clients sending that content type are refused |
| New security requirement, or an extra scope required | Breaking | Existing credentials stop being sufficient |
| New optional parameter or property | Compatible | Old requests are still valid |
| Enum value added | Compatible | Old values are still accepted |
| Constraint loosened | Compatible | Everything valid before is still valid |
| Optional property's default changed | Spec-compatible, behaviour-breaking | Every caller that omitted it now gets a different result; treat as a breaking change in the notes |

## Response side

Status codes, headers and bodies the server returns.

| Change | Verdict | Why |
| --- | --- | --- |
| Property removed | Breaking | Clients reading it get nothing or crash |
| Required property made optional | Breaking | Clients assuming presence fail when it is absent |
| Property made nullable | Breaking | Clients without null handling crash on the first null |
| Type changed | Breaking | Deserialisation fails |
| Success status code changed or removed | Breaking | Clients branch on the code they were told to expect |
| Response media type removed | Breaking | Clients requesting it get a 406 or a body they cannot parse |
| Enum value added | Potentially breaking | Fatal to strict generated enums and exhaustive switches; harmless to tolerant readers |
| Constraint loosened: longer strings, larger numbers, more items | Potentially breaking | Clients that sized storage or validated against the old limit fail |
| New error status code documented | Potentially breaking | Clients without a branch for it fall into a generic error path |
| New optional property | Usually compatible | Breaks clients that reject unknown properties; most generators tolerate them, some configurations do not |
| Property made required, or enum value removed, or constraint tightened | Compatible | The server returns a subset of what it returned before |
| Response header removed | Breaking where clients read it | Pagination, rate-limit and ETag headers are read even when undocumented as required |

## Cases that depend on how clients were built

For each potentially breaking finding, answer with evidence rather than intuition:

- **Who consumes this operation?** Your own front end, first-party SDKs, partner
  integrations, the public. Usage telemetry by client identifier is the best evidence;
  the list of generated SDKs is the next best.
- **How do the SDKs model enums and unknown properties?** Check the generator and its
  configuration for each language you ship. A strict enum in one language and a string in
  another make the same change breaking for half the clients.
- **Can you reach every consumer before release?** If not, treat the change as breaking.

Record the answer in the pull request next to the finding. A future reviewer needs to see
why a `WARN` was accepted, not only that it was.

## Shared schemas

A component referenced from both a request body and a response body takes both rule sets.
Adding an enum value is compatible for the request use and potentially breaking for the
response use; tightening a constraint is the reverse. A structural differ evaluates each
usage, which is one reason to rely on it instead of reasoning about `components/schemas`
in isolation.

When a shared schema keeps producing findings on one side, split it into request and
response variants. The split is itself compatible when both variants keep the old shape.

## What a spec diff never shows

The differ compares two documents. These break clients without changing either:

- Behaviour behind an unchanged schema: a different sort order, a different meaning for
  the same field, a changed default applied in code but never stated in the spec.
- Error semantics: the same status code returned for a different condition, or an error
  body whose machine-readable code changed while the schema did not.
- Limits and timing: rate limits, page sizes, timeouts, eventual-consistency windows.
- Authentication and tenancy changes made outside the spec's security section.
- A spec that has drifted from the implementation, so both sides of the diff are wrong.

Cover these with the release's breaking-change review and contract tests; the diff gate
cannot.
