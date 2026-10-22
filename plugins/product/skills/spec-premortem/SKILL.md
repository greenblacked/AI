---
name: spec-premortem
description: "Attack a spec, PRD, launch plan or big bet before committing to it, then score the forecast afterwards. Assume it failed six months out; have each reviewer write reasons alone before any discussion; sort them into real risks, paper tigers and unspoken elephants; turn each real risk into a tripwire with a metric, threshold, date and owner; record three numeric predictions and score them at day 30 and day 90 so the team learns how well it forecasts. Use when someone asks to review a PRD or spec before sign-off, what could go wrong with a launch, to stress-test a plan, run a premortem, or check last quarter's bet against what was predicted. Not for recording the decision once made (decision-record), writing the spec itself (feature-spec), handing a design to engineers (design-handoff), or the write-up after an incident (postmortem)."
allowed-tools: Read, Glob, Grep
---

# Spec Premortem

Done means the spec has been attacked by reviewers who each wrote failure reasons alone before hearing anyone else, every reason is sorted as a real risk, a paper tiger or an elephant, every real risk is either fixed in the spec or watched by a tripwire with a metric, threshold, date and owner, three numeric predictions are on record, and both the tripwires and the predictions are checked at day 30 and day 90.

The usual failure is a review meeting that asks "any concerns?" The most senior person speaks first, everyone else adjusts, the spec owner answers each point as it lands, and the session ends with general reassurance and no list. The second failure is that a premortem's output is never checked: the risks were written, the launch happened, and nobody looked to see which ones arrived, so the team never learns whether its fears or its forecasts were any good. The premortem itself comes from Gary Klein; the scoring half is what turns it from a ritual into practice at forecasting.

## Scope

Use for: a spec, PRD, launch plan, pricing change, migration plan or any large bet before the commitment is made; scoring an earlier premortem's predictions and tripwires.

Do not use for: recording the decision and its alternatives, which is `decision-record` (the premortem feeds it); writing the spec in the first place, which is `feature-spec`; turning an approved design into a build spec, which is `design-handoff`; writing up an incident that already happened, which is `postmortem`; modelling security threats to a system, which is `threat-model`.

## Workflow

### 1. Prepare: the spec, the reviewers, the definition of failure

Send the spec at least a day ahead. Invite four to eight reviewers, including people who will live with the result and are not on the team: support, sales, operations, finance, an engineer from a dependent team. Name a facilitator who is not the spec owner, because the owner cannot both defend the plan and draw out attacks on it.

Write failure in concrete terms before the session: the spec's success metric missed by a stated amount at six months, or the launch rolled back, or the cost exceeded a figure. A vague "it didn't work" lets everyone imagine a different failure.

### 2. Write alone, before anyone speaks

Open with: "It is six months from now. This shipped and it failed, as defined. Write down why." Give ten minutes of silent, independent writing; each person aims for at least five reasons, as specific as they can make them. Collect them in writing.

Independence is the point. Once the first reason is spoken, everyone's list bends toward it, and the quiet reviewer who saw the real problem decides it is not worth raising. Writing first is cheap protection against anchoring and seniority.

### 3. Collect round-robin, without rebuttal

Go round the room taking one reason per person per turn until every list is exhausted, writing each where all can see it and merging exact duplicates. The spec owner may clarify a fact but does not argue a reason down in the room. Then ask once, directly: "What is the thing we all know and are not saying?" Offer an anonymous channel for it if the room is hierarchical.

### 4. Sort into real risks, paper tigers and elephants

| Category | What it is | What to record |
| --- | --- | --- |
| Real risk | Plausible, would cause the defined failure, and not already handled | Goes to step 5 |
| Paper tiger | Sounds alarming but evidence says it will not happen or will not matter | The evidence, so it is not re-litigated |
| Elephant | Known to many, unsaid: the team does not believe the goal, a dependency has no capacity, the sponsor's pet feature, a date nobody thinks is real | Who owns raising it, and by when |

A paper tiger needs evidence, not confidence; if nobody can produce any, it is a real risk. An elephant left in the notes without an owner will still be there at day 90.

### 5. Fix or tripwire every real risk

For each real risk, choose one:

- **Change the spec now** when the fix is cheap or the risk would be fatal.
- **Set a tripwire** when the risk can only be seen after launch. A tripwire has four parts: the metric (from data that exists today), the threshold that trips it, the date it is checked, and the owner who checks it. Add the action agreed in advance for when it trips: pause the rollout, roll back, cut scope, escalate.

A tripwire whose metric cannot be measured today is an instrumentation task first; record it as such rather than as a tripwire. The template is in `references/session-and-scoring.md`.

### 6. Record three numeric predictions

Before the decision, record three predictions about measurable outcomes, for example adoption at day 30, the success metric at day 90, and the cost or effort to launch. Express each as an 80% range ("we are 80% sure weekly active teams at day 90 will be between 120 and 260") or, for a yes-or-no event, a probability. Collect each reviewer's estimate independently, then record the median and the spread as well as the individual figures.

The predictions make the premortem checkable. A team that never writes numbers can always say it expected what happened.

### 7. Decide and hand over

The spec owner, with the decision-maker, decides: go as written, go with changes, or stop. Record the decision, the changes and the tripwires in the spec or in a `decision-record`. Put the day-30 and day-90 scoring sessions in the calendar now.

### 8. Score at day 30 and day 90

At each checkpoint:

1. Check every tripwire against its threshold; record tripped or not, and whether the agreed action was taken.
2. Score each prediction: did the actual fall in the 80% range? For probabilities, compute the Brier score, the squared difference between the probability and the outcome (1 or 0), averaged across predictions; lower is better.
3. List what went wrong that nobody wrote down. These unlisted failures are the most useful part of the review, because they show where the team's imagination was blind.
4. Compare categories with outcomes: did any paper tiger turn out to be real?

Over many premortems, about eight in ten outcomes should land inside their 80% ranges. Far fewer means the team is overconfident and should widen its ranges; nearly all means the ranges are too wide to be useful. Keep a running tally across premortems so this calibration is visible. The scoring sheet is in `references/session-and-scoring.md`.

## Output

```markdown
## Spec and definition of failure
[Link, decision being made, failure stated in numbers.]

## Reasons
[Every reason, with its category: real risk, paper tiger (with evidence), elephant (with owner).]

## Real risks
[Per risk: spec change made, or tripwire: metric, threshold, check date, owner, action.]

## Predictions
[Three predictions as 80% ranges or probabilities, individual estimates and median.]

## Decision
[Go, go with changes, or stop; scoring dates booked.]

## Scoring (day 30, day 90)
[Tripwires tripped, predictions in range, Brier score if used, unlisted failures.]
```

## Anti-patterns

**"Any concerns?"** An open floor anchors everyone on the first speaker. Silent writing first, every time.

**The owner rebutting live.** Each defended point teaches the room to stop raising the next one. Clarify facts only; sort afterwards.

**Tripwires with no date or owner.** A threshold nobody checks is a wish. Book the check and name the person.

**Never scoring.** Without day-30 and day-90 scoring the predictions were decoration. The scoring is what teaches the team to forecast.

## Reference files

- `references/session-and-scoring.md` — read when preparing the session and again at each scoring date: the facilitation script with timings, the reason and tripwire templates, the prediction sheet, and a worked scoring example including the Brier score.
