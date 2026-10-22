# Reviewing an observational analysis

Work through these in order. The early questions decide whether the later ones are worth asking: an analysis with no defensible comparison group does not need its standard errors checked.

## 1. Is the question stated?

- Is there a single estimand: treatment, population, outcome, window?
- Is it clear whether the number is the effect on those treated or on everyone?
- Is the decision threshold stated, so the interval can be read against it?

Finding if missing: "The analysis does not say whose effect this is. As written, it will be quoted as the effect of a full rollout, but the treated group was self-selected early adopters."

## 2. Is the assignment mechanism described?

- Who decided which units were treated, and on what basis?
- Was the date chosen because of something that also affects the outcome (a seasonal peak, a quarter end, a reaction to falling numbers)?
- Could units opt in, opt out, or move across an eligibility line?

Treatment launched because a metric was falling is the classic case: the metric would have recovered partly on its own (regression to the mean), and the launch takes credit.

## 3. Does the comparison stand in for the counterfactual?

- Is there a comparison group at all? Before-and-after alone is description.
- Was the comparison group chosen before looking at the outcome?
- Could the treatment spill over into the comparison group (shared inventory, shared marketing, users in both)? Spillover biases the estimate towards zero or beyond it, depending on direction.
- Did anything else change for the treated group in the same window?

## 4. Were the assumption checks run, and did they pass?

| Method | Check that must be in the write-up |
| --- | --- |
| Difference-in-differences | Event-study plot with pre-period leads; pre-period placebo |
| Staggered DiD | Estimator that avoids already-treated controls, or a decomposition showing those comparisons carry little weight |
| Synthetic control | Pre-period fit, donor weights, placebo-in-space ranking |
| Regression discontinuity | Density test, covariate balance at the cutoff, bandwidth sensitivity |
| Matching or weighting | Overlap plot, balance table, weight distribution, E-value |

A check described as "parallel trends hold" without the plot is a claim, not a check.

## 5. Is the uncertainty honest?

- Are errors clustered at the level treatment was assigned?
- How many treated clusters are there? Under a few dozen, ask for a wild cluster bootstrap or randomisation inference.
- Is a percentage effect reported with the base it is a percentage of?
- Were several outcomes, segments or windows tested and only the striking one reported? Ask for all of them.

## 6. Does it survive reasonable alternatives?

- Alternative comparison groups, windows and covariate sets, in one table.
- Excluding known shock periods.
- The effect over time, not only the average.

## 7. Does the conclusion match the evidence?

- Is "caused" used where only "associated with" is supported?
- Is the result extrapolated beyond the population studied (from the cutoff neighbourhood to everyone, from early adopters to all users)?
- If the design does not hold, does the write-up name the experiment that would settle it?

## Phrasing findings

One finding per point, in the order above, each with:

- what is wrong, specifically (the table, the chart, the sentence);
- the consequence if the analysis is used as is ("the 8% lift includes the seasonal uplift visible in the comparison group's own pre-period");
- the smallest change that would fix it ("add last year's same weeks as a comparison and re-run the event study").

Lead the summary with the verdict: supported, supported with caveats, or not identified.
