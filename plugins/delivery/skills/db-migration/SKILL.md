---
name: db-migration
description: "Ship a schema change to a live relational database without downtime, a stuck lock, or a deploy that cannot be reverted: expand, backfill in bounded batches, migrate reads, migrate writes, contract — each phase its own independently revertible deploy, every migration session carrying an explicit lock_timeout and a retry loop. Use this skill whenever someone is adding, renaming, dropping or retyping a column, adding an index or a constraint, backfilling a large table, splitting or merging tables, or asking things like \"will this migration lock the table\", \"how do I rename a column with no downtime\", \"the deploy is stuck on the migration\", \"is this migration reversible\", or \"can we drop the old column yet\". Covers PostgreSQL and MySQL/InnoDB, including gh-ost and pt-online-schema-change. Do not use it for choosing a database, ORM or framework setup, tuning a slow query, or building an ETL or data pipeline."
allowed-tools: "Bash(psql:*), Bash(mysql:*), Read, Grep, Glob"
---

# Database Migration

A schema change lands well when it arrives as a sequence of small deploys, each safe to revert on its own, none of which holds a lock long enough for anyone to notice.

The job is hard for two reasons that only appear in production. The first is locking. A migration that runs in 40ms against an empty test database takes an ACCESS EXCLUSIVE lock on a 400M-row table in production, waits behind one long-running `SELECT` — and because a pending exclusive request queues ahead of every lock request that arrives after it, every reader that turns up during that wait also stops. The table is not slow, it is unavailable, and the outage is measured from the moment the migration began waiting, not from the moment it began working. The second is reversibility. The deploy that "worked" is often the one you can no longer roll back, because the new code is writing to a column the old code does not know about, or the old code is selecting a column the migration just dropped. Application and schema have to be compatible in both directions at every instant. That is a property of the release sequence, not of any single migration file.

## Scope

Use for: a schema change against a database that is serving traffic — columns, indexes, constraints, types, table splits — plus the backfill that populates it, the release sequencing around it, and the decision about whether a change can be rolled back.

Do not use for: choosing a database engine, ORM or framework setup, tuning a slow query or adding an index purely for performance analysis, or building an ETL or analytics pipeline. If the migration is one step inside a larger switchover event with a point of no return, the sequencing here still applies but the event belongs to the `cutover` skill.

## Hard gates

Breaking one of these does not slow the migration down, it invalidates the plan.

1. Every migration session sets `lock_timeout`. Without it a blocked DDL statement waits forever and takes the readers behind it down with it.
2. Schema and application code are compatible in both directions at every point in the sequence. If reverting the application would break against the new schema, the phase is not shippable.
3. One phase, one deploy. Expand, backfill, read-switch, write-switch and contract never share a release.
4. Contract is gated on evidence that no code reads or writes the old object — not on the previous deploy having finished.
5. A backfill runs in bounded batches with a commit per batch. A single `UPDATE` over a large table holds one transaction open for hours, bloats the table, and cannot be stopped cleanly.
6. Assume every phase can be interrupted halfway. Backfills are resumable and idempotent because at some point one will be killed at 60%.

## Workflow

### 0. Classify the change and size the table

Before writing SQL, get the two facts that decide everything else: how big the table is, and whether the operation rewrites it.

```sql
SELECT pg_size_pretty(pg_total_relation_size('orders')) AS total,
       (SELECT reltuples::bigint FROM pg_class WHERE relname='orders') AS approx_rows;
```

Under roughly a million rows on a quiet table, most operations are fast enough that the phased sequence is overhead. Above that, or on any table in the request path of a live service, use the full sequence. Check the lock table below for the specific operation before assuming either.

Also check for long-running transactions, because they are what turns a fast lock into an outage:

```sql
SELECT pid, state, now() - xact_start AS age, left(query, 80)
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND now() - xact_start > interval '1 minute'
ORDER BY age DESC;
```

An idle-in-transaction session older than the migration's `lock_timeout` means the migration will fail its first attempt. Fix that first — usually a leaked connection or an open analytics query — rather than raising the timeout.

### 1. Expand

Add the new shape alongside the old one, additively and nullably. Nothing reads it yet and nothing depends on it, so this deploy is trivially revertible.

```sql
ALTER TABLE orders ADD COLUMN customer_ref uuid;          -- instant, metadata only
CREATE INDEX CONCURRENTLY idx_orders_customer_ref ON orders (customer_ref);
```

The application deploy that accompanies expand does nothing new. Keeping schema and code changes in separate releases is what lets you revert one without the other.

### 2. Dual-write, then backfill

Start writing both the old and the new column on every insert and update, in application code, before backfilling. Backfilling first and dual-writing second leaves a gap in which new rows arrive with the new column empty, and the backfill you just finished is already wrong.

Then backfill in batches keyed on the primary key, committed per batch, with a pause between them:

```sql
-- One batch. Driven by a loop that carries the last id forward.
UPDATE orders SET customer_ref = legacy_customer_uuid(customer_id)
WHERE id > :last_id AND id <= :last_id + 5000 AND customer_ref IS NULL;
```

Between batches, sleep and check replica lag. Start at 1000-5000 rows and a 100ms sleep, then tune from observed rows/s and lag rather than from a guess. `references/backfill.md` has the full driver loop, the throttle, and the resume logic — read it before writing the backfill.

### 3. Migrate reads

Switch reads to the new column, behind a flag if the read path matters. Keep writing both. This deploy reverts by flipping the flag back, which is the point: the old column is still current, so the old read path still works.

Watch error rates and a comparison counter — reading both and counting disagreements for a day is cheap and is the only thing that catches a backfill that silently missed a case.

### 4. Migrate writes

Stop writing the old column. From here the old column starts drifting out of date, so this is the deploy where revertibility narrows: reverting is still safe for as long as no rows have been written since, and stops being safe after that. Say that out loud in the PR rather than discovering it during a revert.

### 5. Prove nothing uses the old object

Contract is the one-way phase. Before it, produce evidence, not a belief:

```sql
-- Any statement still touching the column, from pg_stat_statements.
SELECT calls, left(query, 120) FROM pg_stat_statements
WHERE query ILIKE '%customer_id%' AND query NOT ILIKE '%pg_stat%'
ORDER BY calls DESC LIMIT 20;
```

Reset `pg_stat_statements` after the write-switch deploy so the counts cover only the period since. Combine with a grep of the application repository, and with a shadow-read counter — a metric incremented wherever the old column is still read — which is the only source that covers code paths too rare to appear in a statement sample. Add the batch jobs, the reporting replica, and anything with its own copy of the schema.

Bake for days, not minutes. The rare caller is a monthly invoice run.

### 6. Contract

Drop the old object, in its own deploy, as the last step.

```sql
ALTER TABLE orders DROP COLUMN customer_id;
```

This is irreversible in practice. A `down()` migration that re-adds the column restores the schema and not the data; the only real reversal is a restore from backup, and that loses every write since. Treat contract as a one-way door and schedule it deliberately.

## Postgres lock table

What is safe, what is not, and what the safe version is. All of these still take a brief ACCESS EXCLUSIVE lock to update the catalog — safe means the lock is held for microseconds instead of for a full table rewrite.

| Operation | Safe? | Notes |
| --- | --- | --- |
| `ADD COLUMN` nullable, no default | Yes | Metadata only. |
| `ADD COLUMN ... DEFAULT 'x'` (non-volatile) | Yes, PG 11+ | The default is stored in the catalog and applied on read. On PG 10 and older this rewrites the whole table. |
| `ADD COLUMN ... DEFAULT gen_random_uuid()` | No | A volatile default has to be evaluated per row, which is a full rewrite under an exclusive lock. Add the column nullable, then backfill. |
| `CREATE INDEX` | No | Blocks writes for the whole build. Use `CREATE INDEX CONCURRENTLY`. |
| `CREATE INDEX CONCURRENTLY` | Yes | Cannot run inside a transaction, so it needs its own migration file. On failure it leaves an `INVALID` index that must be dropped with `DROP INDEX CONCURRENTLY` and rebuilt — check `pg_index.indisvalid` afterwards. |
| `ADD CONSTRAINT ... CHECK/FOREIGN KEY` | No | Scans the whole table under an exclusive lock. Split it: `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT`, which takes only SHARE UPDATE EXCLUSIVE. |
| `SET NOT NULL` | No, by default | A full scan under an exclusive lock. On PG 12+, add a validated `CHECK (col IS NOT NULL)` first and the `SET NOT NULL` uses it as proof and skips the scan. Drop the redundant check afterwards. |
| `ALTER COLUMN TYPE` | Usually no | Rewrites the table and all its indexes. Widening `varchar(n)` to a larger `n` or to `text` is exempt. Anything else — `int` to `bigint` especially — is an expand/contract on a new column. |
| `DROP COLUMN` | Fast, but not safe | Metadata only, so the lock is short, but any deployed code doing `SELECT *` or an ORM model listing that column starts erroring immediately. |
| `RENAME COLUMN` / `RENAME TABLE` | Fast, but not safe | Instant and atomic in the database, and instantly wrong for every process still using the old name. Use the rename recipe below. |

Set the guards on the migration session, inside the transaction:

```sql
BEGIN;
SET LOCAL lock_timeout = '3s';        -- fail fast rather than queueing readers behind us
SET LOCAL statement_timeout = '30s';  -- bound the work itself
ALTER TABLE orders ADD COLUMN customer_ref uuid;
COMMIT;
```

Then retry the whole transaction, with a pause, rather than raising the timeout — the point is to release the queue between attempts. Six attempts at three seconds costs at most eighteen seconds of contention spread over a minute; one attempt with no timeout can cost an hour of it. `references/postgres-locks.md` has the retry wrapper, the lock conflict matrix, and the queries for finding what is blocking a migration in flight.

## MySQL and InnoDB

The same sequence applies; the mechanics differ. State the algorithm and lock level explicitly so the server rejects the statement instead of silently falling back to a blocking copy:

```sql
ALTER TABLE orders ADD COLUMN customer_ref BINARY(16), ALGORITHM=INSTANT;
ALTER TABLE orders ADD INDEX idx_customer_ref (customer_ref), ALGORITHM=INPLACE, LOCK=NONE;
```

`ALGORITHM=INSTANT` (MySQL 8.0.12+) covers adding a column, and from 8.0.29 adding one in the middle of the row. `ALGORITHM=INPLACE, LOCK=NONE` covers most index work without blocking DML. An `ALTER` that supports neither — many type changes, dropping a primary key, older server versions — needs an external tool: `gh-ost` copies the table by reading the binlog, so it adds no triggers and can be throttled and paused mid-run; `pt-online-schema-change` uses triggers, which is more intrusive on write-heavy tables but works where binlog access does not. Either way the cut is a table rename at the end, and it is still a schema change: sequence the application deploys around it exactly as above.

## Worked example: renaming a column with no downtime

Renaming `orders.customer_id` to `orders.customer_ref` is five deploys, not one.

1. **Expand.** `ADD COLUMN customer_ref` nullable. Create any index `CONCURRENTLY`. No application change.
2. **Dual-write.** Application writes both columns on every insert and update. Reads still use `customer_id`. Revertible.
3. **Backfill.** Batched, throttled, resumable, until `customer_ref IS NULL AND customer_id IS NOT NULL` returns zero. Add the `NOT NULL` via a validated `CHECK` if the column needs one.
4. **Read switch.** Reads move to `customer_ref`, behind a flag. Bake. Compare and count disagreements.
5. **Stop dual-writing**, then bake for days while step 5 of the workflow collects evidence. Only then `DROP COLUMN customer_id`.

The bake period is the part people cut, and it is the part that catches the quarterly job.

## Failure signals during a migration

| Signal | Class | Action |
| --- | --- | --- |
| Migration statement pending; `pg_stat_activity` shows it waiting and a growing queue of `ACCESS SHARE` waiters behind it | Lock queue | Cancel the migration immediately — `pg_cancel_backend(pid)` — which releases the queue. Find and end the blocking transaction, then retry with `lock_timeout`. |
| Replica lag climbing during a backfill | Batch too large or too fast | Pause the backfill, let lag drain, halve the batch size and raise the sleep. Lag is the throttle signal, not rows/s. |
| Disk usage climbing fast, table size doubling | Table rewrite in progress | A rewrite needs room for a full second copy plus WAL. Either it completes and you reclaim, or you run out of disk mid-rewrite and take an outage. Cancel now if headroom is under 2x the table. |
| `deadlock detected` between the migration and application traffic | Lock-order conflict | Retry the batch — deadlocks are expected under concurrent write load. If it repeats, order the batch by primary key so the migration and the application take row locks in the same order. |
| `ERROR: canceling statement due to lock timeout` | Working as designed | This is the guard doing its job. Retry with backoff; investigate only if every attempt fails, which means a persistent long transaction. |
| Backfill finished but rows still `NULL` | Rows arriving faster than the backfill, or a missed write path | Dual-write is incomplete. Find the write path that skips the new column before re-running. |
| Index shows `indisvalid = false` after `CREATE INDEX CONCURRENTLY` | Failed concurrent build | Drop it with `DROP INDEX CONCURRENTLY` and rebuild. An invalid index is maintained on write but never used for reads, so it is pure cost. |

## Output format

Report a migration plan in this shape, one row per deploy:

```markdown
## Change
[What is changing, on which table, and its size in rows and bytes.]

## Lock analysis
[Each DDL statement, the lock it takes, for how long, and why that is acceptable.]

## Sequence
| # | Phase | Schema change | Application change | Revertible by |
|---|-------|---------------|--------------------|---------------|

## Backfill
[Batch size, sleep, throttle signal, expected duration, how to resume.]

## Contract gate
[The evidence required before the one-way step, and the bake period.]

## Rollback
[Per phase. Name explicitly the phase after which rollback stops being possible.]
```

## Anti-patterns

**Migration inside the application deploy transaction.** Couples a schema change to a code change, so the revert has to undo both at once and there is no ordering in which both are correct. It also means a slow migration blocks the deploy and, on some platforms, times out halfway through with the schema half changed.

**The `down()` that has never been run.** Reversibility is a property you have tested, not one the framework grants by generating a method. An untested `down()` on a table with real data is a guess, and it is being run for the first time during an incident.

**Backfill in one statement.** One `UPDATE` over 400M rows holds a transaction open for hours, blocks vacuum, bloats the table, replicates as one enormous chunk, and cannot be stopped without losing all of it. Batches with per-batch commits cost slightly more total time and can be paused at any moment.

**Dropping the column in the same release that stops using it.** The window between the two is what makes rollback possible. Dropped together, the moment the deploy has to be reverted the old code comes back up against a schema that no longer has the column, and a code rollback becomes a database restore.

**Adding a column with a volatile default.** Reads as a one-line migration and behaves as a full table rewrite under an exclusive lock. Add nullable, backfill, then set the default.

**Raising `lock_timeout` because the migration keeps failing.** The failures are the guard telling you a long transaction is in the way. Raising the timeout converts fast failures into a queue of blocked readers, which is the outage the timeout existed to prevent.

**Trusting the test database's timing.** Every operation is fast on 10,000 rows. Size the table, then look up the operation, and if neither is possible, run it against a restored production-sized copy first.

**Treating a rename as a rename.** The database renames instantly; the fleet does not. Every process still running the old code breaks at the moment of commit, including the ones nobody remembered are running.

## Reference files

- `references/postgres-locks.md` — read before running any DDL against a live Postgres table: the lock conflict matrix, the queue behaviour, per-operation safety, the retry wrapper, and the queries that identify what is blocking a migration.
- `references/backfill.md` — read when writing the backfill: the batch driver loop, throttling on replica lag, resumable checkpoints, idempotency, and how to verify the backfill is complete.
