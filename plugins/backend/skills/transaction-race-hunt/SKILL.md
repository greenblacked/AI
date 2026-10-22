---
name: transaction-race-hunt
description: "Find and fix check-then-act races in code that talks to a relational database. Name the anomaly first (lost update, write skew, check-then-insert phantom, double claim of work), establish the isolation level in force, then take the weakest fix that closes it: a constraint, one atomic conditional statement, an optimistic version column, SELECT FOR UPDATE in a global order with SKIP LOCKED for job claiming, or SERIALIZABLE with a retry on SQLSTATE 40001. Reproduce with a deterministic two-session interleaving, not a load test. Use whenever someone says \"two requests booked the same seat\", \"balance went negative\", \"duplicate rows even though we check first\" or \"inventory oversold\". Not for slow queries (sql-performance), general fault isolation (debugging), locks across processes (distributed-lock-audit), choosing constraints for a new model (schema-design), diagnosing a deadlock from the database log (deadlock-analysis)."
allowed-tools: Read, Grep, Glob, Edit
---

# Transaction Race Hunt

Done means the anomaly has a name, a deterministic test reproduces it before the fix and passes after, and the fix is the weakest mechanism that closes it. The usual failure is reaching for a lock or a bigger isolation level before knowing which anomaly is happening, which adds contention and deadlocks without closing the actual gap.

## 1. Name the anomaly

Read the code path and classify it. The class decides the fix.

| Anomaly | Shape | Example |
| --- | --- | --- |
| Lost update | Read a value, compute in the application, write it back | Balance read, 10 subtracted, written; two requests both read 100 |
| Write skew | Two transactions read an overlapping set and write different rows; the invariant spans both | Two doctors both see two on call and both go off call |
| Check-then-insert phantom | Query for absence, then insert | "No booking for that seat" then insert; both pass the check |
| Double claim | Two workers select the same pending job | Both mark job 7 as running |

If you cannot say which one it is, you cannot yet say whether a given fix closes it.

## 2. Establish the isolation level in force

Do not assume. Ask the database and the driver.

- PostgreSQL defaults to READ COMMITTED: `SHOW transaction_isolation;`. Every statement sees newly committed rows, so read-modify-write loses updates.
- MySQL InnoDB defaults to REPEATABLE READ: `SELECT @@transaction_isolation;`. A plain read uses a snapshot, but an UPDATE reads the latest row, and read-modify-write code that selects then updates from the application still loses updates.
- Check what the ORM or pool sets per connection or per transaction, and whether the code is in a transaction at all (autocommit makes the read and the write separate transactions).

## 3. Take the weakest fix that closes it

Work down this list and stop at the first that works.

1. **Make the invariant a constraint.** A unique index for "one booking per seat", a CHECK for `balance >= 0`, an `EXCLUDE USING gist` constraint for overlapping time ranges in PostgreSQL. The database enforces it for every writer, including ones you forgot about. Handle the violation as a normal outcome.
2. **One atomic statement.** `UPDATE stock SET qty = qty - 1 WHERE id = $1 AND qty >= 1` and test the affected row count; zero means the condition failed. For insert-if-absent use `INSERT ... ON CONFLICT DO NOTHING` (PostgreSQL) or `INSERT IGNORE` / `ON DUPLICATE KEY UPDATE` (MySQL) and read the affected count.
3. **Optimistic version.** Add a `version` column; `UPDATE ... SET ..., version = version + 1 WHERE id = $1 AND version = $2`; zero rows means someone else won, so re-read and retry or surface a conflict.
4. **Pessimistic lock.** `SELECT ... FOR UPDATE` on the rows the decision depends on. Always take locks in one global order (for example ascending id) to avoid deadlocks. For job claiming use `FOR UPDATE SKIP LOCKED` so workers pass over rows already taken instead of queueing behind them.
5. **SERIALIZABLE with retry.** For write skew spanning rows that no single constraint or lock covers cleanly. Wrap the whole transaction in a retry loop on SQLSTATE `40001` (serialisation failure) and `40P01` (deadlock detected). The retry re-runs the entire transaction from the reads.

Write skew is the case where steps 2 to 4 often do not help on their own, because the two transactions touch different rows; either lock a shared row that represents the invariant, express it as a constraint, or use step 5.

## 4. Reproduce with a deterministic interleaving

A load test finds races by luck and proves nothing when it passes. Instead, open two sessions and pause both between the read and the write, using a barrier in the test or a PostgreSQL advisory lock (`pg_advisory_lock`) held by the test harness, then release them together. The failure appears every run.

That interleaving becomes the regression test: it fails on the original code, passes on the fixed code, and stays in the suite. Read `references/interleavings.md` for session scripts per anomaly and the test skeleton.

## 5. Constrain the retry and the transaction

- A retry re-reads. It must not repeat external side effects (emails, charges, published events) that happened inside the failed attempt; move those after commit or key them with an idempotency key.
- Keep transactions short. No network calls, no user waits and no slow queries inside; the longer the transaction, the wider the race window and the more lock waiting.
- Bound retries and add jitter so a hot row does not turn into a retry storm.

## Verify

- The interleaving test fails before the fix and passes after.
- The constraint or conditional update is present in the migration, not only in application code.
- Run the test at the isolation level production uses.
- Deadlock handling: two transactions locking the same rows in opposite order no longer deadlock, or the retry handles `40P01`.

## Hand back

The anomaly name, the isolation level observed and how you read it, the fix and why a weaker one was not enough, the migration if any, the interleaving test, and what the retry does about side effects.

## Anti-patterns

**Check in code, insert in code.** `if not exists(...) then insert` is a race under every isolation level below serializable. A unique constraint is the simplest closer; SERIALIZABLE with a retry, or a lock on a parent row, also closes it.

**SELECT FOR UPDATE on rows that do not exist yet.** In PostgreSQL it locks nothing for a phantom; in InnoDB under REPEATABLE READ the gap lock does block the insert but tends to cause deadlocks. Prefer a unique constraint, or lock a parent row.

**Raising the isolation level everywhere.** It trades one rare wrong answer for constant serialisation failures; apply it to the transactions that need it, with the retry loop.
