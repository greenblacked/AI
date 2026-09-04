---
name: okr-planning
description: "Set goals for a team or organisation that change what people do, then review them honestly at the end — objectives as outcomes, key results as evidence with a baseline before a target, guardrails that must not degrade, a small defended number of them, confidence check-ins, and scoring whose real output is what you learned about predicting. Use this skill whenever someone is writing, rewriting or grading goals: OKRs, quarterly objectives, key results, a goal offsite, a mid-period reset, or an end-of-period retrospective — including phrasings like \"help me draft our Q3 OKRs\", \"these key results are just the roadmap again\", \"what target should we set\", or \"how do we score this\". Do not use it to read delivery metrics like DORA or flow (delivery-review), design the cadence the check-ins sit in (design-team-cadence), write a status update (status-update), record a technical decision (decision-record), or assess an individual's performance (growth-review)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# OKR Planning

A good goal set is short enough to recite, states outcomes the team does not fully control, and is specific enough that someone outside the team could tell at the end of the period whether it happened.

Goal-setting degrades into one of two failure modes with great reliability. Either the objectives restate the roadmap — ship the four things we were already going to ship — which measures activity, cannot be missed, and changes nothing about how anyone spends a Tuesday. Or they are aspirational to the point of being unfalsifiable, and everyone quietly ignores them by week three. Both produce a document nobody opens between the kickoff and the retrospective. The work of this skill is to force the outcome question at every step: what would be different in the world if this goal were met, and what number would show it. Where a number does not exist yet, say so rather than inventing one — a target picked before a baseline was measured guarantees the team spends the period arguing about the metric instead of the work.

## Scope

Use for: drafting a quarter's or a year's objectives and key results, rewriting deliverable-shaped key results into outcomes, choosing baselines and targets, setting guardrails, running the check-in rhythm, doing the mid-period reset, and scoring and retrospecting at the end.

Do not use for: reading delivery health metrics such as DORA or flow, which is `delivery-review`; designing the meetings the check-ins live in, which is `design-team-cadence`; writing the weekly or executive update that reports on progress, which is `status-update`; recording a technical decision, which is `decision-record`; or anything about an individual's performance, levelling or promotion, which is `growth-review` and must stay separate from this for the reason in step 5.

## Workflow

### 1. Establish the level, the period and the direction above

Name whose goals these are — one team, a platform group, a whole organisation — and the period. Then get the level above's goals in front of you before drafting. Not to decompose them, but so the finished set can be read against them.

Also establish what is already committed: the contractual dates, the compliance work, the migration that must land. Those are constraints on capacity, not objectives. A goal set that pretends the committed work does not exist will be abandoned the first week it collides with it.

### 2. Write objectives as outcomes

An objective is the outcome you want. A key result is the evidence it happened. Almost every defect in a goal set is a violation of that one sentence.

The test for an objective: could a reasonable person outside the team read it and say what would be different if it were met? "Improve the platform" fails. "New services reach production without platform hand-holding" passes.

The test for a key result: if it can be achieved by performing an activity, it is a task. When you find one, do not delete it — ask what launching that thing was supposed to change, and the answer is the key result. The deliverable then goes on the roadmap where it belongs.

| Deliverable (a task) | The question to ask | Key result (the outcome) |
| --- | --- | --- |
| Launch the new build cache | What does a faster build get us? | Median CI wall time for the top 20 repositories falls from 14 min to 6 min |
| Migrate 12 services to the new pipeline | What does the pipeline change? | Change failure rate across migrated services falls from 22% to under 10% with deploy frequency unchanged or better |
| Write the golden-path onboarding docs | Docs so that what happens faster? | Time from repo creation to first production deploy for a new service falls from 9 days to 2 |
| Roll out the new on-call tooling | What is the point of the tooling? | Pages per on-call shift fall from a median of 7 to under 3, with page-to-mitigation median under 20 minutes |
| Ship the internal developer portal | Who has to use it for it to have worked? | 70% of engineers complete a service change end to end through the portal in a week without filing a platform ticket |

The last row carries the general adoption pattern: an adoption key result names who, doing what, in what period, without help. "Portal launched" is a task; "portal used by 70% of engineers weekly" is an outcome; the difference is the entire value of the exercise.

`references/writing-key-results.md` has more worked rewrites, the shape of a leading versus lagging indicator, and how to write a key result for work whose outcome lands after the period ends. Read it when a key result resists rewriting.

### 3. Baselines before targets

A key result with no current value cannot be judged at the end, only argued about. Before writing a target, answer: what is it now, where is that measured, and who can pull the number without a project to build it.

Three honest cases:

| Situation | What to write |
| --- | --- |
| The number exists and is trusted | Baseline, target, source. "Median lead time 4.1 days (deploy dashboard, last 90 days) to under 2 days" |
| The number could be pulled but nobody has | Pull it before the kickoff. A goal set that starts with an unmeasured baseline starts with a dispute in escrow |
| The measurement does not exist | The first key result is the instrument: "A change-failure-rate measurement exists for all tier-1 services, reviewed weekly, with a stated 90-day baseline by week 4." No target this period |

Writing "improve by 20%" against an unmeasured baseline is the most common way a goal set becomes unusable. The number will be defined at the end, by whoever is most motivated, and the retrospective becomes a definition argument. Say plainly that the baseline is unknown and make measuring it the goal — that is a real quarter's work in most organisations and it is worth naming as such.

### 4. Keep the list small, and defend it

The ratio worth defending: three to five objectives for a team, three to five key results each. That is the mechanism, not a style preference — the value of goal-setting is what it excludes, and a list of twelve has excluded nothing. Twelve objectives is a roadmap wearing a costume, and it will be triaged informally by whoever is loudest in week six rather than deliberately now.

When a stakeholder wants a thirteenth, the question is which of the existing twelve it replaces. If the answer is none, the list was never the real priority set.

### 5. Set ambition deliberately, and keep it away from pay

Decide per objective whether it is committed or aspirational, and write which:

- **Committed** — expected to land in full. Missing one is a genuine failure that warrants a conversation about what went wrong. Contractual and compliance work belongs here or nowhere.
- **Aspirational** — set beyond what the team knows how to do, so that hitting roughly 70% is the success case. The point is that a target you know how to hit produces the plan you already had.

Stretch works only under one condition, and it is not negotiable in practice: goals must be separated from compensation and performance ratings. When the two are linked, people set targets they know they can beat, because the rational move is to sandbag. You then get honest-looking numbers attached to dishonest goals, and the entire instrument stops carrying information within one cycle. Separating them is the price of getting real ambition, and if the organisation will not pay it, set committed goals only and say why — that is a better outcome than pretending.

Individual performance is `growth-review`. A key result appearing in someone's rating is the failure mode above arriving by the side door.

### 6. Align without cascading

A team's goals should be legible against the level above — a reader should see how this set serves that direction — without being a mechanical decomposition of it. Cascade produces goals that were assigned rather than chosen, and an assigned goal has no owner in any sense that matters when the quarter gets hard.

Run it as a negotiation with two inputs and two rounds:

1. **Top-down direction.** Leadership states the direction and the constraints: what matters this period, what capacity exists, what must not slip.
2. **Bottom-up drafting.** Teams write their own objectives against that direction, including the ones leadership did not think of, because the team knows what is actually possible and what is already half-built.
3. **Reconciliation.** Read the drafts together. Look for direction with no team pursuing it, two teams pursuing the same outcome with different targets, and any goal whose achievement depends on a team that has not agreed to it.
4. **Cross-team dependencies get named in both sets.** A key result that depends on another team's work and appears in only one goal set is a commitment one party has not made.

The output of reconciliation is a written trade: what leadership dropped or funded, and what the team took on. Undocumented, the trade gets forgotten and the team is judged against the original ask.

### 7. Add guardrails

Beside the key results, list the health metrics that must not degrade while chasing them. Without guardrails, a goal to raise deploy frequency is achieved by shipping worse; a goal to cut cloud spend is achieved by deleting redundancy; a goal to cut onboarding time is achieved by skipping the security review.

Each guardrail is a metric, its current value, and the threshold that constitutes a breach. Guardrails are not scored — they are a stop condition. A breached guardrail means the approach is wrong, not that a point was lost.

| Objective is about | Guardrail candidates |
| --- | --- |
| Deploy frequency or lead time | Change failure rate, rework rate, failed-deployment recovery time |
| Cost or efficiency | Availability against SLO, p95 latency, on-call page volume |
| Onboarding or developer speed | Security review coverage, production incident rate from new services |
| Adoption of a platform capability | Support ticket volume to the platform team, legacy path still in use |

### 8. Run the period on confidence, not percentage complete

A short weekly or fortnightly check, five minutes per objective. Each key result gets a confidence that it lands: high, medium, low, or a 0-10 if the team prefers a number. Percentage complete is the wrong question, because a key result is an outcome and outcomes do not accrue linearly — 80% complete on a deliverable is common and 80% of the way to a latency target is usually fiction.

What the check-in is looking for is **movement in confidence**, especially downward, and a confidence that has been unchanged for six weeks, which usually means nobody has looked. Where the check-in sits in the week is `design-team-cadence`; how to read the delivery numbers underneath it is `delivery-review`; what to write in the update that comes out of it is `status-update`.

At the midpoint, run an explicit reset. Reality has changed: a reorganisation, a major incident, a customer commitment, a discovery that the approach does not work. Permitted moves, all of which must be written down with the date and the reason:

- Retarget a key result where the baseline turned out to be wrong.
- Kill a key result that has stopped mattering. This is the discipline most teams lack. Carrying a dead key result to the grading so it can be scored zero teaches everyone that the goals are a scoring exercise rather than a steering instrument.
- Add an objective only by dropping one.

An unrecorded change is indistinguishable at the end from a goal that was quietly rewritten to match the outcome.

## Objective block

Fill one of these per objective.

```markdown
## Objective: [The outcome, in a sentence someone outside the team understands]
Type: [Committed | Aspirational]
Owner: [Named person accountable for the outcome, not the tasks]
Why now: [One or two sentences. What changes for whom if this lands.]
Reads against: [The org or level-above goal this serves]

### Key results
| # | Key result | Baseline (source, window) | Target | Owner |
| --- | --- | --- | --- | --- |
| KR1 | [Outcome, measurable by an outsider] | [Value, where from, over what period, or "unmeasured — KR is to establish it"] | [Value] | [Name] |
| KR2 | | | | |
| KR3 | | | | |

### Guardrails (must not degrade)
| Metric | Current | Breach threshold |
| --- | --- | --- |
| | | |

### Dependencies
[Team, what is needed, by when, and confirmation that it appears in their goals too]

### Deliberately not doing
[What this objective excludes. If nothing, the objective is not a choice.]
```

## Scoring and retrospective block

Run at the end of the period. Score first, then get to the second half, which is the part that compounds.

```markdown
## Scores
| Objective / KR | Baseline | Target | Actual | Score (0.0-1.0) | Notes |
| --- | --- | --- | --- | --- | --- |

Committed objectives are pass or fail. Aspirational objectives score 0.0-1.0, with
0.7 as the healthy landing point.

## Guardrails
| Metric | Start | End | Breached? | What we did about it |

## Changes made mid-period
[Every retarget, kill and addition, with the date and the reason recorded at the time.]

## What we learned about predicting
- Where were we most wrong, and in which direction — too ambitious or too safe?
- Which key results moved because of our work, and which moved because the world did?
- Which key result did nobody look at between kickoff and now, and why was it in the set?
- What did we learn about how long this kind of work takes here?

## Calibration verdict
[If everything scored 1.0, the targets were set too low — say so plainly rather than
celebrating. If most scored under 0.3, the goals were disconnected from what the team
could influence, which is a planning failure and not a delivery one.]

## Carried into next period
[What we now know that changes how we set the next set. This is the durable output.]
```

The scores are the cheap half. The durable output is a better model of what this team can actually move in a quarter, which is the thing that makes the next set worth writing.

## Anti-patterns

**Key results that are deliverables.** "Launch X" is achieved by launching X, whether or not launching X helped anyone. The team optimises for the ship date, the outcome is never measured, and the goal set records that work happened, which was never in doubt.

**A target with no baseline.** The number gets defined at the end by whoever is most motivated, and the retrospective becomes an argument about the metric. Measure first, or make the measurement the key result.

**Twelve objectives.** No decision has been made, so the real prioritisation happens informally in week six under time pressure, by whoever is loudest, with no record.

**Goals tied to compensation.** Targets get sandbagged within one cycle. You get reliable full marks and a goal set that tells you nothing, and the loss is permanent because nobody will set an honest stretch target again.

**Cascading.** Mechanically decomposing the level above produces goals nobody chose, and a goal nobody chose has no owner when the quarter gets hard. Legible alignment, not decomposition.

**No guardrails.** A goal to raise deploy frequency is met by shipping worse; a goal to cut spend is met by deleting redundancy. The objective scores well and the system is worse.

**Grading a key result nobody looked at since kickoff.** Scoring it produces a number with no information in it. The finding is that it should not have been in the set, and that belongs in the retrospective rather than the score table.

**Rewriting the goal at the end to match the outcome.** It converts the one honest instrument the team had into a record of what happened, which they already knew. Record mid-period changes with dates as they are made, and the temptation disappears.

## Reference files

- `references/writing-key-results.md` — worked rewrites from deliverable to outcome across platform, developer-experience and reliability goals, leading versus lagging indicators, and how to write a key result whose outcome lands after the period. Read it when a key result resists rewriting.
