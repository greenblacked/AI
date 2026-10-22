---
name: late-data-maturity
description: "Decide when a daily or hourly figure is final enough to publish, from measured arrival lag: record event time and load time on every row, build a maturity curve of the share of each day's eventual rows and value present 1h, 6h, 24h and 7d after the day closes, publish where it passes an agreed completeness on bad days, not the median day, label earlier figures provisional, compare only at equal age, and fix a restatement window incremental models honour. Use when someone says \"yesterday's number keeps changing\", \"today always looks down\", \"when is last week final\", \"late-arriving events\" or \"how far back should the incremental model look\". Not for a one-off repair of existing records (safe-backfill), consumer replay design (event-driven-reliability), a service freshness objective (slo-design), or which checks a table gets (data-quality-checks)."
allowed-tools: Read, Glob, Grep
---

# Late Data Maturity

Done means every published figure carries a stated maturity: a publish time chosen from measured arrival lag, a provisional label on anything shown before that time, a restatement window after which the figure is frozen, and a pipeline whose incremental logic picks up every row that arrives inside that window.

The usual failure is treating lateness as noise. Yesterday's total is published at 07:00, grows by 3% over the next week, and every Monday someone explains a drop that was only rows still in transit from offline mobile clients, a partner's nightly file or a payment processor's settlement feed. The fix is not a faster pipeline; it is knowing, per source, how much of a day exists at each age and saying so.

## Workflow

### 1. Confirm the figure moves because rows arrive, not because logic changed

Pull the published value for the same past day at several computation times. If the change comes from new rows with an old event time, this skill applies. If existing rows were updated (a refund, a status change), the row count curve in step 3 will miss it, so build the value curve from a metric log instead. If the transformation code or a filter changed between runs, that is a reconciliation problem for `metric-reconciliation`, not lateness.

Start a metric log now if none exists: one row per metric, period, segment and computation time with the value. It is the cheapest durable instrument for this question, and it is what makes step 6's same-age comparison possible for figures built from many tables.

### 2. Put two timestamps on every row

Each row needs the event time (when it happened, in UTC, plus the reporting time zone used to assign it to a day) and the first load time (when the warehouse first held it). Set the load time on insert only; a `MERGE` that overwrites it on every update erases the arrival history this skill depends on. Keep a separate last-updated time if updates matter.

If load time was never recorded, recover an approximation before measuring: the loader's run log per batch, the landing bucket's object creation time per file, or, in BigQuery, `_PARTITIONTIME` on an ingestion-time partitioned table. Mark any curve built from that approximation as such.

### 3. Build the maturity curve

For each event day old enough to be treated as final (older than the longest lag you have seen, typically 30 days or more), compute the share of the eventual row count, and of the eventual metric value, that was present at fixed ages after the day closed in the reporting time zone: 1h, 6h, 24h, 72h, 7d. Measure lag from day close, not from event time, because the question is how long after the period ends a figure can be published.

Cut the curve by source and by any segment that arrives differently (platform, partner, region). A blended curve hides the one source that is 40% complete at 24h behind the large one that is complete in an hour.

Read `references/maturity-queries.md` for the curve query, its BigQuery form, the value curve and the summary across days.

### 4. Agree the completeness threshold with the figure's consumer

The threshold is a business decision, not an engineering one: a finance close may need 99.9% of value, an operations dashboard may act on 95% of rows. Ask the person who acts on the figure what error they can tolerate, write it down with their name, and set the threshold on value when decisions are about money and on rows when they are about counts.

### 5. Set the publish time from bad days

Choose the earliest age at which the curve passes the threshold on, say, 95% of past days, not on the average day. A publish time set from the median is wrong one day in two, and the wrong days cluster on month end, holidays and partner outages, which are exactly the days people look hardest. Check weekdays separately when the source has a weekly rhythm.

If the resulting publish time is too late for the consumer, the options are, in order: publish earlier with a provisional label and an expected-final band from the curve, get the slow source to deliver sooner, or exclude the slow source from the early figure and say so.

### 6. Label provisional figures and compare only at equal age

Show anything published before its maturity age as provisional, in the table (a maturity column or `is_final` flag) and in the dashboard (a distinct style and the age). Then stop comparing a provisional day with a final one: "yesterday is down 4% on last Tuesday" compares 20 hours of arrival with 8 days. Compare yesterday at 20 hours with last Tuesday as it stood 20 hours after it closed, from the load time or the metric log. The same-age query is in `references/maturity-queries.md`.

### 7. Fix a restatement window and make the pipeline honour it

Pick the window from the tail of the curve, the age past which late rows are rare enough to stop restating (for example where the bad-day curve reaches 99.9%). Inside the window, figures are restated in place and labelled as such. After it, choose one policy and publish it: freeze the period and book later arrivals into the period they arrived, as accounting does, or restate with a versioned figure and a notice. Read `references/publish-policy.md` for the decision table and the policy text.

Then check the incremental models. An incremental filter on `event_time > max(event_time)` silently drops every late row, because a late row's event time is already behind the high-water mark. Select new rows by load time and re-aggregate every event day they touch, or re-process a lookback at least as long as the restatement window. The pattern is in `references/maturity-queries.md`.

### 8. Re-measure on a schedule

Lag drifts when a source changes its batching or a partner moves its file drop. Recompute the curve monthly and whenever a source changes, and add a check that the day being published is at or above the curve for its age; which checks block publish is decided with `data-quality-checks`.

## What to hand back

```markdown
## Figure
[Metric, grain, reporting time zone, sources.]

## Maturity curve
[Table: age vs share of rows and of value, median day and 95th-percentile-bad day, per source.]

## Threshold and publish time
[Threshold, on rows or value, who agreed it; resulting publish age.]

## Provisional labelling and comparisons
[How provisional figures are flagged; the equal-age comparison now used.]

## Restatement window and policy
[Window length, what happens to arrivals after it, how restatements are announced.]

## Pipeline changes
[Load-time column, incremental predicate or lookback, metric log, monitoring check.]
```

## Anti-patterns

**Fixing lateness with a faster schedule.** Running the job hourly does not make a partner's nightly file arrive sooner; it only publishes the incomplete figure more often.

**A single blended curve.** The large, fast source dominates the average and hides the small, slow one that moves the total.

**Overwriting load time on update.** The arrival history disappears the first time the row changes, and the curve can no longer be rebuilt.

**Week-on-week comparisons across maturity.** A provisional day compared with a final one shows a drop that is pure arrival lag, and somebody spends a morning explaining it.

**An incremental model keyed on event time.** It looks correct in testing, where nothing arrives late, and loses rows in production every day.

## Reference files

- `references/maturity-queries.md` — read at steps 3, 6 and 7: the maturity curve and value curve queries, the summary across days, the equal-age comparison, and the incremental pattern that keeps late rows.
- `references/publish-policy.md` — read at steps 4, 5 and 7: choosing the threshold, the restatement policy decision table, and the policy text to publish beside the figure.
