# Lock options compared

Contents: what each service provides, fencing sources, release patterns.

## What each provides

| Mechanism | Fencing token available | Fit |
| --- | --- | --- |
| Single-node Redis `SET NX PX` | No | Efficiency only |
| Redlock across several Redis nodes | No monotonic token; depends on bounded clock drift | Not for correctness |
| Postgres `pg_advisory_xact_lock` / `pg_try_advisory_xact_lock` | Not a token, but released when the transaction ends, so it cannot outlive the work it guards | Correctness for work inside one database |
| Postgres session advisory lock | No; tied to the connection | Efficiency; breaks under transaction-mode pgbouncer |
| etcd lease and lock | Key revision serves as a token | Correctness with checks at the resource |
| ZooKeeper ephemeral sequential node | zxid or sequence number | Correctness with checks at the resource |
| Consul session lock | Lock index on the key | Correctness with checks at the resource; session TTL still applies |
| Kubernetes `Lease` | Resource version and transition counter, usable as a guard | Leader election for controllers |

## Release pattern for Redis

Store a random value per acquisition. Release only if the stored value still equals yours, in one atomic script: if the value matches, delete; otherwise do nothing. The same compare applies when extending the TTL.

## Where the fencing check lives

The check has to be in the system that performs the final write, because that is the only place that sees both tokens. Options: a `fence` column compared in the `WHERE` clause of the update; a conditional put in object storage using an `If-Match` precondition on a version; a per-record version in a key-value store. If the final resource cannot compare tokens (an external API, an email), the lock cannot make that effect safe; make the effect idempotent with a key instead.
