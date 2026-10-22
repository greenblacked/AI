---
name: distributed-lock-audit
description: "Review every lock, lease and leader election in a service. For each, decide whether it exists for efficiency (a duplicate only wastes work) or correctness (a duplicate corrupts data); a TTL lock alone never protects correctness because a holder can pause past its lease and still write, so the resource must reject stale holders with a fencing token, or the lock should be replaced by a constraint or compare-and-swap. Covers Redis SET NX, Redlock, etcd, ZooKeeper, Consul, Kubernetes Lease and Postgres advisory locks. Use when you hear \"is Redlock safe\", \"two pods ran the job at once\", \"the lock expired while the holder was still writing\", \"use a Redis lock to stop double processing\", \"leader election with etcd\". Not for cache-fill leases (application-caching), anomalies inside one database (transaction-race-hunt), delivery duplicates (event-driven-reliability)."
allowed-tools: Read, Glob, Grep, Edit
---

# Distributed Lock Audit

Done means every lock in the service is listed with its purpose, each correctness lock is backed by a fencing token or replaced by a data-level guard, each efficiency lock is knowingly best-effort, and a pause test shows a stale holder's write being rejected. The usual failure is a Redis lock with a 30 second TTL guarding a write that can take longer than 30 seconds some day: the lease expires, a second instance enters, the first wakes up and both write.

## 1. Inventory

Search for every place the service takes mutual exclusion: `SET ... NX`, `SETNX`, Redlock client libraries, `pg_advisory_lock` and `pg_try_advisory_lock`, `SELECT ... FOR UPDATE` used as a cross-process lock, etcd or ZooKeeper clients, Consul sessions, Kubernetes `Lease` objects, leader-election libraries, file locks on shared storage. Record for each: what it protects, the TTL or session timeout, how it is released, and what happens to the holder when it loses the lock.

## 2. Efficiency or correctness

Ask one question per lock: if two holders ran at once, would the result be wasted work or wrong data?

- **Efficiency** (duplicate email digest computation, double cache warm): a duplicate costs money or time and nothing else. A best-effort lock is enough.
- **Correctness** (double charge, two writers on one record, two leaders both assigning work): a duplicate corrupts data. The lock alone is not enough.

Write the answer next to each lock in the inventory. Most audits find correctness locks that were built as efficiency locks.

## 3. Efficiency locks

Single-node Redis is acceptable: `SET key <unique-value> NX PX <ttl>`. Release with compare-and-delete in a Lua script, so a holder whose lease expired cannot delete the next holder's lock. Never release with a plain `DEL`. Accept that a failover or an expiry will occasionally let two through.

## 4. Correctness locks

No TTL-based lock is sufficient on its own. A holder can pause past its lease (garbage collection, VM freeze, SIGSTOP, a slow network round trip) and then write, believing it still holds the lock. The fix is at the resource, not the lock:

- Take a monotonically increasing **fencing token** with the lock: an etcd revision, a ZooKeeper zxid or czxid, or a sequence from the lock service.
- Pass the token with every write and make the protected resource reject any token lower than the highest it has seen, for example `UPDATE accounts SET balance = $1, fence = $2 WHERE id = $3 AND fence <= $2`, so the current holder's repeated writes (equal token) pass and lower tokens are rejected. Check the affected row count: zero rows means a stale holder.
- Redlock has no monotonic token and relies on bounded clock drift and pause times, so it is not a correctness lock. Do not use it as one.

Read `references/lock-options.md` for what each lock service can and cannot provide.

## 5. Better: remove the lock

Prefer, in this order:

1. A unique constraint, conditional write or compare-and-swap on a version column in the data store itself. No lease, no clock, no pause problem.
2. A database lock inside a transaction. `pg_try_advisory_xact_lock` is released when the transaction ends, so it cannot outlive its connection.
3. A consensus-backed lease with fencing (etcd, ZooKeeper, Consul, Kubernetes Lease).
4. Single-node Redis, for efficiency only.

Session-level advisory locks (`pg_advisory_lock`) belong to the connection, not the caller; behind pgbouncer in transaction pooling mode the next statement may run on a different server connection, so the lock is held by someone else or never released. Use the transaction-scoped form or a session-pooled connection.

## 6. Lease numbers

- TTL above the worst observed pause plus clock drift, measured from real GC and latency data rather than guessed.
- Renew at about one third of the TTL, so two renewals can fail before the lease is lost.
- When renewal fails, the holder stops side effects immediately and aborts, not finishes the batch.
- Check the remaining lease before each externally visible effect, not once at the start.

## 7. Leader election

A leader is a lock with a long lease, so the same rules apply. Anything the leader does that must not be done twice needs fencing at the target. Followers must expect leadership to change between any two statements. A Kubernetes `Lease` or an etcd election is acceptable; a Redis key is not for correctness.

## 8. Gate: pause the holder

Start two instances. Take the lock in instance A and begin a write loop. Send `SIGSTOP` to A for longer than the TTL, let B acquire and write, send `SIGCONT` to A, and let it attempt its stale write. Assert the resource rejects it and the final data matches B's writes only. A lock that passes only when nothing ever pauses has not been tested.

## Hand back

The inventory table (lock, purpose, efficiency or correctness, TTL, release method, stale-holder behaviour), which locks were replaced and by what, the fencing check at each correctness resource, the lease numbers with the measurements behind them, and the pause test result.

## Anti-patterns

**Plain DEL to release.** It deletes someone else's lock after your lease expired.

**Redlock for correctness.** No token, and it assumes bounded clock drift and pauses.

**Checking the lock once at the start of a long job.** The lease can end before the job does.

**Session-level advisory locks behind a transaction pooler.** The lock and the caller are on different connections.
