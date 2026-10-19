# Tool design

Read this when writing or reviewing the definitions a server exposes through `tools/list`,
or the results and errors its tools return. Requirements are marked with the spec revision
they come from; everything else is guidance from this repository, labelled as such.

## Contents

- What the spec fixes
- Naming
- Descriptions
- Input schemas
- Results
- Errors
- State across calls
- Annotations
- Keeping the list stable

## What the spec fixes

Sources: the [2025-11-25 tools page](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/server/tools.mdx)
and the [2026-07-28 tools page](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx).
Both agree on everything in this list unless a revision is named.

- A tool has a `name`, an optional `title`, a `description`, an `inputSchema` and an
  optional `outputSchema` and `annotations`.
- `inputSchema` must be a valid JSON Schema object, not `null`, and defaults to the 2020-12
  dialect when no `$schema` is present.
- Servers must validate all tool inputs, implement access controls, rate limit tool
  invocations and sanitise tool outputs.
- Servers that support tools must declare the `tools` capability; its `listChanged` flag
  says whether the server will notify when the list changes.

Everything below that is not tagged with a revision is this repository's judgement.

## Naming

The spec says tool names should be 1 to 128 characters, case-sensitive, and drawn only
from ASCII letters, digits, underscore, hyphen and dot, with no spaces or commas. These
are SHOULD rules in both revisions; treat them as hard limits, because nothing is gained
by breaking them and a client is not obliged to handle a name that does.

Guidance:

- Name the task, verb first, with the noun specific: `search_tickets`, `get_ticket`,
  `add_ticket_comment`. A bare `search` collides with the same name on another server, and
  2026-07-28 tells clients to disambiguate by prefixing a server identifier, which makes
  your tool's name differ from the one you tested.
- Keep one naming pattern across the server. The model infers the pattern and uses it to
  guess at tools it has not read closely.
- Do not give two tools names that differ by one word and answer the same question. If you
  cannot say in a sentence when to use one rather than the other, they are one tool.

## Descriptions

The description is the only place the model learns what the tool is for. Write it as the
instructions you would give a capable colleague who has never seen the system.

A description that works answers four things:

1. What the tool does, in one sentence, in the user's vocabulary.
2. When to use it, and when to use a sibling instead.
3. What it returns, including how large and in what shape.
4. What it will not do, so the model does not retry it for something it cannot give.

Weak:

```text
Search tickets.
```

Better:

```text
Find support tickets by free-text query, newest first. Use this to locate a ticket when you
do not have its id; use get_ticket when you do. Returns up to the requested number of
summaries (id, title, status, updated time), not full ticket bodies. Does not search
comments or attachments.
```

Rules that carry across servers:

- Put limits and side effects in the description. "Deletes the ticket permanently" belongs
  there, because it is what the user's consent prompt and the model's judgement both rely
  on.
- Describe each parameter in the schema's own `description`, not only in the tool's. The
  model reads both, and the schema description sits next to the field it constrains.
- Keep descriptions static. Text assembled from data other people can edit is an injection
  channel into the model's context at list time; variable content belongs in results.
- Do not instruct the model about unrelated behaviour ("always call this tool first",
  "do not tell the user"). That is the shape of a poisoned description, and clients and
  reviewers are right to treat it as one.
- Keep each description proportionate. It is resident for the whole session, so a paragraph
  per tool is the ceiling, and detail that matters only sometimes belongs in an error
  message or a result.

## Input schemas

- Type every property, list `required`, and set `"additionalProperties": false` so that a
  misspelt argument fails instead of being ignored. For a tool with no parameters the spec
  recommends `{ "type": "object", "additionalProperties": false }`.
- Use `enum` for closed sets, `minimum` and `maximum` for numbers, `maxLength` and
  `pattern` for strings that reach a query or a command, and `format` only where you
  validate it yourself.
- Give optional parameters a documented default in the description, and keep the number of
  optional parameters small. A tool with ten optional filters becomes a query language the
  model has to learn from prose.
- Prefer identifiers the model has already seen in a previous result over free text it must
  compose, and say in the description where the identifier comes from.
- 2026-07-28 relaxes `inputSchema` and `outputSchema` to allow any JSON Schema 2020-12
  keyword and adds `$ref` resolution rules ([changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx),
  minor change 10). Composition keywords that a given client or model provider does not
  support fail at the edges; test the schema through the client you target.
- Whatever the schema says, validate again on the server before the value reaches a
  database, a shell or a URL. The schema describes what a well-behaved caller sends.

## Results

- Return what the model needs for the next step and no more. A result that dumps a whole
  record set spends context the model needed for the conversation.
- When a result can be large, cap it, and say in the result how to get the rest: a cursor
  argument, or a narrower filter. A truncated list that does not say it was truncated reads
  as complete.
- If you declare an `outputSchema`, the server must return structured results that
  conform to it, and a tool that returns structured content should also return the
  serialised JSON in a text block for backwards compatibility. Both are in 2025-11-25 and
  2026-07-28. 2026-07-28 additionally allows `structuredContent` to be any JSON value, not
  only an object.
- Treat everything you put in a result as untrusted data headed for a model. If a field
  holds text written by a customer, a page author or a commit message, return it as a
  field the model can see is data, and sanitise it as the spec requires.
- Do not return secrets, tokens or internal paths in a result because they happened to be
  in the upstream response.

## Errors

The spec defines two mechanisms, and which one you use decides whether the model can
recover.

| Situation | Mechanism | Revision note |
| --- | --- | --- |
| Unknown tool, malformed request | JSON-RPC protocol error (the spec's example is code -32602 for an unknown tool) | Both |
| Invalid argument value, date in the wrong format, out of range | Result with `isError: true` | 2025-11-25 and later; 2025-06-18 listed invalid arguments as protocol errors |
| Upstream API failure, record not found, business rule refused | Result with `isError: true` | Both |
| Unexpected exception in your code | Catch it, log to stderr, return `isError: true` with a safe message | Guidance |

The spec says clients should give tool execution errors to the model so it can self-correct,
and may give protocol errors, which are less likely to lead to recovery. So the message is
the whole interface of a failure. Write it to answer three questions:

- What was wrong, in terms of the argument the model sent.
- What would be valid: the allowed values, the range, the format, or the tool that supplies
  the id.
- What to do next, if it is not obvious.

```text
No ticket with id "TCK-99213". Ids look like TCK-1234 and come from search_tickets.
Call search_tickets with the ticket title to find the id.
```

Do not include stack traces, SQL, file paths, hostnames or credentials. If the upstream
error contains them, translate it.

A tool that is rate limited or temporarily unavailable should say so and, where it is
known, when to retry, so the model does not loop.

## State across calls

2026-07-28 has no protocol-level session, and its tools page says a server that needs
state across calls, such as a basket or an open transaction, should return an explicit
handle from a creation tool and accept it as an argument on later calls. The same page
gives the design rules:

- On an authenticated server, a handle is a name, not a capability: check the caller's
  authorisation against it on every call.
- Make handles opaque, so they cannot be parsed or guessed. On an unauthenticated server
  the handle is effectively a bearer token, so give it enough entropy and a bounded
  lifetime.
- State the retention in the creating tool's description, so the model knows what it is
  committing to.
- Answer an expired or unknown handle with a tool execution error that says so, so the
  model can create a new one.

Do the same under 2025-11-25. Keeping state in the connection works until the client
reconnects or a second instance answers, and handles survive both.

## Annotations

The `annotations` field describes tool behaviour. Both revisions say clients must consider
tool annotations untrusted unless they come from a trusted server. Set them where your SDK
offers them, since well-behaved clients use them for consent prompts, but enforce the real
policy in the tool: a read-only tool should hold read-only credentials, not merely say so.

## Keeping the list stable

- 2026-07-28: `tools/list` must return the tools currently available to the requesting
  client, must not vary per connection or as a side effect of other requests, and may vary
  by the authorisation presented on the request. Servers should return tools in a
  deterministic order, which helps client caching and model prompt caches.
- Do the same under 2025-11-25 even though it does not require it: a list that depends on
  what a connection did earlier cannot be snapshotted or reasoned about.
- If you change the list at runtime, send the list-changed notification the revision
  defines and expect clients to re-read it. Prefer a fixed list.
- A tool list that varies with scopes needs one snapshot per scope set, so the contract
  test can show what each kind of caller sees.
