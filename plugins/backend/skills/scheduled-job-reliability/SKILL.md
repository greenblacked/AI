---
name: scheduled-job-reliability
description: "Make cron-style jobs run when intended, once, and visibly. Give every job a contract (idempotent or not, maximum runtime, overlap policy, missed-run policy), pass the logical window in as a parameter instead of reading now(), stop overlap with a lease row or a Kubernetes CronJob set to concurrencyPolicy Forbid with startingDeadlineSeconds and activeDeadlineSeconds, and monitor as a dead-man's switch on time since last success rather than on error logs. Use for \"the cron job ran twice on two pods\", \"the nightly job silently stopped\", \"the job now takes longer than its interval\", \"missed run after a deploy\", \"how do we monitor cron\". Not for one host's crontab not firing (scheduled-job-debugging), general lock correctness (distributed-lock-audit), queue-driven work (event-driven-reliability), paging rules (alert-design), manifest faults (k8s-workloads)."
allowed-tools: Read, Glob, Grep, Edit, Write
---

# Scheduled Job Reliability

Done means every scheduled job has a written contract, cannot overlap itself, produces the same output whether it runs once, twice, late or after a crash, and raises an alert when it stops succeeding, including when it never starts.

The usual failure is a job that works on the day it was written. It runs on every replica because the scheduler lives in the application. It takes longer than its interval one busy month and starts stacking. It misses a run during a deploy and nobody notices for nine days, because a job that never starts logs nothing and an alert on error logs stays quiet.

## 1. Inventory and contract

Find every scheduled job: crontabs, systemd timers, Kubernetes `CronJob` objects, in-process schedulers (`@Scheduled`, `node-cron`, APScheduler, Quartz, Celery beat), cloud schedulers, and CI schedules that do production work. Write one row per job and do not leave a cell blank:

| Cell | Question |
| --- | --- |
| Idempotent | If it runs twice for the same window, is the result the same as once? |
| Max runtime | What duration means it is hung, measured from the slowest healthy run? |
| Overlap policy | Skip the new run, queue it, or replace the old one? |
| Missed-run policy | Skip, run once on recovery, or catch up each missed period? |
| Window | What logical period does a run cover, and who supplies it? |
| Owner and alert | Who is told when it has not succeeded, and after how long? |

A job with no answer for idempotence is treated as not idempotent until proven otherwise. Read `references/job-contract.md` for the template and a worked example.

## 2. Make the window a parameter

A job that reads `now()` to decide what to process gives a different answer on a rerun, a late start or a catch-up. Pass the logical window in (`--window-start 2026-03-01T00:00:00Z --window-end 2026-03-02T00:00:00Z`) and derive every query from it. The scheduler computes the window from the scheduled time, not the start time, so a run started forty minutes late still covers the right day. Half-open intervals (start inclusive, end exclusive) stop a row on the boundary being counted twice.

Make the write side idempotent on the same key: upsert on `(job, window, entity)`, replace the whole window's output in one transaction, or write to a staging table and swap. Appending without a key is how a rerun doubles a report.

## 3. Stop overlap

Pick the mechanism by what a duplicate costs.

- **Kubernetes `CronJob`.** Set `concurrencyPolicy: Forbid` so a new run is skipped while the previous one is active, and set `startingDeadlineSeconds` so a run that cannot start in time is counted as missed instead of firing late. Without it, the controller counts missed schedules since the last one and refuses to start the job at all once more than 100 have accumulated. Set `activeDeadlineSeconds` in `jobTemplate.spec` below the interval so an overrun is killed instead of stacking, and bound retries with `backoffLimit`. `Forbid` is a scheduling policy, not a guarantee: the documentation states a job may be created zero or two times for a schedule, so the job must be idempotent regardless.
- **A lease row** when the scheduler lives in the application or runs on several hosts. One row per job holding `owner` and `expires_at`; acquire with a single conditional statement and check the affected row count:

```sql
INSERT INTO job_lease (job, owner, expires_at)
VALUES ($1, $2, now() + $3 * interval '1 second')
ON CONFLICT (job) DO UPDATE
   SET owner = EXCLUDED.owner, expires_at = EXCLUDED.expires_at
 WHERE job_lease.expires_at < now()
RETURNING owner;
```

Zero rows returned means someone else holds it: skip the run. Renew while working with a separate statement that only the current holder can satisfy; the acquire statement cannot renew, because the holder's own unexpired lease fails its `WHERE`:

```sql
UPDATE job_lease
   SET expires_at = now() + $3 * interval '1 second'
 WHERE job = $1 AND owner = $2 AND expires_at > now()
RETURNING owner;
```

Zero rows on renewal means the lease was lost: stop work. If the job writes shared state, the lease is not enough on its own, because a paused holder can write after its lease lapses; carry a fencing token to the write or make the write itself idempotent. Read `distributed-lock-audit` for that decision instead of rebuilding it here.

- **Run the scheduler once.** Often the simplest fix is moving the schedule out of the replicated application into one `CronJob` or one scheduler deployment with a single replica, then still treating a double start as possible.

Reject `flock` on a path inside a container filesystem or per-pod disk as a cross-instance guard: each instance has its own file.

## 4. Choose the missed-run policy on purpose

A missed run happens at every deploy, node loss and scheduler outage, so choose rather than inherit:

- **Skip.** Right for a refresh whose next run supersedes it (cache warm, snapshot).
- **Run once on recovery.** Right for a job that computes from current state and covers any gap (sync, cleanup). Systemd calls this `Persistent=true`.
- **Catch up per period.** Right when each window has distinct output (daily billing, daily report). Enumerate the windows with no successful run record and run each in order, with the window as the parameter from step 2. Cap how many run in one pass so recovery does not become an overload.

Write the choice in the contract. A catch-up policy needs the run records from step 5, since that table is what says which windows are missing.

## 5. Write a run record

Each run inserts a row at start and updates it at the end: job, window, scheduled time, start, end, status (`running`, `succeeded`, `failed`, `skipped`), rows touched, owner. Three uses: the catch-up query, the evidence for "did it run last Tuesday", and the metric source. Mark a row `running` for longer than the max runtime as abandoned, so a crashed run does not block the next window.

## 6. Monitor absence, not errors

Alert on the time since the last success exceeding interval plus tolerance. An error-log alert cannot see a job that never started, a scheduler that is down, or a suspended `CronJob`.

- **Heartbeat.** The job calls a check service (a dead-man's-switch endpoint) on success only; the service alerts when the call does not arrive within the period plus a grace time. Ping at the end, with a separate start ping if duration matters.
- **Gauge.** Export a last-success timestamp and alert on `time() - job_last_success_timestamp_seconds{job="nightly-report"} > 1.5 * 86400`. Short-lived jobs push it to a Pushgateway, with the caveat that a pushed value persists after the job disappears, which is why the comparison is against the timestamp rather than against presence. On Kubernetes, kube-state-metrics exposes `kube_cronjob_status_last_successful_time` and `kube_cronjob_status_last_schedule_time`, and the first covers a job that was scheduled but never finished.
- Alert on duration approaching the max runtime as a ticket-level warning, well before it hits the interval.

Read `references/monitoring.md` for rules and a tolerance table. What reaches a pager versus a ticket belongs to `alert-design`.

## 7. Schedule hygiene

- Express schedules in UTC. A local-time schedule skips an hour in spring and runs twice in autumn in zones with daylight saving time, and a daily job at 02:30 local may not exist on one day. A Kubernetes `CronJob` has a `spec.timeZone` field; absent it, the schedule uses the controller's zone. If business hours drive the schedule, state the zone and accept a documented DST behaviour.
- Add deliberate jitter. Move fleets off `:00`, and spread many jobs across minutes with a fixed per-job offset (for example `7 3 * * *`), so they do not hit the database or an upstream API together. Where simultaneous start is unavoidable, add a random sleep inside the job, bounded well below the interval.
- Keep the interval at least several times the typical runtime. When runtime approaches the interval, fix the job (partition by window, process incrementally) before widening the interval.

## 8. Gate

Run these against a copy of the data and compare the output with a clean single run, row for row:

1. **Kill mid-run.** Send `SIGKILL` part-way, then rerun the same window. Output matches the clean run, with no duplicate rows and no half-written window.
2. **Two at once.** Start two instances for the same window together. Exactly one does the work, or both run and the result is still identical.
3. **Skip a day.** Do not run one window, then recover under the chosen missed-run policy. The catch-up fills the gap and nothing else changes.
4. **Silence.** Stop the scheduler and confirm the dead-man alert fires inside interval plus tolerance, in a staging alert route.

## Hand back

The contract table, the window parameter and idempotency key for each job, the overlap mechanism with its numbers (deadline, lease TTL, renewal), the missed-run policy and its cap, the run-record schema, the alert rules with tolerance and reasoning, and the four gate results with the comparison against the clean run.

## Anti-patterns

**Scheduler inside a replicated app.** Three replicas mean three runs. A leader check helps only if it survives a pause and the job is idempotent anyway.

**Alerting on errors only.** The one failure that matters, nothing ran, produces no error.

**Reading now() inside the job.** A rerun at a different time returns a different answer, so a retry is a new, unreviewed computation.

**Raising the timeout to stop overruns.** It hides a job outgrowing its interval until runs stack.

**Trusting `Forbid` to mean exactly once.** It reduces overlap; it does not remove a duplicate start.
