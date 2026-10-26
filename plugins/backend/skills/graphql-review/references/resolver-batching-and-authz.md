# Resolver batching and authorization

Read this when the finding is an N+1 resolver or a field readable through the graph that
should not be. The two travel together because both are resolved per field, per item.

## The N+1, concretely

```graphql
{ posts(first: 50) { id title author { name } } }
```

A `Post.author` resolver that calls `db.getUser(post.authorId)` runs fifty times for one
document. Fifty calls is survivable; a thousand posts is a thousand round trips, and the
latency is the sum of them, not the maximum.

## The batch loader

Collect the keys requested in one execution tick, then resolve them together:

1. The resolver calls `loader.load(post.authorId)` and returns a promise.
2. The loader queues the key, and on the next tick (or the end of the tick) issues **one**
   query for every queued key: `SELECT * FROM users WHERE id = ANY($1)`.
3. Each pending promise resolves from the result map.

The properties that matter:

- **One loader per request.** A module-scope loader shares keys across users and can return
  one tenant's row to another. Put it in the per-request context.
- **Stable key order.** Build the result map by key, not by row order; a query with `IN` does
  not promise order.
- **A miss is data.** A key with no row resolves to null, not to a rejected promise, unless
  the field is non-null — then it is an error for that item.
- **Batch size cap.** Split a very large key set into chunks so one document cannot issue a
  single query with a hundred thousand parameters.

DataLoader (JavaScript), `graphql-batch` (Ruby), Graphene's `DataLoader` (Python) and
`dataloaden` (Go) implement exactly this. The pattern, not the library, is the point.

## Field-level authorization

Authorization runs per field and per object. The check is not "may this caller use the graph"
but "may this caller see this value":

- **At the object.** `Order.customer` returns a customer only if the caller may see that
  customer. The check uses the resolved object's owner, not the query's root.
- **At the field.** `User.email` is a separate check from `User.name`; a private field returns
  null (or an error) for a caller who may not see it.
- **Before the resolver's side effect.** For a mutation, authorize before any write, not after.

A schema directive (`@auth(requires: OWNER)`) that the server executes before the resolver is
equivalent and keeps the check out of each resolver body; a check in the client's field
selection is not a check at all.

## The leak to look for

```graphql
{ node(id: "someone-elses-id") { ... on User { email } } }
```

A global `node`/`id` field that resolves any object by id is the common leak: the root check
passes, and the nested field returns another user's data because no per-object check ran. Read
every resolver that takes an id argument and confirm it re-checks ownership against the
authenticated caller.

## What this cannot prove

A schema and its resolvers show what the server *will* return for a selection. Whether a
particular caller is entitled to a particular row depends on the policy source — a role table,
a claims token, a relationship — which is `authorization-design`'s subject. Record which
policy you read and which you assumed.
