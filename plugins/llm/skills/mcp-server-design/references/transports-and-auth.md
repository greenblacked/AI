# Transports and authorisation

Read this when choosing between stdio and Streamable HTTP, when deploying a server that
anyone other than its author will reach, and when reviewing how a remote server checks
who is calling. Each rule names the revision it comes from; text not tagged is guidance
from this repository.

## Contents

- Choosing a transport
- stdio
- Streamable HTTP
- What changed in 2026-07-28
- Authorisation for a remote server
- Rejecting the wrong caller
- Calling upstream services
- Hostile content
- Review checklist

Spec pages used:
[2025-11-25 transports](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/transports.mdx),
[2025-11-25 authorization](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/authorization.mdx),
[2026-07-28 stdio](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/stdio.mdx),
[2026-07-28 Streamable HTTP](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/streamable-http.mdx) and
[2026-07-28 authorization](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/index.mdx).

## Choosing a transport

| Question | stdio | Streamable HTTP |
| --- | --- | --- |
| Who starts it? | The client launches it as a subprocess | You run it as an independent process |
| Who can reach it? | The user who launched it | Anyone who can reach the endpoint, so it needs authentication |
| Where do credentials come from? | The environment | OAuth bearer tokens |
| Fits | A developer tool, a local file or repository helper | A shared service, a hosted product, anything multi-user |

Start with stdio if the server only touches things on the user's machine. A server that
holds a shared credential or serves several people is a remote server even if you begin by
running it on a laptop, and should be built as one.

## stdio

Both revisions agree on the framing:

- Messages are JSON-RPC, UTF-8, one per line, and must not contain embedded newlines.
- The server reads stdin and writes stdout. It must not write anything to stdout that is not
  a valid MCP message.
- The server may write UTF-8 text to stderr for logging of any severity, and the client may
  capture, forward or ignore it. The client should not treat stderr output as an error.

What follows from that:

- Configure logging to stderr before anything else runs, including inside imported
  libraries. A library that prints a banner or a warning to stdout breaks the stream the
  same way your own `print` does.
- Do not write a log line to stdout "just while debugging". Use the Inspector instead.
- Never log request bodies that may hold secrets, and never log environment variables.
- Exit when stdin closes. 2026-07-28 says servers should exit promptly on end-of-file on
  standard input, which is the primary graceful-shutdown signal.
- Authorisation: both revisions say a stdio implementation should not follow the OAuth
  specification and should retrieve credentials from the environment. Pass the secret
  through the environment variable or a file the client's configuration names, scope it to
  what the tools need, and do not echo it into any result.
- A stdio server runs with the launching user's privileges. Build commands as argument
  arrays, never by interpolating tool input into a shell string, and restrict file tools to
  an explicit root.

2026-07-28 deprecates the protocol's own Logging feature and suggests logging to stderr on
stdio or using OpenTelemetry ([changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx),
Deprecated 1). Do not build new log delivery on `notifications/message`.

## Streamable HTTP

A single MCP endpoint path, for example `https://example.com/mcp`. Both revisions require
these security rules, in the same words:

1. Validate the `Origin` header on all incoming connections to prevent DNS rebinding. If
   it is present and invalid, respond 403 Forbidden. The body may be a JSON-RPC error
   response with no `id`.
2. When running locally, bind to localhost (127.0.0.1) rather than all interfaces
   (0.0.0.0). This is a SHOULD.
3. Implement proper authentication for all connections. Also a SHOULD.

Consequences worth stating:

- The Origin rule applies when the header is present. A non-browser client sends none, so
  an Origin check protects browsers from being used against your server and is no
  substitute for authentication. Do both.
- Compare Origin against an explicit allowlist of exact origins, not a substring or
  suffix match, and fail closed when the list is empty.
- A server bound to 127.0.0.1 is still reachable from every page open in the user's own
  browser through DNS rebinding unless Origin is checked. Binding is not the control.
- Never bind to 0.0.0.0 without authentication in front of it.
- Terminate TLS in front of any server that is not strictly local.

Per-request mechanics both revisions share:

- Each client message is a new HTTP POST to the endpoint with an `Accept` header listing
  `application/json` and `text/event-stream`.
- A response to a request is either one JSON object or an SSE stream; a notification gets
  202 Accepted with no body.
- The client sends `MCP-Protocol-Version` on subsequent requests, and an invalid or
  unsupported value gets 400 Bad Request.

2025-11-25 adds optional behaviour a server may or may not implement: a session
identifier in `MCP-Session-Id`, a GET endpoint for server-initiated messages, and SSE
event ids with `Last-Event-ID` for resuming. If you assign session ids, they should be
globally unique and cryptographically secure, and the session identifies a conversation,
not a caller. The authorisation rule still requires credentials on every HTTP request
within a session. A server that keeps sessions in process memory needs sticky routing and
loses them on restart; do not rely on them, or hold them in storage every instance shares.

## What changed in 2026-07-28

From the [changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx)
and the Streamable HTTP page:

- No `initialize` handshake and no `MCP-Session-Id`. Each request carries its protocol
  version and client capabilities in `_meta`.
- `server/discover` is a method servers must implement, advertising supported versions,
  capabilities and identity.
- The HTTP GET endpoint is gone. Change notifications travel on the response stream of a
  `subscriptions/listen` request.
- SSE resumption by `Last-Event-ID` is removed: a broken stream loses the in-flight
  request and the client re-issues it.
- Streamable HTTP requests carry `Mcp-Method` (and `Mcp-Name` for `tools/call`,
  `resources/read` and `prompts/get`) headers mirroring the body, plus `MCP-Protocol-Version`
  that must match the body's version or the server answers 400 with a `HeaderMismatch`
  error. Servers should send `X-Accel-Buffering: no` when opening an SSE stream so that
  reverse proxies do not buffer it.
- Server-initiated sampling, elicitation and roots requests become `InputRequiredResult`
  replies the client answers by retrying the request.

For a tool author the practical rule is the same as before: keep no state in the connection,
hand out explicit handles for what must persist, and let any instance answer any request.
A server written that way needs no change to move between the two revisions except the
framing the SDK handles.

## Authorisation for a remote server

Authorisation is optional in the protocol, but a remote server with real data behind it
should treat it as required. The server is an OAuth 2.1 resource server; the authorisation
server may be separate, and designing it is `auth-design`'s subject. What the MCP server
itself must do, in both revisions unless marked:

**Publish where to authenticate.**

- Implement OAuth 2.0 Protected Resource Metadata (RFC 9728), including an
  `authorization_servers` field with at least one entry.
- Provide the metadata location either in the `WWW-Authenticate` header of 401 responses,
  as `resource_metadata`, or at a well-known URI (`/.well-known/oauth-protected-resource`,
  optionally suffixed with the endpoint path). Doing both costs nothing.
- Include a `scope` parameter in the challenge so clients request the least that works.
  This is a SHOULD.

**Validate every token on every request.**

- Authorisation goes in the `Authorization: Bearer` header of every HTTP request. Access
  tokens must not be in the URI query string, so ignore one if sent and keep URLs that
  could carry one out of logs.
- Validate the token as OAuth 2.1 section 5.2 describes: signature or introspection,
  issuer, expiry.
- Validate that the token was issued for this server as its audience, per RFC 8707. Only
  accept tokens valid for your own resources, and reject tokens that do not name you in
  the audience claim or that you cannot otherwise verify were meant for you. Compare against
  the canonical URI you published as the resource in your metadata, exactly. If your
  authorisation server offers no way to bind a token to a resource, you cannot meet the
  requirement; say so and choose a server that does rather than skipping the check.
- Answer invalid or expired tokens with 401.

**Answer under-scoped calls usefully.**

- A call with too few scopes gets 403 Forbidden with a `WWW-Authenticate` Bearer challenge
  carrying `error="insufficient_scope"`, the scopes needed, and `resource_metadata`. The
  client can then run a step-up flow. This is a SHOULD in the spec.
- Keep scopes narrow and tied to tool groups, such as separate read and write scopes.
  A single all-access scope means every approved client holds the keys to every tool.
- 2026-07-28 allows `tools/list` to vary with the authorisation presented, so a caller
  may see only the tools its scopes permit. Enforce scopes at call time as well, because
  hiding a tool is not denying it.

**Clients and registration.** How a client identifies itself is mostly the authorisation
server's business: the spec prefers OAuth Client ID Metadata Documents, and 2026-07-28
deprecates Dynamic Client Registration in their favour while keeping it for compatibility.
If your MCP server is also a proxy in front of a third-party authorisation server using a
static client ID, it must obtain user consent for each dynamically registered client before
forwarding to that server, or it is a confused deputy for stolen authorisation codes.

## Rejecting the wrong caller

Write a test for each of these refusals; each is a defect the spec's wording exists to
prevent.

| Request | Expected |
| --- | --- |
| No `Authorization` header | 401 with a challenge naming `resource_metadata` |
| Expired token | 401 |
| Token whose audience is another service | 401 |
| Token signed by an issuer you do not trust | 401 |
| Valid token missing the scope the tool needs | 403 with `insufficient_scope` |
| Browser request with a foreign `Origin` | 403 before any token is considered |
| Token in the query string, header absent | 401 |

## Calling upstream services

If a tool calls another API, the access token you received from the MCP client is for you,
not for that API. The spec says the server must not pass through the token it received, and
that any upstream token is a separate token issued by the upstream authorisation server.
Passing the token through also makes the upstream trust a credential it never
audience-checked, which is how a confused deputy arises.

So obtain an upstream credential of your own: a service credential with minimal scope, or a
token exchange or per-user authorisation with the upstream provider. Keep it server-side,
never return it in a result, and attribute upstream calls to the calling user in your own
audit log, because the upstream only sees the server.

## Hostile content

The spec's position is that tool annotations, and by extension descriptions of tool
behaviour, are untrusted unless they come from a trusted server, and that tool results
should be sanitised. What that means for a server author, as guidance:

- A description is read by the model as instructions. Anything in it that tells the model to
  act outside the tool's stated job, or to hide something from the user, is the signature of
  a poisoned definition. Keep your own definitions free of it so that a reviewer or scanner
  can flag the same pattern elsewhere without false positives.
- A definition that changes after a user approved it is a risk of its own: the user
  consented to one description and the model reads another. Version your tool list and
  announce description changes in release notes. The tool-list snapshot test is what
  enforces this on your side.
- Names are scoped to one server. A client combining servers can end up with two tools of
  the same name, so a generic name can be shadowed by, or shadow, another server's tool.
  Distinct names reduce the chance that a call is routed to the wrong server.
- Text a third party can write, such as a ticket body, can contain instructions aimed at
  the model. Return it as data, keep it out of descriptions, and do not give a tool that
  reads untrusted text a sibling that can send data out in the same server without the
  approval controls `agent-security-review` describes.

## Review checklist

- Local server: stdout carries only protocol; logging goes to stderr; credentials come from
  the environment; process exits on stdin close; no shell string built from input.
- HTTP server: Origin allowlist with 403; loopback bind for local use; authentication on
  every request; TLS in front.
- Auth: metadata published; 401 challenge carries `resource_metadata`; audience checked
  against the published resource; 403 `insufficient_scope` on under-scoped calls; no token
  in query strings or logs.
- Upstream: separate credential; no token passthrough; per-client consent if proxying a
  third-party authorisation server.
- No state in the connection; handles checked against the caller on every call.
- Tool list and descriptions snapshotted and reviewed on every change.
