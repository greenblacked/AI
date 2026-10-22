# MySQL blocking queries

Assumes MySQL 5.7 or 8.0 with the `sys` schema and Performance Schema enabled, which is the
default. On MariaDB the Performance Schema may be off by default and `information_schema`
tables carry the same row-wait information.

## Contents

- [Row lock waits](#row-lock-waits)
- [Metadata lock waits](#metadata-lock-waits)
- [Who holds the transaction](#who-holds-the-transaction)
- [Kill syntax and settings](#kill-syntax-and-settings)

## Row lock waits

```sql
SELECT wait_age, locked_table, waiting_pid, waiting_query,
       blocking_pid, blocking_query, sql_kill_blocking_connection
FROM sys.innodb_lock_waits ORDER BY wait_started;
```

`blocking_pid` is the connection id of the holder. If the blocker's `blocking_query` is
NULL, it is idle inside a transaction, which is the common case.

## Metadata lock waits

A pending `ALTER TABLE` waits for the metadata lock and queues later statements behind it:
`SHOW FULL PROCESSLIST` shows `Waiting for table metadata lock`.

```sql
SELECT object_schema, object_name, lock_type, lock_status, owner_thread_id
FROM performance_schema.metadata_locks
WHERE object_name = 'orders' ORDER BY lock_status;
```

`PENDING` rows are waiting; `GRANTED` rows are holders. Map `owner_thread_id` to a
connection with `SELECT thread_id, processlist_id, processlist_user, processlist_info FROM
performance_schema.threads WHERE thread_id = <id>;`. `sys.schema_table_lock_waits` joins
this for you.

If the metadata_locks table is empty, the instrument is off. Enable it at runtime with
`UPDATE performance_schema.setup_instruments SET enabled = 'YES' WHERE name =
'wait/lock/metadata/sql/mdl';`, which only shows locks taken afterwards.

## Who holds the transaction

```sql
SELECT trx_mysql_thread_id, trx_started, trx_state, trx_rows_locked, trx_query
FROM information_schema.innodb_trx ORDER BY trx_started;
```

The oldest `trx_started` with `trx_query` NULL is the usual holder. The holder of a
metadata lock may be a transaction that only ever read the table: it keeps the lock until
it commits.

## Kill syntax and settings

```sql
KILL QUERY <processlist_id>;   -- ends the statement, keeps the connection
KILL <processlist_id>;         -- ends the connection and rolls back
```

Kill the waiting DDL first, then the holder. Prevention: `SET SESSION lock_wait_timeout =
5;` in the DDL session, and `innodb_lock_wait_timeout` (default 50) for row waits. Error
1205 is a row-lock timeout; by default (`innodb_rollback_on_timeout` off) it rolls back only
the statement, so the application must retry or roll back the transaction itself.
