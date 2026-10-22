# Lock grids and live inspection

Read this when you need a worked grid for a class, or the commands to watch locks while reproducing a cycle.

## Worked grids

### Opposite-order batch updates

| Step | Transaction A | Transaction B |
| --- | --- | --- |
| 1 | `UPDATE accounts SET ... WHERE id = 1` (holds 1) | `UPDATE accounts SET ... WHERE id = 2` (holds 2) |
| 2 | `UPDATE accounts SET ... WHERE id = 2` (waits for B) | `UPDATE accounts SET ... WHERE id = 1` (waits for A) |

Fix: both sort ids ascending before the first update.

### Foreign-key parent versus child (PostgreSQL)

| Step | Transaction A | Transaction B |
| --- | --- | --- |
| 1 | `INSERT INTO orders (customer_id) VALUES (7)` (shared key lock on customer 7) | `INSERT INTO orders (customer_id) VALUES (7)` (shared key lock on customer 7) |
| 2 | `SELECT * FROM customers WHERE id = 7 FOR UPDATE` (waits for B's shared lock) | `SELECT * FROM customers WHERE id = 7 FOR UPDATE` (waits for A's shared lock) |

Fix: lock the parent before inserting the child in both paths, and use `FOR NO KEY UPDATE` when the key is not changing, since it does not conflict with the shared key lock.

### Gap locks (MySQL, REPEATABLE READ)

Both transactions run `SELECT ... WHERE k = 10 FOR UPDATE` on a key that has no row. Both get a gap lock, which does not conflict with the other's gap lock. Each then runs `INSERT` for `k = 10`, which needs an insert-intention lock the other's gap lock blocks. Fix: insert first and handle the duplicate with `INSERT ... ON DUPLICATE KEY UPDATE`, or use READ COMMITTED for that transaction.

## Reproducing with two sessions

Open two sessions, run step 1 in each, then step 2 in each. One session is chosen as victim after `deadlock_timeout` in PostgreSQL; InnoDB detects immediately when `innodb_deadlock_detect` is on (the default).

## Live inspection

PostgreSQL:

```sql
SELECT l.pid, l.locktype, l.mode, l.granted, a.query
FROM pg_locks l JOIN pg_stat_activity a USING (pid)
WHERE NOT l.granted OR l.pid IN (SELECT pid FROM pg_locks WHERE NOT granted);
```

`pg_blocking_pids(pid)` returns who a given backend waits for.

MySQL 8.0:

```sql
SELECT * FROM performance_schema.data_lock_waits;
SELECT object_name, index_name, lock_type, lock_mode, lock_status, lock_data
FROM performance_schema.data_locks;
```

`lock_data` shows the key values, and a `GAP` in `lock_mode` marks a gap lock.
