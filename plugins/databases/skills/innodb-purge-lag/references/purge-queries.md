# Purge lag queries

Reference for steps 1, 2 and 6. Read-only queries unless marked. Run them on the
primary and on each replica.

## Contents

- [Sampling the history list](#sampling-the-history-list)
- [Transactions and their owners](#transactions-and-their-owners)
- [Settings to read](#settings-to-read)
- [Reading the result](#reading-the-result)

## Sampling the history list

Run once a minute for several hours from a shell on a management host and append to a
file with the time:

```bash
while true; do
  printf '%s ' "$(date -u +%FT%TZ)"
  mysql -N -e "SELECT count FROM information_schema.INNODB_METRICS WHERE name = 'trx_rseg_history_len'"
  sleep 60
done >> history-list.log
```

The credentials come from the client's option file, not the command line. Plot or read
the file for a rising floor.

## Transactions and their owners

```sql
SELECT trx_id, trx_state, trx_started, trx_mysql_thread_id,
       TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS age_s,
       trx_rows_modified, trx_isolation_level, LEFT(trx_query, 80) AS query
FROM information_schema.innodb_trx
ORDER BY trx_started LIMIT 10;
```

Idle-in-transaction sessions only:

```sql
SELECT t.trx_mysql_thread_id, p.user, p.host, p.db, p.time AS idle_s, t.trx_started
FROM information_schema.innodb_trx t
JOIN information_schema.processlist p ON p.id = t.trx_mysql_thread_id
WHERE p.command = 'Sleep'
ORDER BY t.trx_started;
```

A transaction in `innodb_trx` with `command = 'Sleep'` is open and idle. Prepared XA
transactions: `XA RECOVER;`.

On 8.0 the same ownership data is available from `performance_schema.threads` and
`performance_schema.events_transactions_current` (user, host, command and transaction
state). The client program name is not in those tables; it comes from the connection
attributes in `performance_schema.session_connect_attrs` (`ATTR_NAME = 'program_name'`,
joined on `PROCESSLIST_ID`), and only when the client sets it.

## Settings to read

```sql
SHOW VARIABLES LIKE 'innodb_purge_threads';
SHOW VARIABLES LIKE 'innodb_max_purge_lag%';
SHOW VARIABLES LIKE 'innodb_undo%';
SHOW VARIABLES LIKE 'transaction_isolation';
SHOW VARIABLES LIKE 'wait_timeout';
```

On 8.0 list the undo tablespace files:

```sql
SELECT tablespace_name, file_name FROM information_schema.files
WHERE file_type = 'UNDO LOG';
```

Compare each file's size on disk with `innodb_max_undo_log_size`.

## Reading the result

| Observation | Meaning | Next |
| --- | --- | --- |
| Floor rises, one old row in `innodb_trx` | A read view pins purge | Step 3 and 4 |
| Floor rises, nothing old | Purge is slower than the change rate | Step 5 |
| History list falls after a kill, then rises again | Cause is a recurring owner | Fix the owner and add an alert |
| Undo files large, history list low | Space not yet truncated | Step 6 |
| `ibdata1` large, history list low | Space reusable but not returned | Say so; rebuild only if disk demands it |
