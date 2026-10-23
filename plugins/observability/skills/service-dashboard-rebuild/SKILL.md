---
name: service-dashboard-rebuild
description: "Rebuild a service dashboard nobody can use during an incident so it answers, in order, is it broken, for whom, where, and what changed: rows for the SLI and error budget; traffic, errors and latency split by the dimensions that separated outcomes in past incidents (route, version, region); dependencies as the caller sees them; saturation of the few resources that run out; change markers and pre-filtered log and trace links. Every panel title is a question, with units and the SLO line drawn. Validate by replaying the last two incidents; delete unused panels. Use this skill whenever someone says \"our dashboard has 80 panels and tells us nothing\", \"design the on-call dashboard for this service\" or \"what should be on the service overview\". Not for chart form (data-visualisation), slow queries (slow-dashboard-fix), paging rules (alert-design) or what to emit (instrumentation)."
allowed-tools: Read, Glob, Grep, Edit
---

# Service Dashboard Rebuild

Done means one page that an on-call engineer who has never seen the service can open during an incident and, within a few minutes, say whether users are affected, which slice is affected and which change or dependency is the likely cause.

The usual failure is a dashboard grown by accretion: each incident added a panel, nobody removed one, and the page now lists every metric the service exposes. It answers "what can be measured" rather than "what is wrong". The second failure is a page designed from the metrics available instead of from the questions asked, so the answer to "for whom" requires a different tool.

## Scope

Use for: the primary overview dashboard of one service, as used by on-call.

Do not use for: choosing chart types and colour (`data-visualisation`), dashboards that load slowly (`slow-dashboard-fix`), deciding what pages (`alert-design`), or deciding what the service should emit (`instrumentation`).

## Workflow

### 1. Collect what past incidents needed

Take the last five to ten incidents of this service, or of similar services if it has few. For each, write down the first questions asked, the query that finally found the cause and the dimension that separated good requests from bad ones (one route, one version, one region, one tenant tier, one dependency). These decide the splits; do not choose them from the list of labels. If a needed split has no label, record it as an instrumentation gap for `instrumentation` rather than faking it.

### 2. Lay out rows in the order on-call asks

Top to bottom, so the page reads as a triage procedure:

1. Is it broken? The SLI as a ratio of good over valid events with the SLO line, and the remaining error budget for the window with the burn rate over the short and long alert windows.
2. For whom, and where? Traffic, error ratio and latency percentiles, each split by the dimensions from step 1. Prefer a few lines to a stacked wall; show the top contributors and an "other".
3. What does it depend on? Each dependency as seen from this service: request rate, error ratio and latency of calls out, from the caller's client metrics, not the dependency's own dashboard. A dependency's green status page says nothing about what this service experiences.
4. What is running out? Saturation of the few resources that have actually run out in the past: connection pool use, queue depth and age, thread or worker use, CPU throttling, memory against the limit. Not every host metric.
5. What changed? Change markers over the panels above (see `change-event-correlation` if the stream does not exist yet), and links to logs and traces already filtered to this service, environment and the time range on the dashboard.

Read `references/panel-spec-and-replay.md` for a panel specification template, example queries and the replay worksheet.

### 3. Write every panel as a question

The title is the question, not the metric name: "Are checkout requests failing, and on which route?" rather than "http_requests_total". Then:

- units on the axis and in the title where they could be misread (requests per second, seconds, percent of valid requests)
- the SLO or alert threshold drawn as a horizontal line (most dashboard tools can show thresholds as lines), because a number without its limit makes the reader do arithmetic under stress
- one axis per panel; two axes with different scales make a correlation that is not there
- the same time range, variables and colours for the same dimension across the page
- a one-line description on each panel stating how to read it and what next to open if it is bad

### 4. Link out, not across

Every row ends in a link that opens the next tool already filtered: the log query for the service and the error class, a trace search for the slow route, the runbook section for this alert. Pass the service, environment and the dashboard's time range in the link rather than relying on the reader to retype them. Keep deep-dive panels (per-pod breakdowns, garbage collection detail) on a second dashboard linked from the saturation row, not on the overview.

### 5. Validate by replaying incidents

Take the last two incidents. Give the page, set to the time of each incident, to someone who has never seen the service, or role-play it yourself with only the page and the links. Record, for each: did the page show that something was wrong, could they name the affected slice, and did they reach the cause in the time a good on-call would accept? Every question the page could not answer is a gap; fix it by adding a split or a link, not a panel that repeats existing ones.

### 6. Remove what the replay did not use

Mark each panel as used in a replay, used in a past incident, or neither. Where the dashboard tool reports panel views, use that as a second signal; many do not, so the replay is the primary evidence. Delete or move to the deep-dive dashboard every panel in the third group. Keep the dashboard definition in version control so changes are reviewed and a future incident's new panel has to replace one.

## Anti-patterns

**One panel per metric.** Metrics are the inventory; the dashboard is the answer to a question.

**Averages without percentiles.** A mean hides the slow tail where users complain. Latency belongs in percentiles from a histogram.

**Per-host rows on the overview.** They answer "which machine" before "is it broken".

**Panels that need a legend to decode.** Name the lines and colour consistently.

**No owner.** An unowned dashboard grows panels again within a quarter.

## What to hand back

The incident questions gathered and the splits chosen, the row layout with each panel's question, query, unit and threshold, the instrumentation gaps found, the links wired, the replay results for two incidents, the panels removed with the reason, and the owner and review cadence.

## Reference files

- `references/panel-spec-and-replay.md` — read when specifying panels or running the replay: a panel template, example PromQL for the SLI, split error ratio and burn rate, and the replay worksheet.
