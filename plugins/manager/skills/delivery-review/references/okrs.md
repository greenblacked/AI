# OKRs: writing, grading and the ways they die

## Contents

- [Shape](#shape)
- [The task-versus-key-result discriminator](#the-task-versus-key-result-discriminator)
- [Committed versus aspirational](#committed-versus-aspirational)
- [Grading](#grading)
- [Health metrics](#health-metrics)
- [Never tie OKRs to compensation](#never-tie-okrs-to-compensation)
- [Transparency](#transparency)
- [Review cadence](#review-cadence)
- [Failure modes](#failure-modes)

## Shape

Three to five objectives per team per period, each with three to five key results.
The limit is the mechanism, not a style preference: the value of the exercise is
deciding what not to do, and a list of eleven objectives has made no decision. A
team with more than five objectives has a backlog with a new heading.

**Objective** — qualitative, directional, memorable, and meaningful to someone
outside the team. "New services are production-ready without platform hand-holding."

**Key result** — quantitative, with a baseline and a target, verifiable by someone
who was not involved. "Median time from repo creation to first production deploy
falls from 9 days to 2." A key result without a baseline cannot be graded, only
argued about.

## The task-versus-key-result discriminator

If it can be achieved by performing an activity, it is a task.

| Task (not a key result) | Key result |
| --- | --- |
| Ship the new deployment pipeline | 80% of services deploy through the new pipeline, median lead time under 2 days |
| Run four enablement workshops | Time-to-first-PR for new joiners falls from 11 days to 4 |
| Migrate three services to the new platform | Platform hosts 60% of production traffic with error rate at or below the legacy baseline |
| Write the on-call handbook | Page-to-mitigation median under 20 minutes with no escalation to a named individual |

The task versions are all completable while the underlying situation is unchanged.
That is exactly the failure the format is designed to expose, and it is the most
common defect in a first draft. When reviewing a set, mark every key result that a
team could hit by working hard on the wrong thing.

Tasks are not worthless — they are the plan. They belong in the plan, under the key
result they are meant to move.

## Committed versus aspirational

Two different contracts, and grading them on one scale destroys both.

**Committed** — the team is expected to land these at 1.0. Resourcing, dates and
dependencies are treated as firm. A committed OKR at 0.7 is a miss and warrants a
conversation about what went wrong.

**Aspirational** — deliberately set beyond what is known to be achievable, to force
a different approach. Expected to land around 0.7. An aspirational OKR that lands
at 1.0 every period was mis-set, not over-achieved.

Label each objective explicitly at the point it is written. A set that is entirely
committed is a project plan; a set that is entirely aspirational leaves nobody
accountable for the things that genuinely must happen.

## Grading

Grade 0.0 to 1.0, derived from the baseline and target rather than assigned by
feel. For a key result moving a metric from 9 days to 2:

```text
landed at 4 days → (9 - 4) / (9 - 2) = 0.71
```

0.6-0.7 is the healthy target band for aspirational objectives. Consistent 1.0s
mean targets are being set safely, which costs more than it appears: the
organisation loses its main instrument for detecting over-cautious planning.

Grade the objective as the (usually unweighted) mean of its key results, then write
one paragraph of context. The grade is a conversation opener, not a verdict — the
paragraph explaining a 0.4 is where the actual learning is, and a set of grades
published without commentary trains people to optimise the number.

Grade everything, including things that were abandoned mid-period. A quietly
dropped objective that never appears in the grading is how an organisation stops
noticing that it consistently starts more than it finishes.

## Health metrics

Alongside the OKRs, track the things that must not break while pursuing them:
availability, latency, change failure rate, support backlog age, on-call load,
attrition, customer satisfaction.

Keep them beside the key results, not as key results. A key result is something you
are trying to move; a health metric is something you are trying not to break, and
the two need different responses. Promoting a health metric to a key result creates
pressure to improve something that was fine, at the expense of the objective. Not
tracking it at all is how a team hits every key result while the on-call rotation
quietly becomes unsustainable.

The useful framing when setting them: "if we achieve this objective and X has got
worse, we will regret it." X is a health metric.

## Never tie OKRs to compensation

This is the failure that ends the system outright, and it ends it in a predictable
sequence. Compensation attaches to grades. Teams set targets they know they can
hit. Grades cluster at 1.0. The grades now carry no information about the business,
so leadership stops reading them. The quarterly ritual continues for another year
and is then abandoned as "not working for us".

The same applies to performance review, promotion packets and any calibration
process. Ambition is only safely expressible when missing an aspirational target is
free.

Performance is assessed on judgement, contribution and impact — using the OKR
period as context, not the grade as an input. If someone asks for the grades as a
performance input, the honest answer is that supplying them destroys the data they
came for within one cycle.

## Transparency

Publish OKRs across the organisation, not just up the management chain. The
practical payoff is dependency discovery: team A's key result quietly depends on
team B's platform work, and this is far cheaper to find in week zero than in week
nine. Private OKRs also allow two teams to hold contradictory targets for months.

Publish the grades with the same reach as the objectives. Selective publication —
good grades shared, poor grades quietly not mentioned — teaches sandbagging just as
effectively as tying grades to pay.

## Review cadence

- **Weekly or fortnightly**: a short confidence check per key result, not a
  re-grade. "Still confident, at risk, off track" plus what changed. Cheap, and it
  surfaces problems while there is still time to act.
- **Mid-period**: an explicit decision point. Anything off track gets re-planned,
  re-resourced or dropped. Dropping with a recorded reason is a healthy outcome and
  should be treated as one.
- **End of period**: grade, write the context paragraph, and carry forward the
  learning — not automatically the objective. An objective repeated verbatim for
  three periods is a signal that it was never really funded.

## Failure modes

**OKRs tied to compensation.** Sandbagging within one cycle, then 1.0s, then
irrelevance.

**Key results that are tasks.** Everything is delivered, nothing changes, and the
team feels the process wasted its time — correctly.

**Too many objectives.** No decision was made about what not to do, so capacity is
allocated by whoever asks most persistently.

**No baseline.** The key result cannot be graded, so grading becomes negotiation.

**Committed and aspirational on one scale.** Either the committed work is treated as
optional or the aspirational work is set safely. Usually both.

**Cascading OKRs mechanically down the hierarchy.** Every team's objectives become a
restatement of their parent's, and local knowledge about what would actually move
the metric never enters the system. Align on the objective; let teams set their own
key results.

**Grades published with no commentary.** Trains people to manage the number rather
than explain the outcome.

**Health metrics promoted to key results.** Pressure lands on the thing that was
already fine.
