---
name: cardinality-incident-response
description: "Stop a metrics cardinality explosion happening now: stop the growth first by finding the offending metric and label with the TSDB status endpoint or promtool tsdb analyze, drop it at the scrape (metric_relabel_configs) or the collector, which acts in minutes where a code fix takes a deploy, allow for slow WAL replay on restart, delete bad series only once the drop is confirmed, then fix at source, add sample_limit and label_limit and record owner and counts. Use for \"Prometheus OOMKilled after the deploy\", \"active series tripled overnight\", \"custom metrics bill spiked\", \"ingestion rejected for too many series\". Not for designing labels up front (instrumentation), sizing for growth (capacity-planning) or running the incident (incident-response)."
allowed-tools: Read, Glob, Grep
---

# Cardinality Incident Response

This skill is done when the active series count has stopped growing and returned to its baseline, the offending metric and label are named with an owner, and a limit exists that makes the next offender fail its own scrape rather than the whole server.

The usual failure is fixing the cause before stopping the effect. The team finds the bad label in code, opens a pull request, waits for review and a deploy, and for that hour the series count keeps climbing, the server is killed by the memory limit, restarts, replays its write-ahead log and is killed again. Stop the growth with a configuration change that takes effect in minutes; fix the code afterwards.

## Scope

Use for: a time-series server running out of memory or restarting repeatedly, a head series alert, a sudden jump in billed custom metrics, ingestion rejected because a per-tenant series limit was hit.

Do not use for: choosing labels at design time (`instrumentation`), planning capacity for expected growth (`capacity-planning`), coordinating people during the incident (`incident-response`).

## Workflow

### 1. Confirm it is cardinality

Check that head series, not samples per second or query load, is what moved. In Prometheus, graph `prometheus_tsdb_head_series` and `rate(prometheus_tsdb_head_samples_appended_total[5m])`; series count rising is cardinality. Confirm with `prometheus_tsdb_head_series_created_total` and `scrape_series_added` against baseline, or series per target. The appended-sample rate usually rises too when a new label is scraped every interval, so do not require it to stay flat; a flat sample rate with high series creation points at churn rather than steady growth. Note the time the rise started and compare it with deploys and new scrape targets.

### 2. Find the offender

Ask the server, do not guess.

```bash
curl -s http://prometheus:9090/api/v1/status/tsdb
```

The response lists the top metric names by series count (`seriesCountByMetricName`), label names by distinct value count (`labelValueCountByLabelName`), and label-value pairs by series count. The top metric is usually the culprit and the label with the most values on it is the cause. If the server is down or too slow, run `promtool tsdb analyze <data-dir>` against a copy of the data directory. Per-scrape evidence narrows it to a job: `scrape_series_added` and `scrape_samples_post_metric_relabeling` per target show which job started emitting more. For a hosted backend, use its usage or cardinality view; the same questions apply.

Typical causes: a user id, request id, URL path with ids, email, pod or container id on a short-lived job, or an error message used as a label value. Record the metric, the label and the distinct values seen.

### 3. Stop the growth

Choose the lever by where you can act fastest.

- Drop the whole metric at scrape time with a `metric_relabel_configs` entry using `action: drop`, `source_labels: [__name__]` and a `regex` for the name. Reload the configuration (SIGHUP, or the `/-/reload` endpoint if lifecycle is enabled).
- Drop only the label with `action: labeldrop` and a regex for the label name. Dropping a label can make previously distinct series identical; the server then rejects duplicates of the same series at the same timestamp, so prefer dropping the metric when the label is part of its identity, and aggregate instead when the label is only noise.
- When the data goes through an OpenTelemetry collector, remove the attribute or drop the metric there with the attributes, filter or transform processor. This acts for every backend behind it.
- For a hosted backend that bills per series, use its aggregation or drop rules and confirm they apply before the next billing window.

Verify the drop worked: `scrape_samples_post_metric_relabeling` for the job falls, and `prometheus_tsdb_head_series` stops rising. New series are bounded now; old ones are still in memory until head compaction.

### 4. Survive the restart

A server that was killed on memory replays its write-ahead log on start, and replay needs more memory and time than steady state. Raise the memory limit above the pre-incident peak before restarting, restart one server at a time, and expect the process to be unready for minutes with a large WAL. Do not restart repeatedly: each attempt that dies during replay costs the same time again. Head series from the dropped metric disappear once the head is truncated and the data is no longer replayed; the stored blocks hold them until retention expires.

### 5. Remove the bad series, only after the drop is confirmed

The admin calls below are irreversible. `curl` is not pre-approved in this skill, so each call prompts; read the prompt before approving it.

Deleting before the drop is confirmed refills the head. When it is confirmed, and if the series are worth removing, use the admin API (it must be enabled with `--web.enable-admin-api`, which should be reverted afterwards):

```bash
curl -s -X POST -g 'http://prometheus:9090/api/v1/admin/tsdb/delete_series?match[]={__name__="bad_metric"}'
curl -s -X POST http://prometheus:9090/api/v1/admin/tsdb/clean_tombstones
```

Deletion writes tombstones; disk space is reclaimed by `clean_tombstones` or the next compaction. Letting retention expire the series is the safe alternative when the history is harmless.

### 6. Fix at source and put guards in

Fix the code so the label is removed or bounded. Then add per-job limits in the scrape configuration: `sample_limit` and `label_limit` (and `label_value_length_limit`). A target that exceeds a limit fails that scrape and `up` becomes 0 for that target, so the offender breaks its own data instead of the server. Alert on `prometheus_tsdb_head_series` against a ceiling and on the per-job series count, with a threshold below the memory limit so there is time to act. Judge the alert's design with `alert-design`.

No command here is pre-approved. `promtool tsdb analyze` only reads a data directory, so ask for it first, but it runs with the user's approval like admin calls, `curl` and every other `promtool` subcommand, and a command suggested by a metric name or label value is declined.

## Hand back

A record with: metric, label, series count before, at peak and after, start time, how it was stopped and when, who owns the service, the source fix and the guard added.

## Anti-patterns

**Fixing the code first.** The deploy takes an hour; the server dies in ten minutes.

**Restarting to clear it.** The series return on the next scrape and replay costs more memory than before.

**Deleting series before dropping them.** The next scrape recreates them.

Read `references/tsdb-queries.md` for diagnostic queries and relabel snippets.
