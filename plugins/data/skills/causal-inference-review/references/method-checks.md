# Method checks

## Contents

- Difference-in-differences
- Staggered adoption
- Synthetic control
- Regression discontinuity
- Matching and weighting
- Inference with few clusters
- Packages

Each method below lists what it needs from the data, the diagnostics to run before reading the estimate, and the signs that the design has failed. Run the diagnostics with the effect estimate hidden where you can.

## Difference-in-differences

**Needs.** A treated group and a comparison group observed both before and after the treatment date, at the same granularity, with enough pre-period to see a trend (several periods, not one).

**Diagnostics.**

- Event-study plot: regress the outcome on unit and period fixed effects plus indicators for each period relative to treatment, omitting the period just before treatment as the reference. Plot coefficients with intervals. Leads (pre-treatment periods) should sit around zero with no slope.
- Pre-period placebo: move the treatment date back into the pre-period, drop the real post-period, and re-estimate.
- Composition check: the set of units in each group should be the same before and after. Units entering or leaving the panel at the treatment date (new stores opened with the launch, churned customers dropping out) break the comparison.
- Anticipation: if users or staff knew the change was coming, behaviour may shift before the official date. Look for a dip or bump in the last lead and, if present, move the reference period earlier.

**Failure signs.** Leads trending in the direction of the effect; a placebo estimate of similar size to the real one; a comparison group chosen after looking at outcomes; an effect that appears in the first post period and in no other, coinciding with a known external event.

**Sensitivity.** When leads are not perfectly flat, the honest approach is to bound how much post-period violation of parallel trends would overturn the result, relative to the largest pre-period deviation (the Rambachan and Roth approach). Report the bound rather than declaring the trends parallel.

## Staggered adoption

When units are treated at different dates, the classic two-way fixed-effects regression (unit and period fixed effects plus a treated-after indicator) averages over every two-group comparison in the data, including ones that use already-treated units as controls for later-treated ones. If the effect grows or shrinks over time, those comparisons are biased and some enter with negative weight. The Goodman-Bacon decomposition shows how much of the estimate comes from those comparisons.

Use an estimator that only compares treated cohorts with not-yet-treated or never-treated units:

- Callaway and Sant'Anna: group-time average effects, aggregated to an event study or an overall effect.
- Sun and Abraham: interaction-weighted event study.
- Borusyak, Jaravel and Spiess: imputation estimator.

Report which comparison units each uses (never-treated only, or not-yet-treated), because the choice changes the assumption.

## Synthetic control

**Needs.** One treated unit (or a few, analysed separately), a pool of untreated donor units that were not affected by the treatment or by spillover from it, and a pre-period long enough that a good fit is informative rather than overfitted.

**Diagnostics.**

- Pre-period fit: plot treated against synthetic over the pre-period and report the root mean squared prediction error (RMSPE). A poor fit means the post-period gap is not interpretable.
- Donor weights: list them. Weight concentrated on one donor makes the result a two-unit comparison; check that donor for shocks of its own.
- Placebo in space: run the same procedure with each donor as the treated unit. Compute the ratio of post-period RMSPE to pre-period RMSPE for each. The real unit's rank in that distribution is the permutation p-value (rank divided by number of units).
- Placebo in time: assign a fake treatment date in the pre-period and confirm no gap opens.
- Leave-one-out: drop each donor with positive weight in turn and re-fit. A result that vanishes when one donor is removed rests on that donor.

**Failure signs.** Treated unit outside the range of donors on the outcome (no convex combination can match it); fit achieved only by matching on many lagged outcomes over a short pre-period; donors that received a version of the treatment.

## Regression discontinuity

**Needs.** A running variable with a known cutoff that determines treatment, enough observations near the cutoff, and no ability for units to sort themselves across it.

**Diagnostics.**

- Density test at the cutoff (McCrary, or the Cattaneo, Jansson and Ma test in `rddensity`). Bunching just on the favourable side means units manipulated the running variable.
- Covariate balance: pre-treatment covariates should show no jump at the cutoff.
- Bandwidth sensitivity: estimate at the data-driven optimal bandwidth and at half and double it. Report all three.
- Placebo cutoffs: estimate at points away from the real cutoff, where there should be no jump.
- Fuzzy design: if crossing the cutoff changes the probability of treatment rather than determining it, estimate the first stage (the jump in take-up) and report it; a weak first stage makes the effect estimate unstable.

**Failure signs.** Bunching; covariates that jump; an estimate that depends on a high-order global polynomial (use local linear fits instead); a cutoff that also triggers other changes (an age threshold that changes several eligibility rules at once).

**Scope.** The estimate is the effect for units near the cutoff. Say so; it does not generalise to units far from it.

## Matching and weighting

**Needs.** Every confounder measured before treatment, and overlap: for each treated unit, comparable untreated units exist.

**Diagnostics.**

- Overlap: plot propensity score distributions for both groups. Regions where one group has no support are where the estimate is extrapolation; trim them and say how many units were dropped.
- Balance after matching or weighting: standardised mean difference per covariate. Below 0.1 is the common rule of thumb; report the table, including covariates that remain imbalanced.
- Weight distribution: extreme inverse probability weights mean a handful of units drive the estimate. Report the maximum weight and the effective sample size; trimming or stabilised weights change the estimand, so say which you used.
- Doubly robust estimation (an outcome model plus a propensity model) is consistent if either model is right; prefer it to either alone.
- Sensitivity to unmeasured confounding: report the E-value, the minimum strength of association an unmeasured confounder would need with both treatment and outcome to explain away the estimate.

**Failure signs.** Covariates measured after treatment (they may be mediators); balance achieved by dropping most of the treated group; an E-value small enough that an obvious unmeasured variable could reach it.

## Inference with few clusters

Cluster standard errors at the level treatment was assigned. When the number of clusters is small, and especially when few clusters are treated, clustered standard errors are biased downward. Options:

- Wild cluster bootstrap (restricted, with Rademacher or Webb weights when clusters are very few).
- Randomisation inference: re-assign treatment across clusters under the actual assignment rule many times and locate the real estimate in that distribution.

State the number of treated and control clusters next to every interval.

## Packages

Verify the version you have before relying on an argument name; these are the commonly used implementations, not an exhaustive list.

| Task | R | Python |
| --- | --- | --- |
| Fixed-effects regression with clustered errors | `fixest` | `pyfixest`, `linearmodels` |
| Staggered DiD | `did` (Callaway and Sant'Anna), `fixest::sunab` (Sun and Abraham), `didimputation` | `pyfixest` (event study and DiD estimators) |
| DiD sensitivity to trend violations | `HonestDiD` | |
| Synthetic control | `Synth`, `augsynth` | `pysyncon` |
| Regression discontinuity | `rdrobust`, `rddensity` | `rdrobust`, `rddensity` |
| Matching and balance | `MatchIt`, `WeightIt`, `cobalt` | `statsmodels` for propensity models |
| E-values | `EValue` | |
| Wild cluster bootstrap | `fwildclusterboot` | `wildboottest` |
