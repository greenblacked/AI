# PgBouncer and connection arithmetic

## Contents

- [Worked sizing example](#worked-sizing-example)
- [Settings that matter](#settings-that-matter)
- [Admin console](#admin-console)
- [Session state lost in transaction mode](#session-state-lost-in-transaction-mode)

## Worked sizing example

A 16-core database host, `max_connections = 500`, `superuser_reserved_connections = 3`.

1. Useful active backends: 16 cores times 2 to 4 gives about 32 to 64. Take 48 as the
   target for ordinary workload.
2. Reserve slots for replication, monitoring and administrators: 20.
3. Supply for the pooler's server connections: choose 48 to 60, far below the 477 that
   `max_connections` would allow.
4. Two PgBouncer instances, one pool per application database and user: `default_pool_size`
   of 25 each gives 50 server connections in total.
5. Clients: 40 application instances with pool maximum 20 give 800 client connections, handled
   by `max_client_conn = 2000`. Clients are cheap; server connections are what costs.

Two budgets, kept separate. Without a pooler, the application pools summed across all
instances must stay under the server supply. With a pooler, the application pools summed
across instances must stay under `max_client_conn` (800 against 2000 above), and
`default_pool_size` times the number of pools, plus `reserve_pool_size` times the number of
pools, must stay within the server supply (50 against 48 to 60 above, before reserve). Clients beyond the server supply queue at the pooler by design.

## Settings that matter

| Setting | Meaning | Note |
| --- | --- | --- |
| `pool_mode` | `session`, `transaction`, `statement` | Use `transaction` unless the application needs session state |
| `default_pool_size` | Server connections per database and user pair | Size from the database ceiling, divided across pairs and instances |
| `max_client_conn` | Clients the pooler accepts | Raise it freely; each client is a small structure, but check the file descriptor limit |
| `reserve_pool_size` | Extra server connections for waiting clients | Small, for bursts |
| `reserve_pool_timeout` | Seconds a client waits before the reserve is used | Default 5 |
| `query_wait_timeout` | Seconds a client may wait for a server connection | Make the error appear before your request timeout |
| `server_idle_timeout` | Closes unused server connections | Keeps the pool from holding idle slots |
| `max_prepared_statements` | Prepared statement support in transaction mode | PgBouncer 1.21 and later; zero disables |

Reload with `RELOAD;` on the admin console for most settings; a few need a restart.

## Admin console

`psql -p 6432 -U pgbouncer pgbouncer`, as a user listed in `admin_users` or `stats_users`.

- `SHOW POOLS;` columns `cl_active`, `cl_waiting`, `sv_active`, `sv_idle`, `sv_used`, `maxwait`.
  Rising `cl_waiting` with `sv_active` at the pool size means the pool is the limit; the cause is
  slow queries (`sql-performance`) or a pool smaller than demand.
- `SHOW STATS;` average query and wait times per database.
- `SHOW CLIENTS;`, `SHOW SERVERS;` per connection detail.
- `PAUSE;` and `RESUME;` hold new queries while you restart or fail over a database; use them
  for planned changes rather than letting clients see errors.

## Session state lost in transaction mode

| Feature | Behaviour in transaction mode | Alternative |
| --- | --- | --- |
| `SET` | Lasts until the server connection is reused by another client | `SET LOCAL` inside a transaction, or role defaults |
| Session advisory locks | Held by a connection that someone else may use next | Transaction-level advisory locks |
| `LISTEN` / `NOTIFY` | The listener loses its connection | A direct connection for listeners |
| Temporary tables | Disappear or leak between clients | Create within one transaction |
| Prepared statements | Fail before 1.21 | `max_prepared_statements` on 1.21 and later, or client-side disable |
