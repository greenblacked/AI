---
name: graphql-review
description: "Review or design a GraphQL schema and its resolvers when you are authorised to examine the service: read the schema from its SDL or an introspection result, find the N+1 resolver behind a slow query and fix it with a batched loader, bound what a client can ask for with depth and complexity limits and by turning introspection off in production, enforce authorization inside each resolver rather than trusting the client, and evolve the schema additively with deprecations. Use for \"why is this GraphQL query so slow\", \"one query took the API down\", \"can a client enumerate our whole schema\", or \"change a field without breaking the apps\". Not for a REST or RPC contract (api-design), tuning the SQL a resolver issues (sql-performance), modelling tables (schema-design), or authorization architecture across services (authorization-design)."
allowed-tools: Read, Grep, Glob, Edit
---

# GraphQL review

Good looks like a schema whose cost is bounded before it reaches a resolver, whose every field
returns only what the caller may see, and whose resolver tree issues a number of backend calls
that does not grow with the result size.

The job is hard because a GraphQL request is a query the client writes, not an endpoint you
chose. A single document can fan out to thousands of resolver calls, walk a cyclic type to any
depth, and select fields the UI never shows — and the server executes all of it unless each of
those is bounded on purpose.

## Scope

Use for: reviewing or designing a schema and its resolvers on a service you own or are
contracted to inspect; diagnosing a slow or expensive GraphQL query; closing an
authorization gap where a field is readable through the graph but should not be; bounding
query cost before launch; and evolving a schema without breaking installed clients.

Do not use for: a REST, RPC or event contract, which is `api-design`; the SQL a resolver
issues to the database, which is `sql-performance`; designing the tables behind the
resolvers, which is `schema-design`; deciding the authorization model across services, which
is `authorization-design`; a diff review for vulnerability classes, which is
`security-review`; or a slow trace that has not yet been localised to a resolver, which is
`trace-latency-analysis`.

## Hard gates

1. **Authorisation first.** State whose service it is and why you may read the schema. An
   introspection result is source code.
2. **Read before you change.** Print the schema and the offending operation before proposing a
   fix. A resolver you cannot point at is a guess.
3. **No production introspection without consent.** Running an introspection query against a
   live third-party endpoint is a change to their service; ask first, or read a captured SDL.

## Workflow

### 1. Get the schema and the operation

```bash
# From a running endpoint, when you are authorised to query it
curl -s https://api.example.com/graphql \
  -H 'content-type: application/json' \
  -d '{"query":"{ __schema { types { name kind } } }"}' | jq .

# From a local server or a repository
graphql-inspector introspect schema.graphql --write schema.json
```

Read the type graph, then read the operation that is slow or suspect. The cost lives in the
combination: which root field, which nested types, how many list fields, and what arguments.
[Query cost and limits](references/query-cost-and-limits.md) has the introspection query and
the cost shapes.

### 2. Find the N+1 before anything else

The single most common cause of a slow GraphQL query is a resolver on a list field that
loads its own data per item. Count the backend calls a resolver tree makes for one request;
if the number grows with the list length, it is an N+1.

Fix it with a per-request batch loader: collect the keys for a tick, issue one query, and
resolve every pending field from the result. The loader must be created per request, not at
module scope, or one user's keys leak into another's batch. [Resolver batching and
authorization](references/resolver-batching-and-authz.md) has the loader pattern and the
field-level authorization that goes with it.

### 3. Bound what a client can ask for

A schema with cycles and lists is unbounded by default. Apply, in order:

- **Depth limit** — reject documents past a fixed nesting depth. Cheap, stops trivial cyclic
  abuse, does not bound a wide query.
- **Cost or complexity limit** — assign each field a weight and each list a multiplier, sum
  the document, and reject over a budget. This is the one that bounds fan-out.
- **Pagination on every list** — a list field with no `first`/`last` and no cap is a denial
  of service waiting for a large table.
- **Timeouts and a query allowlist** — a server-side deadline per operation, and persisted
  queries so production accepts only operations the clients actually ship.

Turn introspection and the GraphiQL playground off in production; both are reconnaissance for
an attacker and neither is needed by a deployed client.

### 4. Authorize inside the resolver

Field-level authorization belongs in the resolver or a schema directive that runs before it,
never in the client's field selection. Check the caller's identity against the object being
returned, not only against the root field: a `User.orders` resolver must confirm the caller
may see *this* user's orders. A missing resolver check is invisible in the schema and shows
up only as a data leak.

### 5. Evolve without breaking

Add fields and types; never remove or rename one in place. Mark a field `@deprecated` with a
reason, keep it working for the deprecation window, and watch field-usage metrics before
removing it. Changing an argument's type or making an optional input required is a breaking
change even though the schema still validates.

### 6. Report

Lead with the finding: the resolver or the unbounded field, the operation that triggers it,
and the backend calls or rows it costs. Name each fix and whether it is a schema change, a
resolver change or a gateway limit. Label what you observed from the schema and the operation
versus what you inferred from reading code.

## Anti-patterns

**Adding a cache in front of the N+1.** A cache hides the fan-out until the keys are all
distinct, then the stampede returns. Batch the load first; cache the batch if it still helps.

**A depth limit as the only bound.** `{ a { a { a ... } } }` is bounded by depth; a single
list field returning a million rows is not. Cost limits and pagination bound what depth
cannot.

**Authorization on the root field only.** `viewer { ... }` checked once, then `viewer.orders`
and `order.customer.email` resolved with no further check, leaks every nested object the
caller can reach by traversal.

**Trusting the client's field selection to limit data.** The client chooses the fields; the
server must return only fields the caller is entitled to, regardless of what was asked.
