# MySQL and ProxySQL

## Contents

- [Reading the limit](#reading-the-limit)
- [Recovery](#recovery)
- [ProxySQL multiplexing](#proxysql-multiplexing)
- [Thread pool](#thread-pool)

## Reading the limit

```sql
SHOW VARIABLES LIKE 'max_connections';          -- default 151
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Max_used_connections';
SHOW GLOBAL STATUS LIKE 'Connection_errors_max_connections';
```

`Connection_errors_max_connections` counts the refusals. `Max_used_connections` since start
shows the peak. Error 1040 `Too many connections` refuses everyone except an account with
`CONNECTION_ADMIN` or `SUPER`, which is allowed one extra connection: do not use that slot
for application accounts.

## Recovery

1. Stop the herd as on PostgreSQL: pause the deploy, shed at the balancer.
2. Connect with the administrator's extra connection.
3. `SELECT id, user, host, time, state FROM information_schema.processlist WHERE command =
   'Sleep' AND time > 60 AND user = 'app';` then `KILL <id>;` for the sleeping ones.
4. `SET GLOBAL max_connections = <n>;` buys time but each thread costs memory; raise it
   modestly and revert after the fix. Persist nothing in a hurry.
5. Per-account caps: `ALTER USER 'app'@'%' WITH MAX_USER_CONNECTIONS 300;`.

## ProxySQL multiplexing

ProxySQL keeps a small pool of backend connections and shares them between many frontend
clients, returning a backend connection to the pool after each statement or transaction
when the session carries no state. Check `stats_mysql_connection_pool` (`ConnUsed`,
`ConnFree`, `ConnERR`) and `stats_mysql_global`. Multiplexing is disabled for a session by
things such as `SET` of session variables, temporary tables, `LOCK TABLES` and `GET_LOCK`;
a query rule can disable it explicitly. Set `mysql-max_connections` on ProxySQL for
frontends and `max_connections` per backend server in `mysql_servers`.

## Thread pool

MariaDB and Percona Server ship a thread pool that serves many connections with a
bounded set of worker threads; MySQL Community Edition does not (the thread pool is part
of MySQL Enterprise). It bounds running threads, but still needs a connection cap, since
idle connections hold memory.
