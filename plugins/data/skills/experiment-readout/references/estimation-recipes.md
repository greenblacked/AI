# Readout estimation recipes

## Contents

- One row per unit
- Trust checks
- The sample ratio test
- Intervals: difference, relative lift, ratio metrics, CUPED
- Segments: correction and heterogeneity
- Effect by week since exposure

All Python here uses only the standard library (3.10 or later) and a normal approximation, which is sound at the sample sizes online tests run at. With fewer than a few hundred units per arm, use a t distribution or a bootstrap instead.

## One row per unit

Every estimate starts from one row per randomisation unit, never from event rows, because events from the same user are correlated. The shape, in generic SQL; adjust table names and the timestamp literal to your warehouse:

```sql
WITH exposure AS (
  SELECT unit_id, MIN(arm) AS arm, MAX(arm) AS arm_check, MIN(exposed_at) AS first_exposed_at
  FROM experiment_exposures
  WHERE experiment_id = 'checkout-v2'
  GROUP BY unit_id
)
SELECT
  e.unit_id,
  e.arm,
  e.first_exposed_at,
  COALESCE(SUM(o.revenue), 0) AS revenue,
  COUNT(o.order_id)           AS orders
FROM exposure AS e
LEFT JOIN orders AS o
  ON o.user_id = e.unit_id
 AND o.created_at >= e.first_exposed_at
 AND o.created_at <  TIMESTAMP '2026-10-19 00:00:00'   -- planned end, exclusive
WHERE e.arm = e.arm_check
GROUP BY e.unit_id, e.arm, e.first_exposed_at;
```

Count the units dropped by `e.arm = e.arm_check` (seen in both arms) and report it; more than a fraction of a percent points at an identity or assignment bug. Units with no outcome rows stay in with zero, because dropping them conditions on behaviour after exposure. Only outcomes after first exposure count.

## Trust checks

Before any effect:

1. Units per arm, total and per day. The daily ratio should be steady; a break on one day usually matches a deploy or allocation change.
2. The experiment's change log: allocation, targeting, code or configuration changes between start and end.
3. Pre-period balance: run the difference interval below on each unit's primary metric from the pre-period. With random assignment this interval includes zero about 95% of the time; a clear pre-period difference alongside any other oddity means assignment was not independent of the outcome.

## The sample ratio test

```python
from math import erfc, exp, sqrt


def srm(counts, shares):
    """Chi-square goodness of fit of unit counts against the designed shares."""
    # Fractions that sum to 1: [50, 50] would pass every test with a chi-square near zero.
    if len(counts) != len(shares) or min(shares) <= 0 or abs(sum(shares) - 1) > 1e-9:
        raise ValueError("one positive share per arm, summing to 1 (0.9 and 0.1, not 90 and 10)")
    total = sum(counts)
    chi2 = sum((c - total * s) ** 2 / (total * s) for c, s in zip(counts, shares))
    df = len(counts) - 1
    if df == 1:
        p = erfc(
            sqrt(chi2 / 2)
        )  # chi-square with 1 df is a squared normal; erfc keeps the tail exact
    elif df == 2:
        p = exp(-chi2 / 2)  # exact survival function for 2 df
    else:
        raise ValueError("more than three arms: use scipy.stats.chisquare(counts, expected)")
    return chi2, p


print(srm([1_006_120, 993_880], [0.5, 0.5]))  # chi2 about 74.9, p far below 0.001
```

Pass the designed shares (`[0.9, 0.1]` for a 90/10 test). Flag at p < 0.001: the threshold is strict because the check runs on every test, and a looser one stops healthy tests too often.

## Intervals: difference, relative lift, ratio metrics, CUPED

```python
from math import sqrt
from statistics import NormalDist, covariance, fmean, variance


def z(level=0.95):
    return NormalDist().inv_cdf(0.5 + level / 2)


def mean_and_var(xs):
    return fmean(xs), variance(xs) / len(xs)  # mean and variance of the mean


def diff_and_lift(treat, ctrl, level=0.95):
    """Welch difference and delta-method relative lift for a per-unit metric."""
    mt, vt = mean_and_var(treat)
    mc, vc = mean_and_var(ctrl)
    d, se_d = mt - mc, sqrt(vt + vc)
    lift = mt / mc - 1
    se_lift = sqrt(vt / mc**2 + mt**2 * vc / mc**4)  # arms independent
    k = z(level)
    return {
        "diff": d,
        "diff_ci": (d - k * se_d, d + k * se_d),
        "lift": lift,
        "lift_ci": (lift - k * se_lift, lift + k * se_lift),
    }


def ratio_and_var(xs, ys):
    """Ratio of means for one arm, numerator and denominator per unit."""
    mx, my, n = fmean(xs), fmean(ys), len(xs)
    r = mx / my
    v = (variance(xs) - 2 * r * covariance(xs, ys) + r**2 * variance(ys)) / (n * my**2)
    return r, v


def ratio_diff(xt, yt, xc, yc, level=0.95):
    rt, vt = ratio_and_var(xt, yt)
    rc, vc = ratio_and_var(xc, yc)
    d, se = rt - rc, sqrt(vt + vc)
    return d, (d - z(level) * se, d + z(level) * se)


def cuped(y, x):
    """Adjust outcomes y by pre-period covariate x; pass both arms pooled, then split."""
    theta = covariance(y, x) / variance(x)
    mx = fmean(x)
    return [yi - theta * (xi - mx) for yi, xi in zip(y, x)]
```

Use `cuped` only when the plan pre-registered it, with the plan's covariate and pre-period. Estimate theta on both arms pooled, then pass the adjusted values per arm to `diff_and_lift`.

## Segments: correction and heterogeneity

```python
def benjamini_hochberg(pvals, q=0.05):
    """Indices of the hypotheses rejected at false-discovery rate q."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    cutoff = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= rank / m * q:
            cutoff = rank
    return {order[r] for r in range(cutoff)}


def segments_differ(d1, se1, d2, se2):
    """Two-sided p-value that two segments' effects differ."""
    zstat = (d1 - d2) / sqrt(se1**2 + se2**2)
    return 2 * (1 - NormalDist().cdf(abs(zstat)))
```

Run the correction over every segment test you report, not only the interesting ones. Say "Android +4.1% (95% CI +1.0% to +7.2%), iOS +0.6% (−2.3% to +3.5%); difference between them p = 0.10" rather than "it only worked on Android".

## Effect by week since exposure

Compute each unit's outcome per week since its own first exposure, then the effect per week. In generic SQL, with `days_between` standing for your dialect's day-difference function (`DATEDIFF`, `DATE_DIFF` or subtraction of dates):

```sql
SELECT
  e.arm,
  FLOOR(days_between(e.first_exposed_at, o.created_at) / 7) AS week_since_exposure,
  e.unit_id,
  SUM(o.revenue) AS revenue
FROM exposure AS e
JOIN orders AS o
  ON o.user_id = e.unit_id
 AND o.created_at >= e.first_exposed_at
 AND o.created_at <  TIMESTAMP '2026-10-19 00:00:00'   -- planned end, exclusive, as above
GROUP BY 1, 2, 3;
```

Fill zeros for units with no orders in a week they were observable. Restrict to one fixed cohort: units whose first exposure was at least W full weeks before the end, where W is the number of weeks compared, so every unit contributes to every week. Do not let the cohort change from week to week, or the trend reflects who remains rather than time since exposure. The late weeks then describe early entrants only. Run `diff_and_lift` per week. Read the trend, not each week's significance: a lift of 6%, 3%, 2% over three weeks is consistent with novelty fading toward about 2% among that cohort, and it qualifies the pooled estimate rather than replacing it.
