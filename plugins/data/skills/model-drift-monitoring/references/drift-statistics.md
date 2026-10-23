# Drift statistics

How to compute the layer 2 and layer 3 measures so that they fire on change rather than on sample size.

## Contents

- Population stability index
- The KS statistic
- Categorical features
- Calibrating a threshold per feature
- Seasonality
- Code

## Population stability index

For a reference distribution (the training window) and a current one, both split into the same bins:

```text
PSI = sum over bins of (current_share - reference_share) * ln(current_share / reference_share)
```

- Take the bin edges from the reference data, usually its deciles, and reuse those edges for every current window. Recomputing edges per window measures nothing.
- Put values below the lowest edge and above the highest in the end bins, and give nulls a bin of their own, so a rise in nulls appears here as well as in layer 1.
- An empty bin makes the logarithm undefined. Replace a zero share with a small constant (1e-4 is common) on both sides before computing, and record that you did.
- PSI is symmetric in the sense that swapping reference and current gives the same value, and it grows with the number of bins; keep the bin count fixed per feature so values are comparable over time.

The bands often quoted — below 0.1 stable, 0.1 to 0.25 a moderate shift, above 0.25 a significant one — come from credit-scorecard practice. Use them to start, then replace them per feature as below.

## The KS statistic

The two-sample Kolmogorov-Smirnov statistic is the largest vertical distance between the two empirical cumulative distributions, between 0 and 1. `scipy.stats.ks_2samp(reference, current)` returns it as `statistic`, beside a `pvalue`.

Track the statistic. The p-value answers "could these two samples share a distribution", and with hundreds of thousands of rows the answer is almost always no, even for a shift too small to change a single decision. A threshold on the statistic is a threshold on the size of the shift.

KS is defined for continuous values. On a heavily discrete feature (a count that is mostly 0, 1 or 2) it behaves poorly; treat such a feature as categorical.

## Categorical features

- PSI over categories works as above, with the reference categories as bins, rare categories pooled into "other" so tiny shares do not dominate, and a bin for categories unseen in training. A growing unseen share is worth its own check: the model's encoder maps them all to one value.
- Jensen-Shannon distance is bounded and symmetric; `scipy.spatial.distance.jensenshannon(p, q)` returns the distance (the square root of the divergence), so do not square-root it again.
- Chi-square tests have the same sample-size problem as the KS p-value. Prefer an effect-size measure.

## Calibrating a threshold per feature

A threshold is meaningful only relative to how much the feature moves when nothing is wrong.

1. Split the training period into consecutive windows of the size you will monitor (a day, a week).
2. Compute PSI (or the KS statistic) for each window against the full training reference.
3. That spread is the noise floor. Set the investigation threshold above its high end, for instance above the largest value seen, with a margin you write down.
4. Revisit after the first months live: a threshold that fired and led to nothing should rise; a shift that hurt performance without firing means the threshold is too high or the window too long.

Write the threshold, the method and the date beside each feature in the monitor definition, so the next person knows it was chosen rather than defaulted.

## Seasonality

A feature with a weekly cycle compared against a training window that averaged the cycle out will fire every weekend. Either compare each current window with the same weekday or season in the reference, or monitor the difference from last cycle's value as well as from the training reference. A real shift moves both comparisons; a cycle moves only the first.

## Code

```python
import numpy as np
from scipy.stats import ks_2samp

EPS = 1e-4


def psi_numeric(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    ref = reference[~np.isnan(reference)]
    cur = current[~np.isnan(current)]
    if len(ref) == 0 or len(cur) == 0:
        # An empty window would divide by zero and return NaN, which never fires a threshold.
        raise ValueError("no non-null values in the reference or current window")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        # A mostly constant feature collapses to one bin, where PSI is 0 whatever happens.
        raise ValueError("fewer than two bins survive; monitor this feature as categorical")
    edges[0], edges[-1] = -np.inf, np.inf
    ref_share = np.histogram(ref, edges)[0] / len(ref)
    cur_share = np.histogram(cur, edges)[0] / len(cur)
    ref_share = np.where(ref_share == 0, EPS, ref_share)
    cur_share = np.where(cur_share == 0, EPS, cur_share)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def ks_statistic(reference: np.ndarray, current: np.ndarray) -> float:
    ref = reference[~np.isnan(reference)]
    cur = current[~np.isnan(current)]
    return float(ks_2samp(ref, cur).statistic)
```

`np.unique` on the quantiles collapses duplicate edges for features with heavy ties, so the bin count may come out below ten; that is correct, not a bug, until only one bin is left, where the function refuses rather than reporting a PSI of 0 for a feature it cannot see. Nulls are excluded here because layer 1 tracks the null rate directly; add a null bin if you want one number per feature.
