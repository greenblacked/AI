# Reviewing an alert set

Read this when auditing rules that already exist rather than writing new ones: how to
get fire counts and action rates out of the tooling, how to run the review so deletions
actually happen, and the error budget policy that decides what a spent budget means.

## Contents

- Pulling the numbers
- Scoring each rule
- The review meeting
- The deletion pull request
- Error budget policy
- Coverage gaps the audit will not find

## Pulling the numbers

Fire counts, from Prometheus itself. `ALERTS` is a synthetic series present for every
alert in the firing or pending state, so counting distinct firing episodes over 90 days
is a range query over it:

```promql
# How many distinct times each alert entered the firing state, last 90 days.
sum by (alertname) (
  changes(
    (max by (alertname) (ALERTS{alertstate="firing"}) or vector(0))[90d:5m]
  )
) / 2

# Total time each alert spent firing, in hours.
sum by (alertname) (
  count_over_time(ALERTS{alertstate="firing"}[90d])
) * 5 / 60
```

Adjust the resolution to your scrape interval. If retention is shorter than 90 days,
query whatever you have and say so in the review — a 30-day sample is still far better
than opinion, which is what the meeting will otherwise run on.

Notification counts, from Alertmanager:

```promql
sum by (integration) (increase(alertmanager_notifications_total[90d]))
sum by (integration) (increase(alertmanager_notifications_failed_total[90d]))
```

A non-zero failed count is its own finding: some fraction of your pages never arrived,
and nobody noticed. That needs a fix and an alert of its own.

Action counts do not exist in any tool. They come from the pager system's
acknowledgement notes, the incident channel, or — most reliably — from asking the rota
to annotate a printed list before the meeting. Budget twenty minutes of someone's time
per fifty rules; it is the cheapest data collection in the whole procedure and the only
number that decides anything.

Off-hours firing is worth pulling separately. A rule with a respectable action rate that
fires exclusively at 03:00 is a different problem from one that fires at 14:00, and the
fix — make the condition wait for working hours, because the action always did — is
different too.

## Scoring each rule

For each rule, record: fires, actions, action rate, off-hours fires, owner, whether a
runbook link resolves, and whether the severity routes anywhere distinct.

Verdicts, from the SKILL body: keep above ~50% action rate; one tuning attempt with a
re-review date between ~20% and ~50%; demote or delete below ~20%; delete this week for
anything with double-digit fires and no actions; investigate anything that has never
fired, because a rule that cannot fire and a rule that never needed to look identical.

Prove the never-fired case rather than arguing about it:

```bash
# Does the expression return anything at all right now?
promtool query instant http://prometheus:9090 'sum(rate(http_requests_total{job="checkout"}[5m]))'
```

An empty result means the selector matches no series — a renamed job label, a metric
that moved with a library upgrade, a typo. That is a rule which has been reporting
health it never measured.

## The review meeting

Quarterly, 45 minutes, with the on-call rota present. They pay the cost, so they hold
the vote.

1. Read out the five rules with the worst action rate. Decide each one on the spot:
   delete, demote to ticket, or tune once with a named owner and a re-review date.
2. Read out the never-fired list and the broken-runbook list. Both are usually fixable
   in the meeting.
3. Read out incidents in the period that were detected by a human rather than by an
   alert. Each one is a coverage gap; each gets a ticket, and the fix is usually an SLI,
   not another cause-based rule.
4. Count the alert set. If it grew this quarter, name what was deleted to make room. A
   set that only grows is on a path to being ignored entirely.

Decisions are recorded in the meeting or they did not happen. The failure mode is a
meeting that produces agreement and no diff.

## The deletion pull request

Deleting an alert feels risky in a way that adding one does not, so make the deletion
auditable enough that nobody has to feel brave:

```markdown
Delete NodeHighCPU

Fired 214 times in 90 days. Action taken 0 times. 61 of those fires were between
22:00 and 06:00. The condition is not user-visible: latency SLO burn was normal
during 212 of the 214 fires, and the two exceptions were already covered by
CheckoutErrorBudgetFastBurn, which paged first.

Coverage after this change: CPU remains on the checkout overview dashboard and is
linked from the fast-burn runbook. Saturation-driven latency is covered by the SLO.

Approved by: checkout on-call rota, 2026-02-11.
```

Retire in place if the team is nervous: route the rule to a low-traffic channel for one
cycle instead of the pager, then delete it when nobody has missed it. Do not leave it
there permanently — a rule routed nowhere is a deletion that still costs evaluation time
and still shows up in the count.

## Error budget policy

Burn-rate alerts imply a policy, and without one the tickets they raise get closed
unread. Write the policy once, get it agreed by whoever owns the roadmap, and reference
it from the slow-burn runbook:

- **Budget healthy.** Ship at normal pace.
- **Budget below 25% remaining.** Reliability work takes priority over feature work for
  the affected service until it recovers. Named, not vague: the specific tickets.
- **Budget exhausted.** Change freeze on that service except for reliability fixes and
  security patches, until the trailing window recovers.
- **Budget consistently untouched for two quarters.** The SLO is too loose to be
  informative. Tighten it, or admit the service does not need one.

The policy is what converts a slow-burn ticket into a decision. Without it the ticket is
a notification with extra steps.

## Coverage gaps the audit will not find

Counting fires tells you about rules that exist. Three gaps need a different method:

- **Silent failures.** Anything that fails without producing a metric — a cron that
  never started, an exporter that died, a consumer that stopped consuming. Enumerate the
  scheduled and asynchronous work per service and check each has an absence alert.
- **The alerting pipeline.** The watchdog, notification delivery failures, and rule
  evaluation failures. A dead pipeline scores a perfect zero fires on every rule.
- **Alerts that would not have fired.** The only honest test is to inject the failure and
  watch. That is the `game-day` skill, and the strongest possible outcome of an alert
  review is a scheduled exercise that tries to trip the three rules you are least sure
  about.
