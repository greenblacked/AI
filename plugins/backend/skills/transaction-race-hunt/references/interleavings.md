# Interleavings

Read this when writing the reproduction for a suspected race: it has a session script per anomaly and a test skeleton.

## Session scripts (PostgreSQL, READ COMMITTED)

Run each line in the session shown; the order of lines is the interleaving.

### Lost update

```text
A: BEGIN;
B: BEGIN;
A: SELECT qty FROM stock WHERE id = 1;      -- 100
B: SELECT qty FROM stock WHERE id = 1;      -- 100
A: UPDATE stock SET qty = 99 WHERE id = 1;
A: COMMIT;
B: UPDATE stock SET qty = 99 WHERE id = 1;  -- should be 98
B: COMMIT;
```

Fix check: with `SET qty = qty - 1` both subtractions apply; the final value is 98.

### Check-then-insert

```text
A: BEGIN;  B: BEGIN;
A: SELECT 1 FROM booking WHERE seat = 12;   -- no row
B: SELECT 1 FROM booking WHERE seat = 12;   -- no row
A: INSERT INTO booking (seat, who) VALUES (12, 'a'); COMMIT;
B: INSERT INTO booking (seat, who) VALUES (12, 'b'); COMMIT;
```

With a unique index on `seat`, B fails on insert with SQLSTATE `23505`.

### Write skew

```text
A: BEGIN ISOLATION LEVEL REPEATABLE READ;  B: same
A: SELECT count(*) FROM oncall;             -- 2
B: SELECT count(*) FROM oncall;             -- 2
A: DELETE FROM oncall WHERE who = 'a'; COMMIT;
B: DELETE FROM oncall WHERE who = 'b'; COMMIT;   -- zero on call
```

Under SERIALIZABLE one of the two commits fails with `40001`.

### Double claim

```text
A: BEGIN; B: BEGIN;
A: SELECT id FROM jobs WHERE state = 'pending' ORDER BY id LIMIT 1;  -- 7
B: SELECT id FROM jobs WHERE state = 'pending' ORDER BY id LIMIT 1;  -- 7
```

With `FOR UPDATE SKIP LOCKED`, B receives the next row instead.

## Making it deterministic in a test

1. Open two connections, each in its own thread.
2. Place a two-party barrier between the read and the write in the code under test (a test hook or a seam), or have the test take `pg_advisory_lock(key)` and make the code's read path wait on it.
3. Start both, release the barrier, join, then assert the invariant on the final table state, not on the return values.
4. Run it against the same isolation level as production.

## MySQL notes

`SHOW ENGINE INNODB STATUS` prints the latest detected deadlock. For job claiming, `SELECT ... FOR UPDATE SKIP LOCKED` exists from MySQL 8.0.1. Gap locks under REPEATABLE READ can create deadlocks that do not occur in PostgreSQL; read the lock modes in the status output before changing the query.
