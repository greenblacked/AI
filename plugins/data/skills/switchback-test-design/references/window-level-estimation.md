# Window-level estimation

## Contents

- One row per window
- Checking the realised schedule
- The paired estimate and randomisation inference
- Regression with fixed effects and clustered errors
- Reporting

## One row per window

The window is the unit. Attribute each event to the window in force when it started, using the arm the serving system logged, and drop events that started inside the washout. Generic SQL; interval syntax differs by warehouse, so adjust the 45-minute washout expression to your dialect:

```sql
SELECT
  w.region,
  w.day,
  w.slot,
  w.block,
  w.cluster,
  w.arm,
  COUNT(t.trip_id)                 AS trips,
  AVG(t.pickup_seconds)            AS mean_pickup_seconds,
  COALESCE(SUM(t.fare), 0)         AS gross_fare,
  COALESCE(SUM(CASE WHEN t.served_arm IS DISTINCT FROM w.arm THEN 1 ELSE 0 END), 0)
                                   AS trips_served_other_arm
FROM switchback_windows AS w            -- the realised windows, one row each
LEFT JOIN trips AS t
  ON t.region = w.region
 AND t.requested_at >= w.window_start + INTERVAL '45' MINUTE
 AND t.requested_at <  w.window_end
GROUP BY w.region, w.day, w.slot, w.block, w.cluster, w.arm;
```

The `LEFT JOIN` keeps a window with no trips, which is a real observation (a quiet window in a small region) rather than a missing one; an inner join would silently delete it and then drop its whole block. `COUNT(t.trip_id)` counts trips, not the single null row an empty window produces. Do not filter on `t.served_arm = w.arm` in the join: that would discard the very trips that show the switch is late and would leave the mismatch rate unmeasurable. `IS DISTINCT FROM` also counts a trip whose `served_arm` was never logged, which `<>` would skip because comparing with null is never true. A non-trivial share in `trips_served_other_arm` means the switch is not propagating as fast as the washout assumes; analyse as scheduled, then re-run excluding those trips as a check. A window with zero trips has a null mean: decide in the plan whether it is dropped with its block or scored as zero, before looking.

Decide in the plan whether a window's outcome is a per-window mean (each window weighs the same) or a total, and whether windows are weighted by volume. Equal weighting is the simpler default and matches the randomisation.

## Checking the realised schedule

Before estimating, compare realised windows with the schedule: count scheduled, realised and dropped windows per arm. A block that lost one of its two windows (outage, holiday shutdown) is dropped whole. If drops concentrate in one arm, investigate as you would a sample ratio mismatch: something in that arm is causing the outages or the missing data.

## The paired estimate and randomisation inference

With the paired-day schedule, each block holds one treatment and one control window, so the estimate is the mean within-block difference and randomisation inference is a sign-flip test: under no effect, each block's difference was equally likely to have the opposite sign. Standard library only:

```python
import random
from statistics import fmean


def paired_diffs(rows, outcome):
    blocks = {}
    for r in rows:
        blocks.setdefault(r["block"], {})[r["arm"]] = float(r[outcome])
    return [b["treatment"] - b["control"] for b in blocks.values() if len(b) == 2]


def sign_flip_test(diffs, n_draws=20000, seed=0):
    rng = random.Random(seed)
    observed = fmean(diffs)
    extreme = 0
    for _ in range(n_draws):
        flipped = fmean(d if rng.random() < 0.5 else -d for d in diffs)
        if (
            abs(flipped) >= abs(observed) - 1e-12
        ):  # tolerance: the all-same-sign draw reproduces observed up to rounding
            extreme += 1
    return observed, (extreme + 1) / (n_draws + 1)
```

For an interval, invert the test: the 95% interval is the set of shifts c for which subtracting c from every block difference gives a p-value above 0.05. Search c over a grid around the estimate.

The sign-flip test re-draws exactly what the schedule randomised, so it is valid for the no-effect hypothesis whatever the correlation between windows. Flip at the level that was randomised — here the block — and never at a level chosen after seeing the data. What it cannot absorb is carryover: a washout that is too short lets the previous arm leak into the window. Check by re-estimating with the washout extended by half again; an estimate that moves materially means the washout was too short, and the longer one is the result to report.

## Regression with fixed effects and clustered errors

When the design is not a clean pairing (unequal block sizes, region-by-time units, added covariates), regress the window outcome on the arm with block fixed effects and cluster the standard errors. With pandas and statsmodels installed:

```python
import pandas as pd
import statsmodels.formula.api as smf

df = pd.read_csv("windows.csv")
df["treat"] = (df["arm"] == "treatment").astype(int)

fit = smf.ols("mean_pickup_seconds ~ treat + C(block)", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["cluster"]}
)
print(fit.params["treat"], fit.conf_int().loc["treat"].tolist())
```

Add a pre-period covariate — the same window's outcome in the weeks before the test — as an extra regressor if the plan named one; it reduces noise the same way CUPED does in a user-level test. Cluster on a grouping that contains the correlated windows (region and day pair here). With only a few dozen clusters or fewer, clustered standard errors tend to be too small: report the randomisation-inference p-value alongside, and let it decide when the two disagree.

## Reporting

Report the effect per window with its interval, the number of analysable windows and blocks, the share of windows dropped and why, the washout used, and the mismatch rate between scheduled and served arm. State that the estimate is the effect of switching the whole market, and translate it into the business unit the decision uses (seconds of pickup per trip, fare per hour, items per shift) without changing the unit of analysis.
