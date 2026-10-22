---
name: restore-canary
description: "Build a scheduled, unattended restore of the newest database backup into a throwaway instance, verified and torn down daily, so \"we have backups\" becomes a measurement rather than a belief. Fails first when the newest backup is older than its interval, restores into an isolated scratch target, compares row counts and checksums on key tables over a closed watermark range, runs a canary query suite, records restore duration against the RTO, tears down on every exit path, and alerts on a missed run as loudly as a failed one. Use when someone wants an automated or nightly restore test, asks how to know backups really restore, or says \"nobody has restored a backup in a year\". Not for a human restore rehearsal with business sign-off (disaster-recovery-exercise), backup topology or RPO targets (backup-recovery-design), failover drills (game-day) or replica lag (db-replication)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Restore Canary

The canary is done when a job restores the newest backup of each production database
every day without a person, proves the restored data is complete and readable, records how
long that took against the recovery time objective, deletes what it built, and pages
someone when it fails or when it silently does not run.

The usual failure is a backup estate measured by job success. Backup jobs report that a
copy was written; nothing reports that it can be read back. The gap opens quietly: an
encryption key loses a grant, a schema change breaks the dump format, the snapshot policy
was attached to the old instance after a migration, or the newest backup is from three
weeks ago because the schedule broke. Each of these is found during the incident that
needed the backup. A daily restore turns every one of them into a red check the next
morning.

## Scope

Use for: designing or reviewing a scheduled restore job for a managed or self-hosted
database (RDS, Aurora, Cloud SQL, Azure Database, pgBackRest, WAL-G, XtraBackup, logical
dumps); choosing what the job verifies; wiring its metrics and alerts; deciding which
backup copies to rotate through.

Do not use for: a one-off, human-led restore rehearsal with timed phases and a business
owner's acceptance, which is `disaster-recovery-exercise`; choosing backup topology,
retention, immutability or RPO targets, which is `backup-recovery-design`; deliberate
failover or fault injection, which is `game-day`; replica lag, replication slots and
promotion, which is `db-replication`; rehearsing a major version upgrade from a restored
snapshot, which is `db-major-upgrade`; finding which recovery tooling depends on the thing
it repairs, which is `bootstrap-dependency-audit`.

## Gates

1. **The scratch target cannot touch production.** No route from production applications
   to it, no route from it to production queues, mail or webhooks, no WAL or binlog
   archiving back into the production backup repository. A restored database still holds
   production data and production connection strings in its tables.
2. **The restored data keeps production's data classification.** Same encryption at rest,
   same access controls, no copies into analytics or developer accounts as a side effect.
   A restore canary that becomes an unaudited copy of customer data is a privacy incident
   on a schedule.
3. **A missed run alerts.** A canary that stops running and stays green is worse than none,
   because it carries the confidence without the measurement.

## Workflow

### 1. Fix what the canary proves and its budget

For each database, write down: the key tables (the ones whose loss is a business event,
typically five to fifteen), the database component's share of the RTO, the backup
interval the job should find, and whether point-in-time recovery is claimed. Take these
from the recovery design if one exists; if none does, say so in the hand-back rather than
inventing objectives.

Run daily. A weekly canary leaves a broken backup chain undetected for up to a week, which
on a seven-day retention window is the whole window.

### 2. Select the newest backup and check its age first

List backups, pick the newest completed one, and fail immediately if its completion time
is older than the backup interval plus a stated slack. This one check catches the most
common real defect, a backup schedule that stopped, before any restore time is spent.
Record the backup identifier and its completion time; every later number is reported
against them.

Select by querying, never by a hard-coded identifier or "latest" alias you have not
resolved and logged, so a later reader can see exactly which copy was proven.

### 3. Restore into an isolated scratch target

Restore into a dedicated network segment with no inbound route from production workloads
and outbound limited to what the verification needs (the metrics endpoint). Use a
dedicated role for the job that can restore, read and delete canary-tagged instances and
nothing else. Name and tag every resource it creates (for example a `purpose=restore-canary`
tag and a creation date), so the guard in step 7 and the sweeper can find them.

Size the target like production when the duration figure matters, because restore and
first-read times depend on instance class and storage throughput. A small instance makes
the canary cheap and its RTO figure fiction; if cost forces a smaller class, label the
duration as a lower bound on the real one.

For a restore tool that overwrites an existing target (Cloud SQL restores into an instance
you name; a file-level restore writes into a data directory), assert in code that the
target carries the canary tag or path before calling the restore. The command that
restores a backup onto the wrong instance is the same command with one argument changed.

Read `references/job-skeleton.md` for the restore, wait and teardown commands per
platform, the scheduler settings, and the platform-specific traps (Aurora clusters restore
without instances; snapshot restores lazy-load blocks; restored clusters inherit archiving
settings).

### 4. Time every phase

Record timestamps for: backup selected, restore requested, instance reachable, recovery
or replay finished, verification finished, teardown finished. Report restore duration as
requested-to-verified, not requested-to-available. Several managed services mark an
instance available while blocks are still being fetched from object storage in the
background, so the first full scan is where the real wait sits, and an incident pays it.

### 5. Verify the data, not the process

Run four checks in this order; stop and fail on the first that fails, because a later
check on a broken restore produces noise rather than evidence.

| Check | What it proves | Fails when |
| --- | --- | --- |
| Connect and schema version | The copy is readable with today's credentials and keys, and is the schema the application expects | Key grant lost, migration table missing or behind production by more than the change window |
| Physical integrity | Heap and index pages are not corrupt | `pg_amcheck` or `CHECK TABLE` reports an error |
| Counts and checksums over a closed range | Rows that existed before the backup point are all present and unchanged | Any mismatch outside the documented exceptions |
| Recovery point and canary queries | The data is as recent as the backup claims, and the queries the business depends on return sane answers | Newest row older than backup time minus slack; a canary query errors, times out or breaks an invariant |

The comparison problem is that production has moved on since the backup was taken, so a
whole-table count cannot match. Compare a closed range instead: rows whose creation
timestamp or sequence id falls before a watermark safely older than the backup point,
computed identically on the restored copy and on a production replica. For mutable
tables, hash only the columns that never change after insert, and compare full counts
against yesterday's canary within a stated tolerance. Read
`references/verification-queries.md` for the queries, the watermark rule, erasure
exceptions and what belongs in the canary suite.

### 6. Emit metrics a dead run cannot fake

Push at the end of a successful run: the success timestamp, duration per phase, the backup
age at selection, the recovery point age (backup time minus newest restored row) and the
number of rows verified. Push a success timestamp rather than a success flag: a gauge set
to 1 stays 1 in a push-based store long after the job has stopped running, whereas a
timestamp ages visibly.

### 7. Tear down on every exit path

Delete the scratch instance whether the run passed, failed or was killed, with the
deletion in an exit trap or a final pipeline step that runs on failure. Before deleting,
check the instance carries the canary tag, so a variable that resolved to the wrong name
cannot remove a production database. Skip the final snapshot on the scratch instance; it
is a copy of a copy. Run a separate daily sweeper that deletes canary-tagged resources
older than a day, because the job that crashed mid-restore is exactly the one whose own
trap did not fire.

### 8. Alert on failure, absence and drift

Four alerts, each routed to the team that owns the database, not to a shared inbox:

- the run failed, with the failing check and the backup identifier in the message;
- no success in more than a day plus the expected run time, which covers a scheduler that
  stopped, a job that hangs, and a metric that was never pushed;
- restore duration above a stated fraction of the database's RTO share (half is a
  reasonable starting point), so growth is visible months before it breaks the objective;
- newest backup older than its interval, from step 2.

`alert-design` covers routing and severity; a canary failure is normally a ticket the
same working day, not a page, unless the backup it proves is the only copy.

### 9. Rotate through the copies that matter in a disaster

The newest local snapshot proves the least, because it is the copy most likely to share a
failure with production. Once the daily run is stable, add a weekly run against a
cross-region or cross-account copy, or a locked vault copy, restored in the recovery
account with the recovery role; and, where point-in-time recovery is claimed, a run that
restores to a random time inside the retention window, which proves the log chain rather
than only the base backup.

## What to hand back

```markdown
## Coverage
[Databases under the canary, key tables per database, copies rotated and how often.]

## Job
[Scheduler, isolation of the target, the role it runs as, the tag guard, teardown and sweeper.]

## Verification
[Watermark rule per table, mutable-table handling, documented exceptions, canary queries.]

## Measurements
[Latest run: backup id and age, phase durations, recovery point age, rows verified,
duration against the RTO share.]

## Alerts
[The four alerts, thresholds, owners and routing.]

## Gaps
[Anything not yet proven: PITR, cross-account copies, production-size instance class.]
```

## Anti-patterns

**Counting backup job successes.** A successful job proves a write happened. Only a
restore and a read prove the copy is usable, and only a scheduled one keeps proving it.

**Comparing whole-table counts with live production.** They never match, so someone widens
the tolerance until the check passes on anything, including a restore missing a day of
rows. Compare a closed range.

**Treating "instance available" as restored.** Lazy-loaded storage and log replay mean the
slowest part of a restore can happen after the status turns green.

**A success flag in a push gateway.** The last value persists after the job dies, and the
dashboard stays green for a canary that has not run in a month.

**A scratch target in the production network.** A restored database contains production
webhooks, outbox rows and scheduled jobs; an application that finds it, or a job inside it
that wakes up, can act on real customers.

**Only ever restoring the newest local snapshot.** The copy you need after an account
compromise or a regional loss is the one in another account or region, and it is the one
the canary never touched.

## Reference files

- `references/job-skeleton.md` — read at steps 2, 3, 7 and 8: restore, wait and teardown
  commands for RDS, Aurora, Cloud SQL and pgBackRest, the managed restore-testing option,
  scheduler settings, the exit-trap pattern, and the metric and alert rules.
- `references/verification-queries.md` — read at step 5: the watermark rule, count and
  checksum queries for PostgreSQL and MySQL, mutable tables and erasure exceptions,
  integrity checks, recovery point age, and what belongs in the canary suite.
