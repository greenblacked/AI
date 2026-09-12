# Postgres locking for schema changes

Which lock each operation takes, what that lock blocks, why a pending exclusive lock is
worse than a slow one, and the queries that tell you what is in the way. Load this before
running DDL against a table that is serving traffic.

## Contents

- [The queue is the problem, not the lock](#the-queue-is-the-problem-not-the-lock)
- [Lock conflict matrix](#lock-conflict-matrix)
- [Operation to lock mode](#operation-to-lock-mode)
- [Session guards and the retry wrapper](#session-guards-and-the-retry-wrapper)
- [Finding what is blocking a migration](#finding-what-is-blocking-a-migration)
- [Safe recipes for the operations that are not safe by default](#safe-recipes-for-the-operations-that-are-not-safe-by-default)
- [CREATE INDEX CONCURRENTLY failure modes](#create-index-concurrently-failure-modes)

## The queue is the problem, not the lock

Postgres grants table locks in request order. A statement that wants ACCESS EXCLUSIVE and
cannot have it goes into the queue, and every lock request arriving afterwards queues
behind it — including the ACCESS SHARE that an ordinary `SELECT` needs.

So the sequence that takes a service down is not "the migration was slow". It is:

1. A reporting query has been running for four minutes, holding ACCESS SHARE.
2. `ALTER TABLE` requests ACCESS EXCLUSIVE, conflicts, and waits.
3. Every subsequent query on that table — including one-millisecond primary-key lookups —
   queues behind the `ALTER`.
4. Connections pile up, the pool exhausts, and the failure spreads to endpoints that never
   touch this table.

The migration itself might have taken 2ms. The outage lasted as long as the reporting
query, plus however long it took someone to work out what was happening. This is why
`lock_timeout` is not optional: it bounds step 3 to a few seconds.

## Lock conflict matrix

The four modes that matter for schema work, and what each blocks:

| Mode | Taken by | Conflicts with |
| --- | --- | --- |
| ACCESS SHARE | `SELECT` | ACCESS EXCLUSIVE only |
| ROW EXCLUSIVE | `INSERT`, `UPDATE`, `DELETE` | SHARE, SHARE ROW EXCLUSIVE, EXCLUSIVE, ACCESS EXCLUSIVE |
| SHARE UPDATE EXCLUSIVE | `VACUUM`, `CREATE INDEX CONCURRENTLY`, `VALIDATE CONSTRAINT`, `ALTER TABLE ... SET STATISTICS` | itself, SHARE, SHARE ROW EXCLUSIVE, EXCLUSIVE, ACCESS EXCLUSIVE |
| ACCESS EXCLUSIVE | most `ALTER TABLE`, `DROP`, `TRUNCATE`, `REINDEX`, plain `CREATE INDEX` (SHARE, which blocks writes but not reads) | everything, including plain `SELECT` |

SHARE UPDATE EXCLUSIVE is the mode to aim for: it permits concurrent reads and writes and
only conflicts with other maintenance. It does block autovacuum on that table for its
duration, which matters for a validation that runs for hours.

## Operation to lock mode

| Statement | Lock | Duration | Rewrite? |
| --- | --- | --- | --- |
| `ADD COLUMN` nullable, no default | ACCESS EXCLUSIVE | microseconds | no |
| `ADD COLUMN` with a constant default (PG 11+) | ACCESS EXCLUSIVE | microseconds | no |
| `ADD COLUMN` with a volatile default | ACCESS EXCLUSIVE | full rewrite | yes |
| `DROP COLUMN` | ACCESS EXCLUSIVE | microseconds | no, space reclaimed by vacuum |
| `RENAME COLUMN` / `RENAME TABLE` | ACCESS EXCLUSIVE | microseconds | no |
| `ALTER COLUMN TYPE` (widening varchar, or to text) | ACCESS EXCLUSIVE | microseconds | no |
| `ALTER COLUMN TYPE` (anything else) | ACCESS EXCLUSIVE | full rewrite plus index rebuilds | yes |
| `SET NOT NULL` without a proving check | ACCESS EXCLUSIVE | full scan | no |
| `SET NOT NULL` with a validated `CHECK` (PG 12+) | ACCESS EXCLUSIVE | microseconds | no |
| `SET DEFAULT` / `DROP DEFAULT` | ACCESS EXCLUSIVE | microseconds | no |
| `CREATE INDEX` | SHARE | full build, writes blocked | n/a |
| `CREATE INDEX CONCURRENTLY` | SHARE UPDATE EXCLUSIVE | two full passes | n/a |
| `ADD CONSTRAINT ... NOT VALID` | ACCESS EXCLUSIVE (plus SHARE ROW EXCLUSIVE on the referenced table for a foreign key) | microseconds | no |
| `VALIDATE CONSTRAINT` | SHARE UPDATE EXCLUSIVE | full scan | no |
| `ADD CONSTRAINT` validating immediately | ACCESS EXCLUSIVE | full scan | no |
| `ADD PRIMARY KEY USING INDEX` | ACCESS EXCLUSIVE | microseconds | no |
| `CLUSTER`, `VACUUM FULL`, `REINDEX` (non-concurrent) | ACCESS EXCLUSIVE | full rewrite | yes |

A single `ALTER TABLE` with several sub-commands takes one lock for all of them, which is
useful: batching four fast metadata changes into one statement costs one short lock rather
than four. Never batch a fast change with a rewriting one — the whole statement inherits
the rewrite's duration.

## Session guards and the retry wrapper

Set the guards inside the transaction, so they apply to the DDL and revert with it:

```sql
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
ALTER TABLE orders ADD COLUMN customer_ref uuid;
COMMIT;
```

`lock_timeout` bounds how long the statement waits *to acquire* the lock — the queueing
window. `statement_timeout` bounds how long it runs once it has one. A migration wants
both, and they are different numbers: three seconds of waiting is generous, thirty seconds
of work may not be.

Retry the whole transaction rather than raising the timeout. The pause between attempts is
what drains the queue that built up during the failed attempt:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

attempt=0
until psql -v ON_ERROR_STOP=1 -f migration.sql; do
  attempt=$(( attempt + 1 ))
  if (( attempt >= 6 )); then
    echo "migration did not acquire its lock in 6 attempts; a long transaction is in the way" >&2
    exit 1
  fi
  sleep $(( attempt * 10 ))
done
```

Exhausting the retries is a finding, not a reason to raise the timeout: something holds a
transaction open for longer than the whole retry budget, and that something will still be
there next time.

Tools that manage this for you are worth adopting rather than reimplementing: `pgroll` and
`reshape` run expand/contract with versioned views, and `squawk` and `eugene` lint
migration SQL for exactly the operations in the table above. A linter in CI catches the
volatile default before review does.

## Finding what is blocking a migration

While the migration is waiting:

```sql
SELECT a.pid,
       a.state,
       now() - a.xact_start          AS xact_age,
       now() - a.query_start         AS query_age,
       a.wait_event_type, a.wait_event,
       left(a.query, 100)            AS query
FROM pg_stat_activity a
WHERE a.datname = current_database() AND a.pid <> pg_backend_pid()
ORDER BY xact_age DESC NULLS LAST;
```

The direct blocking relationship, PG 9.6+:

```sql
SELECT pid, pg_blocking_pids(pid) AS blocked_by, left(query, 80)
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

To clear it, prefer cancelling the migration over cancelling production traffic:

```sql
SELECT pg_cancel_backend(<pid>);     -- cancel the current statement, transaction survives
SELECT pg_terminate_backend(<pid>);  -- kill the connection; the client sees a dropped socket
```

Cancelling the waiting DDL releases the entire queue immediately, which is the fastest way
to end the incident. Then deal with the long transaction: an `idle in transaction` session
is nearly always an application bug — a connection checked out and never committed — and
`idle_in_transaction_session_timeout` prevents the class rather than the instance.

## Safe recipes for the operations that are not safe by default

**Adding a NOT NULL column with a default.** Three statements, none of which scans:

```sql
ALTER TABLE orders ADD COLUMN status text;                    -- nullable
-- backfill in batches, then:
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending';
ALTER TABLE orders ADD CONSTRAINT status_not_null CHECK (status IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT status_not_null;       -- SHARE UPDATE EXCLUSIVE
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;          -- uses the check, no scan
ALTER TABLE orders DROP CONSTRAINT status_not_null;
```

**Adding a foreign key.**

```sql
ALTER TABLE orders ADD CONSTRAINT orders_customer_fk
  FOREIGN KEY (customer_ref) REFERENCES customers (ref) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT orders_customer_fk;
```

`NOT VALID` enforces the constraint for new and updated rows immediately; the validation
pass only covers the rows already there.

**Adding a unique constraint.** Build the index concurrently, then adopt it, so the
constraint creation is a catalog update rather than a build:

```sql
CREATE UNIQUE INDEX CONCURRENTLY orders_ref_uniq ON orders (customer_ref);
ALTER TABLE orders ADD CONSTRAINT orders_ref_uniq UNIQUE USING INDEX orders_ref_uniq;
```

**Changing a column type.** There is no safe in-place version for a narrowing or
representation-changing conversion. It is an expand/contract on a new column: add, dual
write, backfill, switch reads, switch writes, drop.

## CREATE INDEX CONCURRENTLY failure modes

- It cannot run inside a transaction block, so it needs its own migration file, and most
  frameworks need to be told to disable their automatic transaction wrapper for that file.
- It makes two passes over the table and waits for all transactions older than each pass
  to finish. One long-running transaction elsewhere in the database stalls it, even on an
  unrelated table.
- On failure it leaves an invalid index behind, which is maintained on every write and used
  by no read. Find them and rebuild:

```sql
SELECT i.indexrelid::regclass AS index, i.indrelid::regclass AS table
FROM pg_index i WHERE NOT i.indisvalid;
```

```sql
DROP INDEX CONCURRENTLY orders_ref_uniq;
```

- It is slower and does more I/O than a plain build. On a replica-served read workload,
  watch replica lag while it runs, the same as for a backfill.
