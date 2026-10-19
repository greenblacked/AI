---
name: mcp-server-design
description: "Build, test and secure a Model Context Protocol server: a few task-shaped tools with names and descriptions written for the model, strict input schemas, failures returned as isError results the model can act on, stdio for local servers with logs on stderr, Streamable HTTP with Origin checks and OAuth audience validation (no token passthrough) for remote ones, a tools/list snapshot test that flags description changes, and a run through MCP Inspector. Use whenever someone is writing or reviewing an MCP server, wants to expose an API or database to an agent as tools, or asks \"why does the model pick the wrong tool\", \"the client says my server output is invalid\" or \"how do we authenticate a remote MCP server\". Not for the underlying REST interface (api-design), what an agent may do with its tools (agent-security-review), login design (auth-design), or a leaked key (secret-rotation)."
allowed-tools: "Read, Grep, Glob, Write, Edit, Bash(npx:*), Bash(curl:*), Bash(jq:*), Bash(rg:*), Bash(git:*)"
---

# MCP Server Design

A good MCP server is one a model can use correctly from its tool list alone, that tells the model what went wrong when it does not, and that cannot be turned against the person who connected it.

The hard part is that the reader of your interface is a language model, and it reads every tool definition on every turn. Two things follow. Each tool you add costs context and competes with the others for selection, so an endpoint-per-tool server works worse than a smaller one shaped around tasks. And a description is not documentation, it is behaviour: changing a sentence changes which tool gets called, and an attacker who can change it, or who can put text in it, steers the model. The protocol also has two layers of failure, protocol errors and tool execution errors, and sending a recoverable mistake down the wrong one hides it from the model that could have fixed it.

## Scope

Use for: designing the tool surface of a new MCP server, wrapping an existing API or database as tools, choosing stdio or Streamable HTTP, securing a remote server, and writing the tests that keep the tool list from drifting.

Do not use for: shaping the underlying HTTP API (`api-design`), reviewing which actions an agent's tools should be allowed to take and under what approval (`agent-security-review`), designing the login and token machinery itself (`auth-design`), or rotating a credential that has leaked (`secret-rotation`). Deciding whether to install someone else's MCP server is a different job from building one; the `agent-extension-audit` skill in the security plugin covers it, so do not stretch this skill to cover that decision.

## Which spec revision

Two protocol revisions are in use, and the rules below say which one a requirement comes from.

- **2025-11-25.** Connections begin with an `initialize` handshake and may carry an `MCP-Session-Id` header; a long-lived GET stream carries server-initiated messages.
- **2026-07-28.** Stateless. Its [changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx) removes the handshake, the session header and the GET stream, adds `server/discover`, and tells servers that need state across calls to hand out explicit handles as ordinary tool arguments. Roots, Sampling and Logging are deprecated.

Clients on both will exist for some time. Design the server so it does not depend on connection state at all: that is correct under both, and it is also what lets you run more than one instance behind a load balancer. Which revisions you can serve depends on the SDK version you pin, so read its release notes before choosing an API, and copy imports from the README of that version rather than from a tutorial, because SDK class names and packages have changed between major versions.

## Workflow

### 1. Write down the tasks before the tools

List the five or six things a person would ask an agent to do with this system, in their words. Each tool should complete one of those tasks, not mirror one endpoint. A task that needs a search, three reads and a join in the underlying API is one tool that does that work, with the model supplying the question. Stop adding tools when the list covers the tasks; every extra tool is a description resident in context and a way for the model to choose wrongly.

### 2. Define each tool for the model

Read `references/tool-design.md` before writing any definition. The short form:

- Name it for the task, specific enough not to collide with another server's tool. Clients that combine servers have to disambiguate same-named tools, and the 2026-07-28 tools page says so ([tools, Tool Names](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx)). Prefer `search_tickets` to `search`.
- Write the description for a reader who has not seen your system: what the tool does, when to use it instead of its siblings, what it returns, and what it will not do.
- Make the input schema strict: typed properties, `required`, enums for closed sets, bounds, and `"additionalProperties": false`. The spec recommends exactly `{"type": "object", "additionalProperties": false}` for a tool with no parameters.
- Validate again on the server. The spec requires servers to validate all tool inputs; the schema is a hint to the model, not a guarantee about the caller.

### 3. Return errors the model can act on

The spec separates protocol errors (unknown tool, malformed request) from tool execution errors, which are normal results with `isError: true`. Anything the model could fix by trying again differently belongs in the second kind: an API failure, a bad date, a value out of range, a missing record. Since 2025-11-25, input validation errors are explicitly in that group; 2025-06-18 listed invalid arguments as protocol errors, and some SDKs still behave that way, so test what yours does.

Write the message as an instruction: what was wrong, what is valid, and what to try next. "Invalid departure date: must be in the future. Current date is 08/08/2025." is the spec's own example. Never let an exception escape as a transport failure, and never put a stack trace, credential or internal hostname in the message.

### 4. Choose the transport

Use **stdio** when the server runs on the user's machine, launched by the client. Use **Streamable HTTP** when it is shared, remote or multi-user. Read `references/transports-and-auth.md` for the details of both. Two rules apply before anything else:

- On stdio, stdout carries protocol messages and nothing else; the server must not write anything to stdout that is not a valid MCP message. Send logs to stderr. A stray `print` or `console.log` corrupts the stream, and the client reports it as a broken server rather than as your log line.
- On Streamable HTTP, validate the `Origin` header and answer 403 when it is present and invalid, bind a local server to 127.0.0.1 rather than 0.0.0.0, and authenticate every request.

### 5. Secure a remote server

A remote MCP server is an OAuth resource server. Read `references/transports-and-auth.md` for the full list; the four decisions that matter most are:

- Validate that each access token was issued for this server as its audience, and reject every other token with 401. Accepting any valid token from the authorization server lets a token minted for a different service work here.
- Do not pass the client's token on to an upstream API. If the server calls another service, it uses a separate token issued by that service's own authorization server. The spec forbids passthrough outright.
- Scope each tool's access narrowly and answer an under-scoped call with 403 and `insufficient_scope`, so a client can ask for more rather than being granted everything up front.
- Treat tool output as data that may carry hostile text. Sanitise it, and never build a tool description out of content a third party can edit.

Designing the authorization server, token lifetimes and refresh handling is `auth-design`'s ground; this skill covers only what the resource server must check.

### 6. Test the contract, then the behaviour

Read `references/testing.md` before writing tests. The order that catches the most:

1. **Snapshot `tools/list`.** Store the names, descriptions and schemas in the repository and fail the test when they change. A reviewer then sees every description edit as a diff, which is the only defence against a wording change quietly altering which tool is called.
2. **Run MCP Inspector against the real server**, in the CLI mode for the repeatable checks and the web UI for exploring.
3. **Call each tool with a bad input** and assert the result is `isError: true` with a message that names the problem.
4. **Check stdout.** Start the stdio server, send one request, and assert every line it writes is a JSON-RPC message.
5. **For HTTP, test the refusals:** a wrong Origin, no token, a token for another audience, and a token with too few scopes.

### 7. Ship with the descriptions pinned

Release the snapshot with the code. When a description changes, the diff is reviewed as a behaviour change, and the release notes say so. If you publish the server for others to install, they pin the version and compare the tool list at upgrade, so a changed description between versions is something they can see. That is the same control you are applying to yourself.

## Anti-patterns

**One tool per endpoint.** It is the fastest way to wrap an API and the slowest for a model to use: dozens of near-identical descriptions in context, and the model picks between `get_order` and `fetch_order_details` on wording alone. Collapse to the tasks from step 1.

**Throwing instead of returning `isError`.** An exception becomes a protocol error or a crash, the model sees nothing it can act on, and it retries the same call or gives up. Catch at the tool boundary and return a message.

**Logging to stdout.** It works in a terminal and fails under every client, because the client parses stdout as protocol. Configure the logger for stderr once, at start-up, before any tool is registered.

**A schema that accepts anything.** `{"type": "object"}` for a tool that needs three fields invites the model to guess, and the server then has to guess back. Strict schemas fail fast with a message the model can use.

**Trusting the token because the authorization server issued it.** A valid signature proves who minted the token, not who it is for. Without an audience check, a token issued for another resource is accepted here.

**Forwarding the caller's token upstream.** It looks like the simplest way to act as the user, and it makes the upstream API trust a token it never audience-checked, with this server as the confused deputy. Get a separate upstream credential.

**Treating `MCP-Session-Id` as a login.** In 2025-11-25 the session identifies a conversation, not a caller; the authorization requirements still apply to every HTTP request. Under 2026-07-28 there is no session to treat that way.

**Editing a description without reading the snapshot diff.** The change looks like documentation and acts like code. The snapshot test exists so that it cannot merge unseen.

**Building descriptions from live data.** A tool description assembled from rows, tickets or pages that other people write is a prompt-injection channel installed in the model's context at list time. Keep descriptions static and put variable content in results, where it is clearly data.
