# Slices, calibration and thresholds

## Contents

- Wilson interval for precision and recall
- Bootstrap interval for any metric per segment
- Segment table
- Calibration check
- Threshold from a cost curve

Inputs are arrays from the validation set: `y` (0 or 1), `p` (predicted probability of class 1) and a segment label per row. scikit-learn and numpy are assumed except where noted.

## Wilson interval for precision and recall

Precision and recall are proportions, so the Wilson score interval is appropriate and needs only the standard library. It behaves well for small counts and proportions near 0 or 1, where the textbook normal interval does not.

```python
import math


def wilson(successes, n, z=1.959964):
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (math.nan, math.nan)
    phat = successes / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


# precision at a threshold: successes = true positives, n = predicted positives
# recall at a threshold:    successes = true positives, n = actual positives
```

## Bootstrap interval for any metric per segment

For PR-AUC, ROC AUC, log loss or any metric that is not a simple proportion, resample rows within the segment:

```python
import numpy as np
from sklearn.metrics import average_precision_score


def bootstrap_ci(y, p, metric=average_precision_score, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue  # resample has one class; metric undefined
        stats.append(metric(y[idx], p[idx]))
    if not stats:
        return np.array([np.nan, np.nan])  # every resample was single-class
    return np.percentile(stats, [2.5, 97.5])
```

Segments with very few positives produce many single-class resamples and a wide, unstable interval. Report them, but do not gate on them: set a minimum positive count per segment before looking at results.

## Segment table

```python
import pandas as pd


def segment_table(df, segment_col, min_pos=30):
    rows = []
    for seg, g in df.groupby(
        segment_col, dropna=False
    ):  # dropna=False: rows with no segment get a row too
        n_pos = int(g["y"].sum())
        row = {
            "segment": seg,
            "n": len(g),
            "positives": n_pos,
            "gated": False,
            "pr_auc": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
        }
        if n_pos >= min_pos and n_pos < len(g):
            row["pr_auc"] = average_precision_score(g["y"], g["p"])
            row["ci_low"], row["ci_high"] = bootstrap_ci(g["y"], g["p"])
            row["gated"] = True
        rows.append(row)
    return pd.DataFrame(rows).sort_values("pr_auc", na_position="last")
```

Read the table from the top. A gated segment whose `ci_high` is below the floor fails; one whose interval contains the floor is undecided and needs more data. Note that PR-AUC depends on the positive rate, so segments with different prevalence are not directly comparable on it; compare each against its own prevalence (the PR-AUC of a random model equals the positive rate) or use precision at the chosen recall.

## Calibration check

```python
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

frac_pos, mean_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
for mp, fp in zip(mean_pred, frac_pos):
    print(f"predicted {mp:.3f}  observed {fp:.3f}  gap {fp - mp:+.3f}")
print("Brier", brier_score_loss(y, p))
```

Points consistently above the diagonal mean the model under-predicts; below means it over-predicts. Run the same check per gated segment.

To recalibrate, fit the calibrator on a split that neither trained the model nor will be used to choose the threshold. `CalibratedClassifierCV` with `method="sigmoid"` or `method="isotonic"` does this; check its documentation for the version you have, since the way to pass an already-fitted model has changed between releases.

## Threshold from a cost curve

```python
import numpy as np


def cost_curve(y, p, cost_fp, cost_fn, recall_floor=None):
    y, p = np.asarray(y), np.asarray(p)
    # The extra last value is "flag nothing": when a false positive costs more than the
    # positives it finds, the cheapest rule is to alert on no one.
    thresholds = np.append(
        np.unique(np.quantile(p, np.linspace(0, 1, 501))), np.nextafter(p.max(), np.inf)
    )
    best = None
    rows = []
    for t in thresholds:
        pred = p >= t
        fp = int(np.sum(pred & (y == 0)))
        fn = int(np.sum(~pred & (y == 1)))
        tp = int(np.sum(pred & (y == 1)))
        recall = tp / max(tp + fn, 1)
        cost = fp * cost_fp + fn * cost_fn
        rows.append((t, cost, recall))
        if recall_floor is not None and recall < recall_floor:
            continue
        if best is None or cost < best[1]:
            best = (t, cost, recall)
    return best, rows
```

`best` is `None` when no threshold reaches the recall floor; report that as a finding about the model rather than lowering the floor. Plot cost against threshold from `rows`. Report the chosen threshold, its cost, its recall and precision with Wilson intervals, and the range of thresholds whose cost is within a few percent of the minimum. A wide flat range means the threshold is robust to small shifts in the data; a narrow one means it should be re-checked whenever the positive rate changes.

If the model was trained on resampled or class-weighted data, its scores are shifted, and the cost-optimal threshold will be far from 0.5. That is expected, not a defect.
