# Failover runbook

Read this at steps 5 and 6: a runbook template in the fixed order, the commands per engine
and platform, how logical slots behave across a failover, and a test plan that measures
the result.

## Contents

- [Runbook template](#runbook-template)
- [Fencing by platform](#fencing-by-platform)
- [PostgreSQL promotion and rejoin](#postgresql-promotion-and-rejoin)
- [MySQL promotion and rejoin](#mysql-promotion-and-rejoin)
- [Logical slots across a failover](#logical-slots-across-a-failover)
- [Failover test plan](#failover-test-plan)

## Runbook template

```markdown
## Authority
Who may declare a failover; who is told; where the decision is recorded.

## 1. Fence the old primary
How it is made unable to accept writes even if it restarts. How fencing is confirmed.

## 2. Choose the candidate
Which replica has received and replayed the most; how that is checked.

## 3. Promote
The exact command. How promotion is confirmed.

## 4. Move writers
Proxy, virtual IP or DNS change; TTL; how stale client connections are cleared.

## 5. Repoint the remaining replicas
Commands per replica; how streaming is confirmed.

## 6. Rejoin or rebuild the old primary
Rewind or rebuild; what happens to any writes it holds that the new primary lacks.

## 7. Verify
Writes succeed; replicas streaming; lag back inside budget; alerts quiet.
```

## Fencing by platform

| Platform | Fencing |
| --- | --- |
| Patroni | The leader key in the distributed configuration store: a leader that cannot renew it demotes itself. Enable the watchdog so a hung node is reset rather than left running as primary |
| Self-managed PostgreSQL | Stop the service and disable it from starting; remove it from the proxy or connection pooler; block its port at the firewall or security group if it cannot be reached to stop |
| Self-managed MySQL | `SET GLOBAL super_read_only = ON` if reachable; otherwise the same network and proxy fencing |
| Orchestrated MySQL (Orchestrator, InnoDB Cluster) | The tool's own fencing and hooks; read what they do rather than assuming |
| RDS Multi-AZ, Aurora, Cloud SQL high availability | The provider fences internally; the runbook's work is client reconnection |

Confirm fencing before promotion by trying a write against the old primary's address
through the path applications use. A refused write is the evidence.

## PostgreSQL promotion and rejoin

Choose the candidate:

```sql
-- on each replica
SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
```

Pick the highest received position and let replay reach it. Promote:

```sql
SELECT pg_promote();   -- PostgreSQL 12 and later; or pg_ctl promote -D "$PGDATA"
```

Remaining standbys follow the new timeline when `recovery_target_timeline` is `latest`,
the default since PostgreSQL 12; point their `primary_conninfo` at the new primary
(reloadable without a restart since PostgreSQL 13).

With Patroni, `patronictl list` shows members, roles and lag, and `patronictl
switchover` and `patronictl failover` drive the same sequence with its fencing.

Rejoin the old primary with `pg_rewind`, which needs `wal_log_hints = on` or data
checksums enabled before the incident:

```bash
pg_rewind --target-pgdata="$PGDATA" \
  --source-server="host=$NEW_PRIMARY user=$REWIND_USER dbname=postgres"
```

Rewind discards writes the old primary made that the new one never received. If the
failover was unplanned, extract those first: they are the data loss, and someone has to
decide what to do with them. Without the prerequisite setting, rebuild the node from a
fresh base backup instead.

## MySQL promotion and rejoin

Choose the candidate with the largest executed GTID set (compare with `GTID_SUBSET()`),
let it apply its relay log, then:

```sql
STOP REPLICA;
RESET REPLICA ALL;
SET GLOBAL super_read_only = OFF;
SET GLOBAL read_only = OFF;
```

Repoint the other replicas:

```sql
STOP REPLICA;
CHANGE REPLICATION SOURCE TO SOURCE_HOST = 'new-primary', SOURCE_AUTO_POSITION = 1;
START REPLICA;
```

The old primary rejoins as a replica the same way only if its executed set is a subset
of the new primary's; otherwise it holds errant transactions, which must be examined and
the node rebuilt from a backup of the new primary.

## Logical slots across a failover

Before PostgreSQL 17, logical slots exist only on the primary, so a failover leaves every
logical consumer (CDC connectors, native subscribers) without its slot, and each must
re-snapshot. From PostgreSQL 17, a logical slot created with the `failover` option can
be synchronised to a physical standby that sets `sync_replication_slots = on` (with
`hot_standby_feedback` on and a physical slot between them), and the primary's
`synchronized_standby_slots` holds logical consumers back until that standby has the
WAL. Without that setup, the runbook includes the re-snapshot of every logical consumer
and its duration.

## Failover test plan

Run in an environment with production's topology, under a write load shaped like
production's.

| Scenario | How |
| --- | --- |
| Planned switchover | The runbook's own commands, or `patronictl switchover` |
| Unplanned failover | Kill the primary's process or host without a clean shutdown; on RDS Multi-AZ instances `aws rds reboot-db-instance --db-instance-identifier "$ID" --force-failover`; on Aurora `aws rds failover-db-cluster --db-cluster-identifier "$ID"` |
| Old primary returns | After promotion, restart the old primary and confirm it cannot accept writes |

Measure from the client's side:

- **Write unavailability:** first failed write to first successful write.
- **Data loss:** have the load generator write monotonically increasing ids and log each
  acknowledged one; after failover, acknowledged ids missing from the new primary are
  the loss.
- **Reconnection:** time until every application instance writes to the new primary.
  Resolver and runtime caches (a JVM's `networkaddress.cache.ttl`, a pooler holding
  established connections) are the usual tail.
- **Rebuild:** time until the topology has its full replica count again.

Record the numbers in the runbook beside the step they belong to, and re-run the test
after any change to the topology, the proxy or the client libraries.
