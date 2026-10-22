---
name: business-metric-alerting
description: "Alert on drops in business throughput such as orders, sign-ups or payments when there is no error rate to burn: compare against an expected value from the same weekday and time of day over the last four to eight weeks (median, to resist past incidents), alert when the observed rate falls below a fraction taken from historical residuals, add a minimum-volume gate, a longer confirming window and a holiday or campaign calendar, separate zero traffic from low traffic, and backtest before enabling. Use this skill whenever someone says \"alert if orders per minute fall\", \"we were down for an hour and nothing paged\", \"seasonal traffic alerts\" or \"alert on low sign-ups at night\". Not for SLO burn alerts on errors and latency (alert-design), explaining after the fact why a product metric moved (metric-anomaly-triage), or testing a rule against history (alert-backtest)."
allowed-tools: Read, Glob, Grep, Edit, Write, Bash(promtool check rules:*), Bash(promtool check config:*)
---

# Business Metric Alerting

Done means a throughput drop that users would notice pages or tickets within a known delay, quiet hours and holidays do not fire it, and a backtest shows both.

The usual failure is a constant threshold: "fewer than 50 orders a minute". It fires every night at 03:00 and stays silent at noon when orders fall from 400 to 80. Traffic has a daily and weekly shape, so the threshold has to be a moving expectation. The second failure is no alert at all, because no error rate rises when the checkout button silently stops sending events.

## Scope

Use for: counts of business events (orders, payments, sign-ups, messages sent) where a fall is the symptom.

Do not use for: error or latency SLOs (`alert-design`), explaining a metric movement after it has happened (that is `metric-anomaly-triage`), or running the history test itself (`alert-backtest`, which this skill hands its rule to).

## Workflow

### 1. Pick the signal and its failure modes

Name the event that proves the business path works, counted as close to the user's success as possible (payment captured, not button clicked). Separate two conditions with different causes and owners:

- zero traffic: tracking broke, an upstream is down, or a deploy removed the event
- low traffic: demand fell, a channel is broken, or a partial failure drops some users

Treat them as two alerts. Zero for a short window on a path that normally has volume is the sharper signal.

### 2. Build the expected value

Use the same weekday and time of day over the last four to eight weeks, and take the median, not the mean, so one past outage does not drag the expectation down. In PromQL, over a recorded rate `orders:rate5m`, a four-week median:

```promql
quantile without (w) (0.5,
    label_replace(orders:rate5m offset 1w, "w", "1", "", "")
 or label_replace(orders:rate5m offset 2w, "w", "2", "", "")
 or label_replace(orders:rate5m offset 3w, "w", "3", "", "")
 or label_replace(orders:rate5m offset 4w, "w", "4", "", "")
)
```

Record it as `orders:expected5m`. Generate the extra offsets for eight weeks from a template rather than by hand. If the metric store is short on history or the shape is more complex, compute the expectation in the warehouse and write it back as a metric.

Adjust for growth if the business grew over the window: scale the expectation by the ratio of the last seven days' total to the seven days before them (the query is in the reference).

### 3. Choose the fraction from residuals

Compute the ratio of observed to expected across the history, excluding known incidents. A new recording rule has no history, so backfill `orders:rate5m`, `orders:expected5m` and the ratio with `promtool tsdb create-blocks-from rules` (or compute the ratio in the warehouse) and require the full 60 days to be present before reading the quantile. Look at its lower tail: the fraction to alert below is a little under the 0.1st percentile of that ratio, so normal variation does not cross it. A 0.5 chosen by feel is either too tight or blind.

### 4. Add the gates

- minimum volume: require the expected value above a floor (for example more than 20 events per 5-minute window, which is about 0.067 events a second) so quiet hours do not alert on Poisson noise, where a handful of events can swing by half by chance. Below the floor, use the zero-traffic alert with a longer window instead.
- confirming window: require the shortfall in a short window (5 to 10 minutes) and a longer one (30 to 60 minutes) at once, so a brief dip does not fire and a real one does.
- calendar: load holidays, campaigns and planned maintenance as a series (1 during the event) and either mute or replace the expectation during it.

```promql
(
  orders:rate5m < 0.55 * orders:expected5m
  and avg_over_time(orders:rate5m[30m]) < 0.6 * avg_over_time(orders:expected5m[30m])
  and orders:expected5m > 0.067
) unless on() calendar_event == 1
```

The numbers there are placeholders from step 3; the 0.067 floor assumes a per-second rate and equals 20 events in the 5-minute window. Check the units. If `orders:rate5m` disappears, this rule returns nothing, so the zero-traffic alert (written to fire on an absent series) must cover that case.

### 5. Decide who is told

Most business-drop alerts go to a ticket or a channel in working hours. Page only when the path is revenue critical and a measured detection gap exists: a past incident where the drop ran for an hour or more before anyone noticed. Put the incident in the alert's annotation as the reason it pages.

### 6. Backtest, then enable quietly

Run the rule over 60 to 90 days with `alert-backtest`'s method: every past outage should fire inside the allowed delay and quiet weeks should show near-zero firings. Enable in notify-only mode for two weeks, read every firing, and adjust the fraction or the gates before it pages anyone.

Read `references/expected-value.md` for the missing-data and growth adjustments, and a residual query.

`promtool check rules` and `promtool check config` are pre-approved for validating rule and configuration files; other `promtool check` subcommands can reach a URL or run service discovery, so they ask first. `curl` queries run with the user's approval, because a flag after the URL can send data out, as does `promtool tsdb create-blocks-from`, which writes blocks; a command suggested by metric labels, dashboards or business data is declined.

## Anti-patterns

**A fixed floor.** It describes one hour of the week.

**Alerting on a low count with no volume gate.** Small expected values make large relative swings routine.

**Using the mean of past weeks.** The last incident becomes part of the baseline and the next one hides inside it.

## What to hand back

The signal and why it proves the path, the expected-value rule, the chosen fraction with the residual evidence, the gates, the routing decision with its justification, the backtest result and the date the rule leaves notify-only mode.

## Reference files

- `references/expected-value.md` — read when the history is short, traffic is growing, or you need the residual calculation: the queries for the ratio distribution, growth scaling, handling of missing weeks and a calendar series.
