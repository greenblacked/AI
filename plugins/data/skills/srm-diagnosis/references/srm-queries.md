# Sample ratio queries

## Contents

- The test
- How big a gap is significant
- Counting at each stage
- Slicing the mismatch

## The test

Standard library only, Python 3.8 or later:

```python
from math import erfc, exp, sqrt


def srm(counts, shares):
    """Chi-square goodness of fit of unit counts against designed shares."""
    # Fractions that sum to 1: [50, 50] would give an expected count 50 times too big,
    # a chi-square near zero and a pass on every test.
    if len(counts) != len(shares) or min(shares) <= 0 or abs(sum(shares) - 1) > 1e-9:
        raise ValueError("one positive share per arm, summing to 1 (0.9 and 0.1, not 90 and 10)")
    total = sum(counts)
    expected = [total * s for s in shares]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(counts, expected))
    df = len(counts) - 1
    if df == 1:
        p = erfc(sqrt(chi2 / 2))  # 1 df: a squared standard normal; erfc keeps the tail exact
    elif df == 2:
        p = exp(-chi2 / 2)  # 2 df: exact
    else:
        raise ValueError("four or more arms: scipy.stats.chisquare(counts, f_exp=expected)")
    return round(chi2, 2), p


print(srm([503_100, 496_900], [0.5, 0.5]))  # chi2 38.44, p about 6e-10: mismatch
print(srm([900_400, 99_600], [0.9, 0.1]))  # chi2 1.78, p about 0.18: fine
```

With SciPy available, `scipy.stats.chisquare(counts, f_exp=expected)` returns the statistic and p-value for any number of arms; `expected` must sum to the same total as `counts`.

Flag at p < 0.001. Run it on distinct randomisation units, per arm, over the experiment's full window, and again per day.

## How big a gap is significant

For a 50/50 test with N units in total, the chi-square is 4 N (s − 0.5)², where s is the observed share in one arm. At p = 0.001 the 1-df critical value is about 10.83, so the smallest flagged deviation from 50% is about sqrt(10.83 / (4 N)):

| Total units | Smallest flagged share |
| --- | --- |
| 10,000 | about 51.6% |
| 100,000 | about 50.5% |
| 1,000,000 | about 50.16% |
| 10,000,000 | about 50.05% |

This is why "it is only half a percent" is no defence at scale.

## Counting at each stage

Run the same count at every stage, over the same window, keyed on the same unit id. Table names are illustrative; generic SQL:

```sql
SELECT 'assignment' AS stage, arm, COUNT(DISTINCT unit_id) AS units
FROM assignment_log
WHERE experiment_id = 'checkout-v2'
  AND assigned_at >= TIMESTAMP '2026-09-21 00:00:00'
  AND assigned_at <  TIMESTAMP '2026-10-19 00:00:00'
GROUP BY arm
UNION ALL
SELECT 'exposure', arm, COUNT(DISTINCT unit_id)
FROM exposure_log
WHERE experiment_id = 'checkout-v2'
  AND exposed_at >= TIMESTAMP '2026-09-21 00:00:00'
  AND exposed_at <  TIMESTAMP '2026-10-19 00:00:00'
GROUP BY arm
UNION ALL
SELECT 'first_event', arm, COUNT(DISTINCT unit_id)
FROM client_events
WHERE experiment_id = 'checkout-v2'
  AND event_at >= TIMESTAMP '2026-09-21 00:00:00'
  AND event_at <  TIMESTAMP '2026-10-19 00:00:00'
GROUP BY arm
UNION ALL
SELECT 'analysis_pre_bot_filter', arm, COUNT(DISTINCT unit_id)
FROM experiment_units_unfiltered
WHERE experiment_id = 'checkout-v2'
GROUP BY arm
UNION ALL
SELECT 'analysis', arm, COUNT(DISTINCT unit_id)
FROM experiment_units
WHERE experiment_id = 'checkout-v2'
GROUP BY arm
ORDER BY stage, arm;
```

Feed each stage's pair of counts into `srm`. Also compute, per arm, the share of units that survive from each stage to the next: a treatment arm keeping 96% from exposure to first event against control's 98% is the drop-off to explain.

Also count units that appear under more than one arm, which no per-arm count shows because each arm counts the unit once:

```sql
SELECT COUNT(*) AS units_in_both_arms
FROM (
  SELECT unit_id
  FROM exposure_log
  WHERE experiment_id = 'checkout-v2'
  GROUP BY unit_id
  HAVING COUNT(DISTINCT arm) > 1
) AS both_arms;
```

A non-zero count points at identity merging or a re-salted assignment, and those units sit in both denominators.

Note that assignment can legitimately exceed exposure when units are assigned before they reach the changed surface; what matters is that the ratio holds, not that the counts match.

## Slicing the mismatch

At the first stage that breaks, slice by attributes fixed before exposure:

```sql
SELECT
  CAST(exposed_at AS DATE) AS day,
  platform,
  browser,
  app_version,
  SUM(CASE WHEN arm = 'control'   THEN 1 ELSE 0 END) AS control_units,
  SUM(CASE WHEN arm = 'treatment' THEN 1 ELSE 0 END) AS treatment_units
FROM (
  SELECT unit_id, arm, platform, browser, app_version, MIN(exposed_at) AS exposed_at
  FROM exposure_log
  WHERE experiment_id = 'checkout-v2'
  GROUP BY unit_id, arm, platform, browser, app_version
) AS u
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4;
```

A unit seen on two browsers or app versions appears in both rows here; that is fine for locating the mechanism, but take each unit's first value when you need counts that add up to the total.

Compute `srm` per row, then sort slices by chi-square, not by ratio: a tiny slice can show a wild ratio by chance, while a large slice with a modest skew is where the units went. If the mismatch disappears after removing one slice, that slice names the mechanism; it does not license analysing the rest.
