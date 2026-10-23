# Failover test

Read this when you are about to run the forced failover and need the probe, the procedure and the record.

## Preconditions

- Steady write load at production-like volume, from the real services, not a single script.
- A window agreed with the owners of every service that uses the database, and a way to abort.
- The server-side runbook for the failover itself; this document does not replace it.

## Probe

One writer per service, once a second, with a short statement timeout so a hang shows as an error:

```sql
SET statement_timeout = '3s';
INSERT INTO failover_probe (service, sent_at) VALUES ('orders', now());
```

Log the wall-clock time, the outcome and the exact error text or SQLSTATE. For MySQL use `SET SESSION max_execution_time` for SELECTs or a client-side timeout, since it does not cover writes.

## Triggering

Amazon RDS and Aurora: reboot with failover from the console or the CLI (`aws rds reboot-db-instance --force-failover` for Multi-AZ instances, `aws rds failover-db-cluster` for Aurora). Patroni: `patronictl switchover`. Note the second the command was issued.

## Record

| Service | Failover started | First failed write | First successful write | Seconds to success | Errors seen |
| --- | --- | --- | --- | --- | --- |

Seconds to success is first successful write minus failover started. Keep one row per run and per service, labelled before or after.

## Reading the errors

| Error seen | Likely cause |
| --- | --- |
| Timeouts for minutes, then success | Half-open sockets: no keepalive or user timeout |
| Connection refused or host not found, long | Cached or pinned address |
| `25006` or MySQL 1290 | Connection to the demoted node still in use |
| Success on the new primary but duplicated rows | Retry of a write with unknown outcome |
| Errors only on long-lived services | No maximum lifetime on the pool |
