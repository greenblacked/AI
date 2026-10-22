# PostgreSQL blocking queries

## Contents

- [The blocking tree](#the-blocking-tree)
- [What a session is holding or waiting for](#what-a-session-is-holding-or-waiting-for)
- [Long transactions](#long-transactions)
- [Cancel and terminate](#cancel-and-terminate)

## The blocking tree

```sql
WITH RECURSIVE waits AS (
  SELECT pid, unnest(pg_blocking_pids(pid)) AS blocker
  FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid)) > 0
), tree AS (
  SELECT a.pid, NULL::int AS blocker, 0 AS depth, ARRAY[a.pid] AS path
  FROM pg_stat_activity a
  WHERE cardinality(pg_blocking_pids(a.pid)) = 0
    AND EXISTS (SELECT 1 FROM waits w WHERE w.blocker = a.pid)
  UNION ALL
  SELECT w.pid, w.blocker, t.depth + 1, t.path || w.pid
  FROM waits w JOIN tree t ON w.blocker = t.pid
  WHERE NOT w.pid = ANY (t.path)
)
SELECT t.depth, t.pid, a.usename, a.application_name, a.state,
       now() - a.xact_start AS xact_age, left(a.query, 80) AS query
FROM tree t JOIN pg_stat_activity a USING (pid)
ORDER BY t.path;
```

Depth 0 rows are the roots. A pending DDL appears at depth 1 with many rows at depth 2
beneath it: that is the queue behind a waiting exclusive request.

## What a session is holding or waiting for

```sql
SELECT l.pid, l.locktype, l.mode, l.granted, l.relation::regclass AS rel
FROM pg_locks l WHERE l.pid = <pid> ORDER BY l.granted, l.locktype;
```

`granted = false` is the request it waits on. `locktype = 'transactionid'` or `tuple` means
a row-level wait on another transaction; `relation` means a table lock.

| Waiting request | Typical statement | Blocked by |
| --- | --- | --- |
| ACCESS EXCLUSIVE | most `ALTER TABLE`, `DROP`, `TRUNCATE`, `VACUUM FULL` | Any lock on the table, including a plain `SELECT` in an open transaction |
| ACCESS SHARE | `SELECT` | Only a granted or already queued ACCESS EXCLUSIVE |
| ROW EXCLUSIVE | `INSERT`, `UPDATE`, `DELETE` | SHARE and stronger locks |

## Long transactions

```sql
SELECT pid, usename, application_name, client_addr, state, xact_start,
       now() - xact_start AS xact_age, left(query, 80) AS last_query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL AND pid <> pg_backend_pid()
ORDER BY xact_start LIMIT 10;
```

For `idle in transaction`, `query` is the last statement it ran, not what it is waiting for;
the application, not the database, left it open.

## Cancel and terminate

```sql
SELECT pg_cancel_backend(<pid>);      -- cancels the current statement only
SELECT pg_terminate_backend(<pid>);   -- ends the connection and rolls back
```

A session `idle in transaction` has no running statement, so cancel does nothing to it;
terminating is the only option. Both functions need to be run by the same role as the
target or by a member of `pg_signal_backend`, or a superuser.
