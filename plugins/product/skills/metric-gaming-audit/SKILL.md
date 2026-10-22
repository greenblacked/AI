---
name: metric-gaming-audit
description: "Stress-test product KPIs and key results for the cheap ways to hit them while harming customers: write the three cheapest moves that raise each metric while damaging the customer, pair each with a counter-metric and a data check that would expose it, require every key result to carry a baseline, written definition, source table and owner, and turn anything not measurable today into an instrumentation task before it counts. Use this skill whenever someone says \"review our product metrics\", \"our OKR got hit but nothing improved\", \"engagement is up but customers are unhappier\", \"can this KPI be gamed\" or wants a north-star metric checked. Not for drafting objectives and key results from scratch (okr-planning), service reliability targets (slo-design), engineering delivery metrics (delivery-review), or a sudden unexplained move in a number (metric-anomaly-triage)."
allowed-tools: Read, Grep, Glob
---

# Metric Gaming Audit

The audit is done when every metric in scope has a specification card (definition, source, baseline, owner), three named ways it could be hit while hurting customers, a counter-metric with a threshold for each, and a data check someone runs on a schedule. Metrics that cannot be measured today are marked as such and carry an instrumentation task, not a target.

The usual failure is a metric that is hit and means nothing. Support sets "time to first response under one hour", agents send an automatic acknowledgement, the number goes green, and customers wait as long as before. Nobody cheated deliberately; the cheapest path to the number was not the path to the outcome, and nothing was watching the gap. The audit's job is to find those paths before the target is set, so that hitting the number and helping the customer become the same thing.

## Scope

Use for: reviewing a set of product KPIs, a north-star metric or product key results before they are adopted; explaining a key result that was hit with no visible improvement; adding guardrails to a dashboard that drives decisions or pay.

Do not use for: writing objectives and key results from scratch (`okr-planning`); availability and latency objectives for a service (`slo-design`); delivery measures such as lead time or deployment frequency (`delivery-review`); a metric that moved suddenly and may be a measurement error (`metric-anomaly-triage`); adding the events a metric needs (`instrumentation`, after this audit has listed them).

## Workflow

### 1. Write a specification card for every metric

For each metric or key result, fill in:

| Field | What good looks like |
| --- | --- |
| Name and intent | The customer outcome it is a proxy for, in one sentence |
| Definition | Numerator, denominator, time window, inclusions and exclusions, in words a new analyst could implement |
| Source | The table or event it is computed from, and the query or model that computes it |
| Baseline | Its value over a stated recent period, computed with this exact definition |
| Target | Where it should be by when, if it has one |
| Owner | The person who answers for the number, and separately who may change the definition |

A key result with no baseline is a guess about a guess: nobody knows whether the target is ambitious or already met. A metric with no source today cannot be a key result yet; record it as an instrumentation task with an owner and a date, and use a measurable proxy or no target in the meantime. Do not let "we will measure it later" stand, because the later measurement is always defined to look good.

### 2. Write the three cheapest harmful ways to hit each metric

For each metric, ask: if a team were told only to move this number and nothing else, what are the three cheapest ways to do it that would make a customer worse off? Write them concretely. These prompts find most of them:

- **Change the denominator.** Exclude the hard cases, the unhappy segment, or the users who did not finish.
- **Change the definition.** Count a weaker action, widen the window, merge or split records.
- **Shift in time.** Pull next quarter's result into this one, delay the bad events past the measurement date.
- **Move the cost elsewhere.** Push work to the customer, to another team, or into a metric nobody watches.
- **Select the easy users.** Target the people who would have done it anyway.
- **Add pressure instead of value.** Notifications, defaults, nags and friction on the way out.

`references/gaming-patterns.md` has a catalogue of common product metrics with their usual gaming moves, counter-metrics and checks. Read it when filling this step, then add the moves specific to your product; the catalogue's entries are where to start, not the whole list.

### 3. Pair each move with a counter-metric and a data check

For every gaming move, name:

- **A counter-metric** that would get worse if the move happened, with a threshold: "time to resolution must not rise more than 10% from baseline". Pairing an effect with its counter-effect makes the cheap path visible on the same page as the target.
- **A data check** that detects the move directly, run on a schedule by someone other than the metric's owner: a query, a sample of records read by hand each month, or a reconciliation against a second source.

A counter-metric without a threshold is decoration. A check nobody runs is the same as no check.

### 4. Look at who controls the number

Gaming follows incentives and access. For each metric, record whether it feeds anyone's bonus, promotion case or team ranking, and who can change its definition or the query behind it. The team measured by a metric should not be the only party able to redefine it. Put definition changes under version control or a change log, with the metric's owner and an analyst outside the team both approving.

### 5. When a key result was hit and nothing improved

Run the step 3 checks over the period. Then ask three questions in order:

1. Did one of the listed gaming moves happen, deliberately or not? The data checks answer this.
2. Was the target met through a move nobody listed? Look at what changed in the numerator and the denominator separately.
3. Did the link between the proxy and the outcome break? A metric that once tracked customer value can stop doing so when the product changes.

Then retire, redefine or re-pair the metric, and record the lesson against its card so the next quarter's target starts from it.

## What to hand back

- A specification card per metric, with gaps marked.
- The audit table: metric, three gaming moves, counter-metric and threshold per move, data check, check owner and schedule.
- The instrumentation tasks for anything not measurable today, with owners and dates.
- A list of incentive and definition-control risks.
- For a post-hit review: which moves the checks found, and the decision on the metric.

## Anti-patterns

**Assuming good faith makes this unnecessary.** Most gaming is not cheating; it is people doing the cheapest thing the number rewards. The audit is about the metric, not the people.

**One counter-metric for everything.** "Customer satisfaction" as the guardrail for every metric is too slow and too coarse to catch a specific move. Each move gets the counter-metric it would actually disturb.

**Targets on metrics with no baseline.** The team cannot tell an achievement from a measurement change, and the first quarter's "result" becomes the next quarter's baseline.

**Definitions owned by the measured team.** A quiet change to an exclusion list moves the number further than a quarter of work.

**Instrument later.** A key result accepted before it can be measured is defined when the results are in, by the people whose results they are.

## Reference files

- `references/gaming-patterns.md` — read when listing gaming moves: common product and support metrics with their typical harmful shortcuts, the counter-metric each disturbs, and a check that detects it, plus the audit table template.
