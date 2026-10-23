---
name: metric-movement-decomposition
description: "Explain why a ratio metric moved — conversion, average order value, churn — with arithmetic instead of a story: rule out data breaks first (volume, null rate on the segment column, a tracking release, an incomplete latest day), check the move is outside normal variation, split the change into rate effect within segments and mix effect from shifting segment shares with a Kitagawa decomposition, rank segments by contribution, test for Simpson's paradox by recomputing on last period's mix, and report the top three contributors with the sums. Use when conversion fell 8% or someone asks whether a drop is mix or performance. Not for two reports disagreeing on one figure (metric-reconciliation), a join-inflated total (join-fanout-hunt), a figure still changing as late data lands (late-data-maturity) or whether the move is real or a tracking artefact (metric-anomaly-triage)."
allowed-tools: Read, Grep, Glob
---

# Metric Movement Decomposition

This is finished when the change in a ratio metric between two periods is split, exactly and with nothing left over, into how much came from segments' own rates moving and how much from the mix of segments shifting, the top three contributors are named with the numbers behind them, and the data has been shown not to be the cause.

The usual failure is the first plausible story. Conversion fell 8%, someone notices mobile conversion is lower, and "mobile got worse" goes into the weekly review — when mobile's rate actually rose and the fall came entirely from more traffic arriving on mobile. An aggregate ratio moves when segment rates move, when segment shares move, or both, and the two need opposite responses: a rate problem is fixed in the product, a mix shift is usually a traffic or marketing change that may not need fixing at all. The other failure is decomposing a broken number: a tracking release that drops half of one platform's events produces a clean-looking decomposition of an artefact.

## Scope

Use for: a ratio metric that moved between two periods — conversion rate, average order value, churn or retention rate, click-through, defect rate, cost per order — and someone needs to know where the movement came from; checking whether a fall is a Simpson's paradox; preparing the "why did it move" section of a metric review.

Do not use for: two reports that disagree on the same figure for the same period, which is `metric-reconciliation`; a total that is too high because of a join, which is `join-fanout-hunt`; a latest-day figure still rising as late rows land, which is `late-data-maturity`; whether the move is real or a tracking or pipeline artefact, which is `metric-anomaly-triage`; drawing the chart for the result, which is `data-visualisation`; designing the alert that should have flagged the move, which is `alert-design`. Decomposition says where the change sits, not what caused it: proving that a launch or a price change caused it needs an experiment or a causal analysis, not this.

## Workflow

### 1. Write the metric as a numerator over a denominator

State it exactly: "orders divided by sessions", "revenue divided by orders", "accounts cancelled in the month divided by accounts active at its start". Pick two periods of the same length and the same weekdays — this week against last week, or against the same week last year when seasonality is strong — and make sure the later one is complete. Record the numerator, denominator and ratio for each period, the absolute change (in percentage points for a rate) and the relative change.

A metric that is not a ratio of two additive totals (a median, a percentile, a distinct count across segments that overlap) does not decompose this way. Say so and stop, rather than forcing it.

### 2. Rule out data breaks first

Check, for both periods and the weeks before them:

- Daily numerator and denominator volumes, each against its own recent range. A rate that moved because its denominator jumped 30% overnight is usually a tracking or filtering change, not behaviour.
- The share of the denominator with a null or unknown value in each column you might segment by. A rising unknown share moves the mix by itself.
- The release log for the window: app and site releases, tag manager changes, consent banner changes, bot filtering rules, event schema changes.
- Whether the latest day is complete, by comparing its row count at this hour with earlier days at the same hour.

If you find a break, it is the answer: report it, the date it started and the segment it touches, and stop. Read `references/decomposition.md` for the checks as queries.

### 3. Check that it moved at all

Compute the same period-on-period change for each of the previous eight to twelve periods. If this change sits inside that range, there is nothing to explain; report that it is within normal variation and show the range. Small denominators make this common: a segment with a few hundred sessions a week moves by whole percentage points on noise alone.

### 4. Choose the segmentation

A segmentation for decomposition has to be on the denominator's unit (sessions by device, orders by country), mutually exclusive, and exhaustive, with an explicit unknown segment so the shares sum to one. Keep it to about ten segments and roll the tail into "other": small segments have noisy rates that dominate the ranking without meaning anything.

Try one dimension at a time — device, channel, country, new against returning, app version — and keep the one where the change concentrates in the fewest segments. The split between rate and mix depends on the dimension chosen, so the report names it.

### 5. Decompose into rate and mix

With segment shares of the denominator `w` and segment rates `r`, the aggregate is the share-weighted sum of segment rates. For periods 0 and 1, the symmetric (Kitagawa) decomposition gives each segment two terms:

- rate effect = (r1 − r0) × (w0 + w1) / 2
- mix effect = (w1 − w0) × ((r0 + r1) / 2 − R̄), where R̄ is the average of the two aggregate rates

Summed over segments, rate and mix effects equal the aggregate change exactly, with no interaction term. Check that they do: a sum that misses means the segments are not exhaustive or the segment denominators do not add up to the metric's denominator. Centring the mix effect on R̄ changes no total, but it stops a segment that gained share at an average rate from showing a large contribution offset by small negatives everywhere else.

Rank segments by the absolute value of rate plus mix. Read `references/decomposition.md` for the SQL, new and vanished segments, and a worked example.

### 6. Test for Simpson's paradox

Recompute period 1's aggregate with period 0's shares: the sum of w0 × r1. If that counterfactual moved the opposite way from the real aggregate — or most segments' rates rose while the aggregate fell — the headline is mix, and the first sentence of the report has to say so, because "conversion fell" will otherwise be read as "the product got worse".

### 7. Drill one level, then stop

If the top contributor is a rate effect in one segment, repeat steps 4 to 6 inside that segment with a second dimension. Stop at two levels: below that, segments are small enough that the ranking is noise.

### 8. Report the top three with the arithmetic

Name the top three contributors, each with its shares, rates, rate effect, mix effect, and share of the total change, and show that all segments together sum to the change. Put the data-break checks and the noise check above the table, so a reader knows the number was worth decomposing.

## Output format

```markdown
## Movement
[Metric as numerator/denominator. Periods. R0, R1, change in points and per cent.]

## Data checks
[Volumes, unknown share, release log, latest-day completeness: each clear, or the break found.]

## Normal range
[This change against the previous N periods' changes.]

## Decomposition by [dimension]
| Segment | w0 | w1 | r0 | r1 | Rate effect | Mix effect | Total | Share of change |
Sum of all segments: [equals the change].

## Simpson check
[Period 1 rates at period 0 mix: value and direction.]

## Top three
[One sentence each, with the numbers.]
```

## Anti-patterns

**Reading segment rates side by side.** "Mobile converts worse" says nothing about change. Compare each segment with itself across periods, weighted by its share.

**Decomposing before checking the data.** A dropped event on one platform decomposes into a confident rate effect on that platform. Rule out breaks first.

**Uncentred mix effects in the ranking.** Without centring, the fastest-growing segment always looks like the biggest contributor. Centre on the average aggregate rate.

**Twenty tiny segments.** A segment with forty orders can swing its rate by ten points on one bad day and top the ranking. Roll the tail up.

**A cause in the conclusion.** "The checkout redesign caused it" is not something rate and mix arithmetic can show. Report where the change sits; name the analysis that would establish why.

## Reference files

- `references/decomposition.md` — read at steps 2, 5 and 6: data-break check queries, the derivation, a SQL template for per-segment rate and mix effects, new and vanished segments, and a worked example where both segments improve and the aggregate still falls.
