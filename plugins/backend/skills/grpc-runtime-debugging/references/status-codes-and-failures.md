# Status codes and failures

Read this first: the code is the classification, and the layer that produced it decides where
to look. The codes are the canonical gRPC set (`google.rpc.Code`); a proxy may rewrite one, so
confirm against the server's own logs.

| Code | Number | Usual layer | First check |
| --- | --- | --- | --- |
| `OK` | 0 | — | If the client saw an error but the server returned OK, look at the client or a proxy |
| `CANCELLED` | 1 | caller | The caller cancelled or the deadline fired on the caller's side; check for a context cancelled upstream |
| `UNKNOWN` | 2 | server | An unhandled error on the server; the server log holds the real exception |
| `INVALID_ARGUMENT` | 3 | request | The request is malformed; not a transport problem |
| `DEADLINE_EXCEEDED` | 4 | either | The deadline fired. Which side? Compare the deadline value at each hop |
| `NOT_FOUND` | 5 | server | Application-level; the entity is absent |
| `ALREADY_EXISTS` | 6 | server | Application-level; a uniqueness conflict |
| `PERMISSION_DENIED` | 7 | server | Application-level; the caller may not do this |
| `RESOURCE_EXHAUSTED` | 8 | either | Flow control, a quota, or a full queue — check the window and the message size |
| `FAILED_PRECONDITION` | 9 | server | State the system is not in, not the request's shape |
| `ABORTED` | 10 | server | A concurrency conflict (compare-and-swap failed) |
| `OUT_OF_RANGE` | 11 | request | An argument past a valid range, e.g. a seek past end |
| `UNIMPLEMENTED` | 12 | server | The method is not served — wrong path, wrong server, or a version skew |
| `INTERNAL` | 13 | server | An invariant was broken; the server log holds the cause |
| `UNAVAILABLE` | 14 | transport | The connection class — see below |
| `DATA_LOSS` | 15 | either | Unrecoverable corruption; treat as a bug, not a transient |
| `UNAUTHENTICATED` | 16 | server | Missing or invalid credentials |

## `UNAVAILABLE` is the one to read carefully

The message distinguishes the causes, and each has a different fix:

- **connection refused / connect failed** — nothing is listening; wrong address or the server
  is down.
- **no healthy upstream / no ready endpoints** — the load balancer has no backend that passes
  its health check; look at readiness, not the client.
- **connection closed / transport is closing** — often a `GOAWAY` from a draining server, or an
  idle-timeout on a proxy closing a connection the client still holds.
- **the connection is draining** — a graceful shutdown in progress; the client should move to
  another backend, which needs a resolver and a balancing policy that can.

A client with one channel and `pick_first` cannot move; that is a configuration finding, not a
retry finding.

## The details trailer

A well-behaved server attaches a `google.rpc.Status` to the trailer
(`grpc-status-details-bin`) with a code, a message and typed details. Read it with a client
that surfaces trailers (`grpcurl -v`), because the summary message can be generic while the
details name the field or the retry hint.

## What the code cannot tell you

The code classifies the failure, not its cause. `DEADLINE_EXCEEDED` says a deadline fired; it
does not say whether the deadline was too short or the server was slow, and those are opposite
fixes. Record which you observed (a slow server span) and which you assumed.
