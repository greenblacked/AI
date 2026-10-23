---
name: db-major-upgrade
description: "Upgrade a PostgreSQL or MySQL major version, managed or self-hosted: scan extensions, removed features and authentication plugins first; restore a production snapshot and rehearse the whole upgrade with timings; choose in-place pg_upgrade, blue/green or logical replication by the downtime you can tolerate; ANALYZE straight after; compare plans for the top queries by total time; keep the old cluster until a full business cycle passes. Use when someone is moving Postgres 13 to 17, MySQL 8.0 to 8.4, planning an RDS, Aurora or Cloud SQL major version upgrade, or asks \"how long will pg_upgrade take\", \"can we roll back after the upgrade\" or why queries got slower after it. Not for a schema change on a live table (db-migration), an application library or framework bump (dependency-upgrade), the switchover window itself (cutover), or replica lag and failover (db-replication)."
allowed-tools: Read, Grep, Glob
---

# Database Major Upgrade

Done means the database runs the target major version, the downtime matched the number
measured in rehearsal, the top queries run on plans at least as good as before, and a
rollback path existed and was named — with its point of no return — until a full
business cycle had passed on the new version.

Major upgrades fail in three predictable places. The first is compatibility discovered on
the night: an extension with no build for the target, a removed configuration parameter,
an old client driver that cannot speak the new default authentication. The second is
timing: a rehearsal on a staging database a hundredth the size of production predicts
nothing about how long the copy, the link or the replication catch-up takes. The third
arrives after everyone has gone home: PostgreSQL's `pg_upgrade` historically carried no
planner statistics across, so until `ANALYZE` finishes the planner is guessing, and a
new optimiser version can choose a different plan for the query that matters most even
with fresh statistics. Each failure is cheap to find in advance and expensive to find
live.

## Scope

Use for: a PostgreSQL or MySQL major-version upgrade — self-hosted, RDS, Aurora, Cloud
SQL or Azure Database — including choosing the method, rehearsing it, running it and
verifying query plans afterwards; and a forced upgrade driven by an end-of-life date.

Do not use for: a schema change on a live database, which is `db-migration`; upgrading
an application's libraries or ORM, which is `dependency-upgrade`; planning the
communication, go/no-go and rollback window for the switch itself, which is `cutover`
(this skill hands it the measured numbers); and replica lag, slots or failover in
steady state, which is `db-replication`.

## Workflow

Every `psql`, `mysql`, `mysqlsh`, `pg_upgrade`, `vacuumdb` and cloud change command below runs
with the user's approval and is not pre-approved (only Read, Grep and Glob are): the query text in `pg_stat_statements`
and the digest tables is written by whoever sent the query, so a grant broad enough to run
SQL would let planted text run a mutating statement unasked.

### 1. Fix the target and the supported path

Name the current and target versions and the reason (end of support, a needed feature).
PostgreSQL's `pg_upgrade` can jump several majors at once; MySQL cannot skip a series
(5.7 goes to 8.0 before 8.4). On a managed service, ask the provider which targets are
valid from where you are:

```bash
aws rds describe-db-engine-versions --engine postgres --engine-version "$CURRENT" \
  --query 'DBEngineVersions[].ValidUpgradeTarget[?IsMajorVersionUpgrade==`true`].EngineVersion'
```

### 2. Scan for incompatibilities before anything else

- **Extensions.** List installed extensions and versions, and confirm each has a build
  for the target (on a managed service, in the provider's supported-extensions list).
  An extension without one is a blocker, not a detail.
- **Removed and changed features.** Read the incompatibilities section of every major's
  release notes between current and target, not only the target's. Each one is a check
  against your configuration, schema or application.
- **The tool's own check.** `pg_upgrade --check` against the target binaries; MySQL
  Shell's `util.checkForServerUpgrade()` with the target version.
- **Clients.** Driver versions against the target's authentication defaults
  (`scram-sha-256` in PostgreSQL, `caching_sha2_password` in MySQL, and
  `mysql_native_password` no longer loaded by default in 8.4).
- **Collation.** If the new version also lands on a new operating system image, a changed
  C library collation silently corrupts text indexes; plan to reindex them.

Read `references/compatibility-scan.md` now for the queries, the checker invocations and
the version-specific traps.

*Gate:* every finding has an owner and a fix merged or scheduled before rehearsal.

### 3. Capture the baseline

Before touching anything, record the top queries by total time with their plans, and the
server settings. This is what step 7 compares against, and it cannot be captured after
the upgrade.

```sql
-- PostgreSQL 13 and later
SELECT queryid, calls, total_exec_time, mean_exec_time, query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 25;
```

Save the query text and `EXPLAIN` output for each with representative parameters. Match
queries across versions by normalised text, not by `queryid`: `pg_stat_statements` does not
keep a `queryid` stable across major versions or after a dump and restore. In MySQL, take the same
list from `performance_schema.events_statements_summary_by_digest` ordered by
`SUM_TIMER_WAIT`.

### 4. Choose the method by tolerated downtime

| Tolerated write downtime | Method | Rollback |
| --- | --- | --- |
| Hours | `pg_upgrade --copy`, or dump and restore; MySQL in-place | Old data directory or instance untouched |
| Minutes | `pg_upgrade --link` (time barely depends on data size); managed in-place upgrade | Not the old directory once the new server starts in link mode: keep a snapshot or a standby on the old version |
| Under a minute | Logical replication into a new-version cluster, RDS Blue/Green Deployments, or a MySQL replica on the target version then promotion | Switch back to the old cluster; writes made after the switch are lost unless replicated back |

Logical methods buy short downtime at the price of their own gaps: PostgreSQL logical
replication does not carry DDL or sequence values, and needs a primary key or replica
identity on every table that takes updates. Read `references/method-and-rollback.md` for
each method's commands, those gaps, and the rollback window each one actually leaves.

### 5. Rehearse on a restored production snapshot, with a stopwatch

Restore the latest production snapshot at full size on production-class storage and run
the chosen method end to end: the check, the upgrade or catch-up, `ANALYZE`, extension
updates, application smoke tests. Time each phase. The rehearsal's numbers are the
downtime estimate given to `cutover` and to the business, and a rehearsal that overruns
is a finding about the method, not about the night.

*Gate:* the full sequence has run once on production-sized data inside the tolerated
downtime, and the step 3 queries have been compared on the rehearsal copy.

### 6. Run it, then ANALYZE immediately

Run the rehearsed sequence. Straight after the new server accepts connections, gather
statistics before full traffic returns:

```bash
vacuumdb --all --analyze-in-stages --jobs="$JOBS"
```

Before PostgreSQL 18, `pg_upgrade` carries no planner statistics at all; from 18 it
carries most of them, but extended statistics still need a fresh `ANALYZE`. Update each
extension (`ALTER EXTENSION name UPDATE`) as its documentation directs. After a logical
copy into MySQL, run `ANALYZE TABLE` on the hot tables.

### 7. Compare plans for the top queries

Re-run step 3's list on the new version and join it to the baseline on normalised query
text. For each query whose plan changed or whose mean
time rose, read the new plan against the old one. Usual causes are a statistic not yet
gathered, a cost or default setting the new version changed, and a correlated predicate
the new optimiser estimates differently; fix with targeted statistics or settings rather
than rolling back the whole upgrade for one query.

### 8. Hold the rollback path for a full business cycle

Keep the old cluster, snapshot or reverse replication until a full business cycle — the
month-end close, the weekly batch, the peak day — has run on the new version. Write down
the point of no return: the moment after which writes on the new version would be lost
by switching back. Decommission the old cluster only after the cycle passes.

## Anti-patterns

**Rehearsing on staging-sized data.** The timing is the deliverable, and it does not
scale linearly from a small copy.

**Opening traffic before statistics exist.** The first hour of production on a planner
with no statistics looks like a failed upgrade and often triggers an unnecessary
rollback.

**Using `--link` and calling the old directory the rollback.** Once the new server has
started in link mode, the old cluster can no longer be used safely.

**Reading only the target version's release notes.** A jump across three majors carries
three sets of incompatibilities.

## Output

```markdown
## Versions and path
[current, target, reason, supported path]

## Compatibility findings
| Finding | Source | Owner | Fix | Status |

## Method and rollback
[method, tolerated downtime, rollback mechanism, point of no return]

## Rehearsal timings
| Phase | Duration on production-sized data |

## Plan comparison
| Query (normalised text) | Mean before | Mean after | Plan changed | Action |

## Decommission
[business cycle waited for, date the old cluster is removed]
```

## Reference files

- `references/compatibility-scan.md` — read at step 2: extension and feature queries,
  `pg_upgrade --check` and MySQL Shell's upgrade checker, the authentication and
  collation traps, and what to read in each set of release notes.
- `references/method-and-rollback.md` — read at steps 4, 5 and 8: commands for each
  method on self-hosted and managed services, the gaps in logical replication, the
  rehearsal timing sheet, and the rollback window each method leaves.
