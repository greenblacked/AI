# Query cost and limits

Read this when you need the introspection query, the shapes that make a document expensive,
or a concrete cost rule. Every weight here is a starting point; the real number comes from
your own tail latency, not from this page.

## Getting the schema

Introspection is a normal query. Against an endpoint you are authorised to query:

```graphql
{
  __schema {
    queryType { name }
    mutationType { name }
    types { name kind fields { name args { name } type { name kind ofType { name kind } } } }
  }
}
```

Send it as the `query` field of a JSON body. A server that has introspection disabled returns
an error naming that fact — record it and read the SDL from the repository instead. Do not
retry against a third party's production endpoint without asking.

## The shapes that cost the most

| Shape | Why it explodes | Bound it with |
| --- | --- | --- |
| List of objects with a per-item resolver | One backend call per item (N+1) | A batch loader |
| A list with no pagination argument | Returns the whole table | `first`/`last` with a maximum |
| A cyclic type (`User.friends: [User]`) | Depth is unbounded by the type graph | A depth limit |
| Aliases repeating one field | `a: user(id:1) b: user(id:2) …` bypasses a naive per-field cap | A cost limit summed over aliases |
| Deeply nested `filter`/`where` input | An unbounded input tree becomes an unbounded query | A validated, bounded input type |
| `__typename` and introspection in production | Schema reconnaissance | Disable introspection |

## A cost rule you can implement

Assign a cost to a field and multiply down the tree:

- a scalar field costs 1;
- an object field costs its own cost plus the sum of its selected children;
- a list field costs its child cost times the requested `first`, or times a default when
  `first` is absent, and `first` is capped before the multiply.

Sum over the whole document, including aliases, and reject above a per-operation budget.
Return the computed cost in the error so a client can fix its query rather than guess.

This is the rule Apollo, graphql-cost-analysis and similar libraries implement; the important
part is not the library but that list multipliers and aliases are both counted, because a
depth limit alone counts neither.

## Persisted queries and the allowlist

In production, accept only operations the clients actually ship:

1. Each client build registers its operation hashes at deploy time.
2. The gateway accepts a hash and rejects an unknown one.
3. The full document is sent only on the first use or in development.

This turns "any document a client can construct" into "the documents we shipped", which is a
stronger bound than any cost rule, and it makes the cost budget a backstop rather than the
only defence.

## Timeouts

Give each operation a server-side deadline and cancel the resolvers when it fires; a resolver
that keeps running after the response is gone holds a connection and a database slot. The
deadline is the last line, not the first: a query that only passes because it is fast enough
today fails the moment the data grows.

## What the schema cannot tell you

A `@deprecated` directive says the author intended removal, not that no client uses the field.
Field-usage telemetry, not the schema, decides when removal is safe. Record which of the two
you used.
