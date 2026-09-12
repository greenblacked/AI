---
name: alert-design
description: "Write, review or delete alerting rules so every page is user-visible, urgent and actionable — classify each signal as page, ticket or dashboard-only, alert on SLO burn rather than on the mechanism, write multiwindow multi-burn-rate Prometheus rules, give every alert an owner, a runbook link and a title naming what is broken for whom, and prune an existing rule set by how often anyone acted on it. Use this skill whenever someone is adding an alert, tuning a threshold, writing PrometheusRule or Alertmanager config, defining an SLO or an error budget policy, or complaining about pager fatigue — including \"should this page someone?\", \"our pager is out of control\", \"add an alert for high CPU\", or \"why didn't we get paged for that\". Do not use it for debugging an incident happening now, building dashboards, capacity planning, or choosing a monitoring vendor."
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(promtool:*), Bash(amtool:*), Bash(kubectl:*), Bash(git:*)
---

# Alert Design

A good alert set is one where every page means a human must do something now, and where nothing that matters to a user can fail silently. Those two properties fight each other, and the whole job is holding both at once.

Alerting is where good intentions turn into pager fatigue. Every incident ends with someone saying "we should have had an alert for that", and the alert they add is almost always cause-based — CPU above 80%, a queue over 1000, a pod restarting — because that is what they were looking at when they found the problem. Each one is a permanent tax on whoever is on call, paid nightly, forever, for a condition that usually resolves itself. The failure mode is not one bad alert; it is the aggregate. Once a rota has learned that most pages are noise, the response time on the real page collapses, and a team that ignores its pager is worse off than a team with no alerting at all, because it believes it is covered. So the bias throughout this procedure is deletion: the default answer to "should this page?" is no, and the burden of proof sits with the alert.

## Scope

Use for: deciding whether a signal should page, ticket, or only sit on a dashboard; writing or fixing a Prometheus, Alertmanager, Datadog or CloudWatch rule; defining SLO burn-rate alerts and an error budget policy; adding runbooks, owners and severities to an existing rule set; auditing a quarter of pages and deleting what nobody acted on; adding deadman, absence-of-data and dependency-suppression coverage.

Do not use for: diagnosing an incident that is burning right now (that is `k8s-triage`), designing dashboards, capacity planning, choosing between monitoring vendors, or writing up the incident afterwards (that is `postmortem`).

## The gate

Page a human only when both halves hold:

1. **User-visible.** A person outside the team is having a worse time right now, or will be before the next working hour. Not "a component is unhealthy" — a redundant component being unhealthy is exactly what redundancy is for.
2. **Requires action now.** A human doing something in the next few minutes changes the outcome. If the system will recover on its own, or if the fix has to wait for business hours anyway, waking someone buys nothing.

Everything else is a ticket or a dashboard. Classify explicitly, out loud, for each signal — write the classification down next to the rule, because an unclassified alert always drifts upward into a page.

| Route | Criteria | Where it goes |
| --- | --- | --- |
| **Page** | User-visible and actionable now. Fast SLO burn, hard-down dependency with no failover, data loss in progress, a deadman that stopped. | The pager, 24/7, with a runbook. |
| **Ticket** | Real degradation, but the response can wait until working hours. Slow SLO burn, a certificate 21 days from expiry, a disk that will fill in six days, a single node degraded behind redundancy. | The team's queue, with an owner and an SLA. |
| **Dashboard only** | Diagnostic. CPU, memory, queue depth, GC pauses, cache hit rate, per-instance latency. Useful when you are already looking; worthless as an interrupt. | A panel, plus a link from the runbook of the alert it explains. |

If a signal does not fit any row, it belongs nowhere. That is a valid outcome and the most common correct one.

## Workflow

### 1. Name what a user experiences when this goes wrong

Before touching a query, write one sentence: "when this fires, a *user* is unable to *do a thing*." If that sentence needs the word "server", "node", "pod", or "queue" to make sense, you are about to write a cause-based alert. Go up a level until the sentence is about a request that failed or an operation that took too long.

If no user-facing sentence exists — the condition is genuinely internal, like a saturating worker pool — the honest answer is a ticket or a dashboard panel, not a page with a lower severity.

### 2. Alert on the symptom, not the mechanism

There is one canonical exception worth encoding: a cause-based alert is justified when the cause is *imminent and unrecoverable* — a disk that will be full in four hours, a certificate expiring on Saturday, a licence quota running out. Those page (or ticket) because by the time the symptom appears it is too late to prevent it.

Everything else is symptom-first. The mechanism belongs on the diagnosis dashboard the runbook links to. The test: if the mechanism changes next quarter — you move from VMs to a serverless runtime, or swap the queue — does the alert still describe something a user cares about? A symptom alert survives the migration; a cause alert has to be rewritten, and usually is not.

### 3. Define the SLI and SLO the alert burns against

An availability or latency alert needs a ratio, not a raw count. The SLI is `good events / valid events` over a window; the SLO is the target for that ratio; the error budget is `1 - SLO` over the compliance period, typically 30 days.

Record the three explicitly before writing the rule:

```text
SLI:  sum(rate(http_requests_total{job="checkout",code!~"5.."}[5m]))
      / sum(rate(http_requests_total{job="checkout"}[5m]))
SLO:  99.9% over 30 days
Budget: 0.1% of requests — about 43 minutes of full outage, or a longer partial one
```

A latency SLI is a ratio too — the fraction of requests served under a threshold — not an average or a p99 value. `histogram_quantile` on a dashboard, a threshold ratio in the alert.

### 4. Write the multiwindow, multi-burn-rate rules

Burn rate is how fast you are consuming the error budget relative to the rate that would exactly exhaust it over the compliance period. Burn rate 1 spends the whole 30-day budget in 30 days. Burn rate 14.4 spends 2% of it in one hour, which is worth waking someone for; burn rate 1 spends 2% in 14.4 hours, which is not.

Two windows per severity, joined with `and`. The long window decides whether the burn is real; the **short window, one twelfth of the long one, exists so the alert resets quickly** once the error rate drops. Without it a one-minute total outage keeps a 1-hour-window alert firing for the rest of that hour, long after recovery — which trains people to ignore whether an alert is still firing.

The Google SRE workbook's default table for a 30-day period:

| Severity | Long window | Short window | Burn rate | Budget consumed before it fires |
| --- | --- | --- | --- | --- |
| Page | 1h | 5m | 14.4 | 2% |
| Page | 6h | 30m | 6 | 5% |
| Ticket | 1d | 2h | 3 | 10% |
| Ticket | 3d | 6h | 1 | 10% |

```yaml
groups:
  - name: checkout-slo
    rules:
      - alert: CheckoutErrorBudgetFastBurn
        # 14.4x burn over 1h, confirmed by the 5m window so it clears on recovery.
        expr: |
          (
            job:slo_errors_per_request:ratio_rate1h{job="checkout"} > (14.4 * 0.001)
            and
            job:slo_errors_per_request:ratio_rate5m{job="checkout"} > (14.4 * 0.001)
          )
        for: 2m
        labels:
          severity: page
          team: checkout
        annotations:
          summary: "Checkout is failing for customers — 2% of the 30-day error budget in under an hour"
          description: "Error ratio {{ $value | humanizePercentage }} against a 99.9% SLO."
          runbook_url: "https://runbooks.internal/checkout/error-budget-fast-burn"
          dashboard_url: "https://grafana.internal/d/checkout/overview"

      - alert: CheckoutErrorBudgetSlowBurn
        expr: |
          (
            job:slo_errors_per_request:ratio_rate1d{job="checkout"} > (3 * 0.001)
            and
            job:slo_errors_per_request:ratio_rate2h{job="checkout"} > (3 * 0.001)
          )
        for: 15m
        labels:
          severity: ticket
          team: checkout
        annotations:
          summary: "Checkout is burning error budget 3x faster than sustainable"
          runbook_url: "https://runbooks.internal/checkout/error-budget-slow-burn"
```

Precompute the ratios as recording rules (`job:slo_errors_per_request:ratio_rate1h`) rather than repeating a long expression four times. Four copies of a query is four places to forget the same fix.

Low-traffic services break this maths: at 20 requests an hour a single failure is 5% of the window and every burn-rate alert becomes a coin flip. Read `references/burn-rate.md` before writing rules for a service under roughly one request per second — it covers generated-traffic probes, longer windows, and when to give up on a ratio SLO entirely.

### 5. Use the golden signals and RED/USE as a coverage check

The four golden signals — latency, traffic, errors, saturation — and their derivatives (RED: rate, errors, duration, for request-driven services; USE: utilisation, saturation, errors, for resources) are a checklist for *gaps*, not a list of alerts to create. Walking them tells you that nothing watches the queue consumer's error rate; it does not mean you should page on utilisation.

Run the check per user-facing journey, not per service: for checkout, is there an SLI for latency, one for errors, one for freshness or correctness where it applies? Saturation almost always resolves to a ticket or a dashboard panel, because saturation without user impact is capacity information.

### 6. Set thresholds and durations from history, not from round numbers

- Percentiles, never averages. An average latency hides the tail that is the actual user experience; a p99 that doubled while the mean stayed flat is a real regression and an average will not show it.
- `for:` has to outlive a scrape gap. With a 30s scrape interval, `for: 1m` fires on two missed scrapes. Two to five minutes is the usual floor for a page; the multiwindow rules above already carry most of that job in the short window, so keep `for:` small there rather than stacking delay on delay.
- Pick the number from the incident record. Pull the last few months of real incidents for this service, look at the SLI value during each, and set the threshold below the quietest genuine incident and above the noisiest healthy period. If those two ranges overlap, the metric does not separate good from bad and no threshold will fix it — find a better SLI.
- 80% is not a threshold, it is a default someone typed. Say why the number is the number, in a comment on the rule.

### 7. Alert on absence, and on the alerting pipeline itself

A dead exporter reports nothing, and nothing looks exactly like healthy to a `> threshold` rule. Cover both:

```yaml
      - alert: CheckoutMetricsMissing
        expr: absent(up{job="checkout"}) or (sum(rate(http_requests_total{job="checkout"}[10m])) == 0)
        for: 10m
        labels: {severity: page, team: checkout}
        annotations:
          summary: "No checkout telemetry for 10 minutes — the service or its exporter is gone"
          runbook_url: "https://runbooks.internal/checkout/no-telemetry"

      - alert: Watchdog
        # Always firing, by design. Routed to a heartbeat monitor that pages when it stops.
        expr: vector(1)
        labels: {severity: none}
        annotations:
          summary: "Deadman switch: proves the alerting pipeline is alive end to end"
```

The watchdog is the alert that catches the failure nobody else can: Prometheus down, Alertmanager misconfigured, the notification integration silently rejecting. It must be routed *out* of the same pipeline, to an external heartbeat service that pages when the pulse stops. A deadman that only exists inside the system it monitors proves nothing.

Also alert on the rule evaluation itself — Prometheus rule evaluation failures, notification delivery failures, and configuration reload failures. A rule that stopped evaluating is an alert you no longer have.

### 8. Give every alert an owner, a runbook, and a title that says what is broken for whom

Labels route. Annotations explain. Both are required, and the failure is nearly always missing annotations.

- `severity:` maps to a real routing decision in Alertmanager and nothing else. If `warning` and `critical` both go to the same Slack channel, you have one severity and a lie.
- `team:` or `service:` decides who receives it. An alert with no owner is a page delivered to a group chat, where responsibility diffuses.
- `summary:` is what a person reads at 3am on a phone screen. "Checkout is failing for customers" beats "HighErrorRate on job=checkout". Name the user impact and the service.
- `runbook_url:` is not optional. The runbook says: what this means, the three things to check first, the two safest mitigations, and who to escalate to. An alert whose runbook link 404s is worse than no link — the responder spends time discovering it is dead.
- `dashboard_url:` takes the responder from the symptom to the mechanism, which is where the cause-based signals you did not alert on actually live.

### 9. Route so one root cause pages once

Forty pages from one failure is the same information delivered forty times, and it buries the one page that named the cause.

- **Group** by the axis that shares a response: `group_by: [alertname, cluster, service]`. Grouping on instance defeats the point.
- **Wait** before sending: `group_wait: 30s` lets a correlated burst arrive together, `group_interval: 5m` batches updates, `repeat_interval: 4h` stops the same open alert re-paging every ten minutes.
- **Inhibit** the dependents: a cluster-down alert suppresses the per-service alerts inside it, matching on the shared label.

```yaml
inhibit_rules:
  - source_matchers: [severity = "page", alertname = "ClusterUnreachable"]
    target_matchers: [severity =~ "page|ticket"]
    equal: [cluster]
```

Dependency suppression only works if the dependency is expressed in labels. If your services do not share a `cluster`, `region` or `dependency` label, add it before writing inhibition rules — an inhibition matching on nothing suppresses nothing, and it fails silently.

### 10. Review the alert set you already have

Adding alerts is the easy half. The review is what keeps the set trustworthy.

Pull the last 90 days of pages from the alerting system and, for each rule, answer three questions: how many times did it fire, how many times did a human take an action because of it, and what was that action. The action rate is the only number that matters — "action taken" means a mitigation, a rollback, an escalation or a code change, not acknowledging the page and watching it clear.

| Action rate over 90 days | Verdict |
| --- | --- |
| Above roughly 50% | Keep. This alert is doing its job. |
| Roughly 20-50% | Tighten it once — a better SLI, a longer window, a dependency inhibition. One attempt, with a date to re-review. |
| Below roughly 20% | Demote to a ticket, or delete. Do not tune. |
| Fired more than about 10 times with zero action | Delete this week. It is training the rota to ignore the pager. |
| Never fired in 90 days | Ask whether it *can* fire. An untested rule with a typo in a label selector is indistinguishable from a quiet system. |

Those cut-offs are judgement calls, not physics — a rule that fires twice a year and both times caught data loss is worth keeping at a 100% action rate on a tiny sample, and a rule that fires nightly at 40% is still ruining sleep. Use the numbers to force the conversation, then decide with the on-call rota in the room, because they are the ones paying.

Delete in a pull request that names the rule, its fire count, its action count and its owner's sign-off. Deletions that happen quietly get reverted after the next incident by someone who does not know they were deliberate.

`references/alert-review.md` has the queries for pulling fire counts out of Prometheus and Alertmanager, plus the review meeting shape. Read it when auditing an existing rule set rather than writing a new one.

## Signal to classification to action

| Signal | Classification | Action |
| --- | --- | --- |
| SLO error budget burning at 14.4x over 1h, confirmed at 5m | Page | Multiwindow burn-rate rule, severity page, runbook links the diagnosis dashboard. |
| SLO burning at 3x over 1d | Ticket | Same shape, severity ticket, into the team queue. |
| Checkout p99 latency past the SLO threshold ratio, sustained | Page | Latency SLI as a ratio of requests under threshold, not a p99 value comparison. |
| CPU above 80% on a node | Dashboard only | Delete the alert. Link the panel from the latency runbook. |
| Memory climbing steadily on one replica, no user impact | Dashboard only, or ticket if it will OOM within days | Ticket the leak with a projection; do not page on the derivative. |
| Queue depth rising | Dashboard only | Page on consumer lag against an SLO for freshness, if freshness is user-visible. |
| Pod restarting, replicas still serving | Dashboard only | Redundancy is working. Page only when replicas available drops below the serving floor. |
| All replicas of a singleton dependency unreachable | Page | Symptom-level rule on the dependent service's SLI, plus inhibition so it pages once. |
| No metrics from a job for 10 minutes | Page | `absent()` plus a zero-traffic check. |
| Certificate expiring in 21 days | Ticket | Renewal ticket with a due date; page at 3 days only if renewal is manual. |
| Disk projected full in 6 days | Ticket | Ticket with the projection in the annotation. |
| Disk projected full in 4 hours | Page | The imminent-and-unrecoverable exception. |
| Backup job did not run last night | Ticket, or page if the RPO is hours | Alert on the *absence* of a successful run, not on a failure event. |
| Watchdog alert stopped arriving at the heartbeat monitor | Page | The alerting pipeline is broken; treat as loss of all coverage. |
| A single failed request | Nothing | Not an alert. It is a ratio's numerator. |

## Output format

Report an alert design or review in this shape:

```markdown
## Classification
[Page / ticket / dashboard-only, and the one sentence about the user that justifies it.]

## SLI and SLO
[The ratio, the target, the compliance period, and the budget in human terms.]

## Rules
[The YAML, with recording rules if the expression repeats. Windows and burn rates named.]

## Routing
[Severity to receiver mapping, group_by, inhibition against the dependency.]

## Annotations
[Summary as a responder reads it, runbook URL, dashboard URL, owner label.]

## What this does not cover
[The failure modes still invisible — absence of data, the alerting pipeline, a dependency
with no label to inhibit on. Say so rather than implying coverage you did not build.]

## Deletions
[Rules this replaces or retires, with their fire and action counts. Omit if none.]
```

## Anti-patterns

**Alerting on the cause.** Pages on CPU, memory, restarts and queue depth fire when nothing is wrong and stay quiet when something is. They also multiply: every mechanism gets its own rule, and a single user-facing failure arrives as fifteen pages that name none of it. Alert on the SLO burn; put the mechanism on the dashboard the runbook links to.

**The alert with no runbook.** The responder starts from zero at 3am, on a phone, on the worst night of the quarter. The cost is measured in minutes of extra outage per page, forever, and it lands hardest on the newest person on the rota. A rule with no `runbook_url` should not merge.

**Severity that routes nowhere.** Three severities that all deliver to the same channel is one severity plus documentation debt. It also removes the mechanism that would let you demote a noisy page rather than delete it, so the noisy page stays. Every severity must name a distinct receiver, or be merged into the one it duplicates.

**Tuning the threshold instead of deleting the alert.** The threshold moves from 80% to 85%, the page rate halves, and everyone declares victory — but the alert was never actionable at any threshold, so half as many useless pages is still a useless alert plus a false sense of having fixed it. Tune once, on a rule with a real action rate. Otherwise delete.

**Averages.** An average absorbs the tail, which is where users live. A service can hold a flat mean latency while a tenth of requests time out. Use percentiles for reporting and a good-events ratio for alerting.

**No deadman.** Every alert in the system is conditional on the alerting system working. Without a watchdog routed to an external heartbeat monitor, a Prometheus that died at 2am reads identically to a perfectly healthy platform, and you find out from a customer.

**One root cause, forty pages.** With no grouping or inhibition, a dependency failure pages every service behind it. The responder spends the first ten minutes deduplicating, and the one page that named the actual cause scrolls past. Group on the axis that shares a response and inhibit dependents on a shared label.

**Adding an alert as a postmortem action item without deleting one.** The alert set grows monotonically after every incident, each addition individually reasonable. Make the review in step 10 a standing item so the set can also shrink — and prefer a `game-day` exercise that proves the existing alert would have caught it over a new rule that duplicates it.

## Reference files

- `references/burn-rate.md` — read when writing or debugging SLO burn-rate rules: the burn-rate arithmetic, window and threshold tables for periods other than 30 days, recording-rule scaffolding, and what to do for a low-traffic service where the ratio is too noisy to alert on.
- `references/alert-review.md` — read when auditing an existing alert set: the Prometheus and Alertmanager queries that produce fire counts and action rates, the review meeting shape, the deletion pull-request template, and the error budget policy that decides what happens when the budget is spent.
