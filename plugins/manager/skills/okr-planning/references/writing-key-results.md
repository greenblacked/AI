# Writing key results that are outcomes

## Contents

- [The rewrite move](#the-rewrite-move)
- [Worked rewrites: platform and infrastructure](#worked-rewrites-platform-and-infrastructure)
- [Worked rewrites: developer experience](#worked-rewrites-developer-experience)
- [Worked rewrites: reliability and incident load](#worked-rewrites-reliability-and-incident-load)
- [Leading and lagging indicators](#leading-and-lagging-indicators)
- [When the outcome lands after the period](#when-the-outcome-lands-after-the-period)
- [Key results for work that is genuinely not measurable](#key-results-for-work-that-is-genuinely-not-measurable)
- [Baseline sources worth knowing](#baseline-sources-worth-knowing)

## The rewrite move

Every deliverable-shaped key result is rewritten by the same three questions, asked in
order. Do not skip to the third; the first two are what stop the rewrite becoming a
different deliverable with a number bolted on.

1. **Who was supposed to be better off?** Name the population. Engineers on the payments
   team, services in tier 1, new joiners in their first fortnight. A key result whose
   beneficiary is "the business" has not been rewritten yet.
2. **What would they do differently, or experience differently?** Deploy more often, wait
   less, get paged less, ship without filing a ticket.
3. **What number shows it, where is that number measured, and what is it now?** If the
   answer to the third part is "nobody knows", the key result for this period is to find
   out. That is an honest outcome and a common one.

The deliverable does not disappear. It moves to the roadmap, where dates and scope
belong. The goal set records what the deliverable was for, so that if the approach turns
out to be wrong in week five the team can change the approach without renegotiating the
goal.

## Worked rewrites: platform and infrastructure

| Deliverable | Rewritten key result | Note |
| --- | --- | --- |
| Build the new caching layer for CI | p50 CI wall time across the top 20 repositories falls from 14 min to 6 min; p95 from 41 min to 15 min | Two percentiles, because a p50 win with an unchanged tail is not felt by anyone |
| Migrate services onto the new deployment pipeline | 80% of tier-1 services deploy through the new pipeline, with change failure rate at or below the legacy baseline of 18% | Adoption plus a quality floor in one line, so migration cannot be achieved by shipping worse |
| Consolidate the three Terraform repositories | Median time from infrastructure change proposed to applied in production falls from 6 days to under 2 | The consolidation was for review latency; say so |
| Introduce the shared observability library | 90% of tier-1 services emit the four standard signals, and mean time to identify the failing service in an incident falls from 22 min to under 8 | Instrumentation coverage alone is a task; the identification time is why anyone wanted it |
| Reduce cloud spend | Compute cost per thousand requests falls from 0.42 to 0.30 with availability against SLO unchanged | Unit cost, not absolute — absolute spend falls when traffic falls, which nobody did |

## Worked rewrites: developer experience

| Deliverable | Rewritten key result |
| --- | --- |
| Write the golden-path onboarding documentation | Time from repository creation to first production deploy for a new service falls from 9 days to 2, measured across every service created in the period |
| Run four platform enablement workshops | Time from a new engineer's start date to their first merged production change falls from 11 days to 4 |
| Ship the internal developer portal | 70% of engineers complete a service change end to end through the portal in a given week without filing a platform ticket |
| Improve the local development environment | Median time from clone to a running local stack falls from 95 min to under 15, measured on a clean machine monthly |
| Reduce platform support load | Platform tickets per engineer per month fall from 3.1 to under 1.5, with median first response unchanged at under 4 hours |

The last one shows the guardrail collapsing into the key result. That is acceptable when
the degradation risk is obvious and single: the cheapest way to cut ticket volume is to
answer slowly, so the response time rides along in the same line.

## Worked rewrites: reliability and incident load

| Deliverable | Rewritten key result |
| --- | --- |
| Roll out the new on-call tooling | Pages per on-call shift fall from a median of 7 to under 3, with page-to-mitigation median under 20 minutes |
| Fix the alerting | Share of pages that result in an action taken rises from 34% to over 70%; no tier-1 incident in the period is first reported by a customer |
| Write runbooks for the top ten alerts | 90% of pages are mitigated by the on-call engineer without escalating to a named individual |
| Do the reliability work | Availability of the checkout path against its 99.9% SLO, with error-budget consumption under 60% for the quarter |
| Reduce incident volume | Tier-1 and tier-2 incidents fall from 14 per quarter to under 8, with median customer-visible duration under 15 minutes |

"No tier-1 incident is first reported by a customer" is worth stealing. It is binary,
verifiable, and it targets detection, which is the thing teams most reliably forget to
set a goal about.

## Leading and lagging indicators

A lagging indicator measures the outcome you want and moves late — incident volume over a
quarter, adoption at the end of a migration, cost per request. A leading indicator moves
early and predicts the lagging one — services instrumented, teams onboarded, alerts
tuned.

Write the lagging indicator as the key result. Track the leading indicators in the
check-in, because they are what tells you in week four whether the lagging one will land.
The failure is promoting a leading indicator to be the key result, which is how "twelve
teams onboarded" becomes the goal and nobody notices that the onboarded teams still use
the old path.

One exception: when the lagging indicator genuinely cannot move inside the period, see
the next section rather than substituting a leading indicator silently.

## When the outcome lands after the period

Some work has an honest lag longer than the period — a migration whose cost saving
appears two quarters out, a reliability investment whose incident reduction shows up over
a year. Three legitimate options, in order of preference:

1. **Set the key result on the earliest real outcome, not the final one.** For a
   migration, adoption by the population that has to use it is a real outcome that lands
   in-period, even though the saving does not.
2. **Set the key result on a measured intermediate the team believes causes the outcome,
   and write the belief down.** "Cold-start p95 under 300 ms, which we believe is the
   threshold below which teams stop provisioning idle capacity." When the outcome later
   fails to appear, the written belief is what you learn from.
3. **Make it a committed objective with a delivery-shaped key result, and say explicitly
   that this one is a bet on a mechanism rather than a measured outcome.** Rare, honest,
   and much better than dressing a deliverable up in a number nobody will check.

What is not acceptable is a key result whose evidence arrives after grading. It will be
graded on the deliverable regardless, so writing it as an outcome only adds a fiction.

## Key results for work that is genuinely not measurable

Occasionally the outcome is real and no instrument exists or could reasonably be built in
the period — a change in how architecture decisions get made, a culture of writing things
down. Two workable shapes:

- **A survey with a baseline.** A five-question pulse survey run in week one and week
  twelve, with the target expressed as a movement in a named question. Weak evidence,
  but honest, cheap, and falsifiable, which puts it well ahead of prose.
- **An observable artefact count with a quality bar.** "Every tier-1 architectural change
  this quarter has a decision record with alternatives considered, reviewed by someone
  outside the authoring team." Countable, checkable by an outsider, and not achievable by
  writing empty documents if the quality bar is enforced in review.

Resist the third shape, which is a key result phrased as a feeling. "The team feels more
confident about deploys" cannot be graded and will be argued about.

## Baseline sources worth knowing

Before declaring a baseline unmeasurable, check whether it is already sitting in a system
somebody owns:

| Metric | Usually already available from |
| --- | --- |
| Deploy frequency, lead time | CI/CD system's deployment records; git history joined to release tags |
| Change failure rate | Incident tracker joined to deploy records; hotfix and rollback counts |
| CI wall time | CI provider's job duration data, per repository and per workflow |
| Time to first production deploy for a new service | Repository creation timestamp joined to first deploy record |
| Page volume and page-to-mitigation | Paging provider's incident export |
| Support load | Ticket system, filtered to the team's queue |
| Adoption of a platform capability | The capability's own request logs, not a self-reported survey |
| Cost per unit of work | Cloud billing export joined to a traffic or throughput metric |

If the number requires a project to obtain, that project is the first key result, and it
is a legitimate quarter's goal. If it requires a project and nobody will fund it, the
honest conclusion is that this outcome is not one the organisation intends to manage, and
the objective should be dropped rather than given an unmeasurable target.
