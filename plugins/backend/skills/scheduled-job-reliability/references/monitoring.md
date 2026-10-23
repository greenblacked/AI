# Monitoring a scheduled job

Alert on the absence of success. Every rule below fires when nothing happens, which an error-rate rule cannot do.

## Heartbeat check

1. Create one check per job with period equal to the schedule interval and a grace time.
2. Call its URL as the last step on success only. A failing run must not ping.
3. Optionally ping a start URL, so the service can report a run that started and never finished.

## Prometheus rules

Last-success gauge exported by the job (or pushed to a Pushgateway):

```promql
time() - nightly_report_last_success_timestamp_seconds > 1.5 * 86400
```

Kubernetes `CronJob` via kube-state-metrics:

```promql
time() - kube_cronjob_status_last_successful_time{cronjob="nightly-report"} > 1.5 * 86400
```

A cronjob that has never succeeded has no sample for the series, so the rule above cannot fire for it. Measure that case from creation time instead:

```promql
time() - kube_cronjob_created{cronjob="nightly-report"} > 1.5 * 86400
unless on(cronjob) kube_cronjob_status_last_successful_time{cronjob="nightly-report"}
```

A bare `absent()` on the last-success series is the wrong substitute: it fires the moment a CronJob is created, before the first run is due, and it keeps firing after the CronJob is deleted or renamed. If you use `absent()`, give the rule a `for:` duration equal to the tolerance.

Duration warning, before overlap:

```promql
nightly_report_last_duration_seconds > 0.6 * 3600
```

## Tolerance

| Schedule | Alert after no success for |
| --- | --- |
| Every 5 minutes | 3 intervals (15 minutes) |
| Hourly | 2 intervals plus the max runtime |
| Daily | 1.5 intervals, so one late run does not page |
| Weekly | interval plus 1 day |

Choose from the cost of a missed run, not from habit. A job feeding a customer-visible report deserves a tighter number than a cleanup.

## Pushgateway caveat

A pushed value stays until deleted. Alerting on the timestamp value catches a job that stopped; alerting on the metric being present does not. Delete the group when a job is retired so a stale series does not mask a replacement.

## What to check after an alert

Distinguish three states using the run record: never scheduled (scheduler down, `CronJob` suspended, bad expression), scheduled but never started (skipped by `Forbid`, past `startingDeadlineSeconds`, no capacity), started and failed or hung. The per-host causes of the first two are in `scheduled-job-debugging`.
