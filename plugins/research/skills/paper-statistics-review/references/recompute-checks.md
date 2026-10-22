# Recompute checks

Contents: p from a statistic, GRIM, SD and SE, CI and p, clustering, script.

## p from the reported statistic

With `scipy.stats`:

```python
from scipy import stats

stats.t.sf(abs(t), df) * 2  # two-sided p from t
stats.f.sf(F, df1, df2)  # p from F
stats.chi2.sf(x2, df)  # p from chi-square
stats.norm.sf(abs(z)) * 2  # two-sided p from z
```

Rounded inputs give a range, not a point: recompute with the statistic at its lower and upper rounding bound. A reported p outside that range is a mismatch. Check whether the paper states one-sided tests (halve the two-sided p), and whether the statistic is from a corrected test (Welch changes df to a non-integer).

## GRIM integer check

For data that can only take integer values, the mean of n values is a multiple of 1/n. Test a reported mean with `d` decimals:

```python
def grim_consistent(mean, n, decimals=2):
    lo = (mean - 0.5 * 10**-decimals) * n
    hi = (mean + 0.5 * 10**-decimals) * n
    import math

    return math.floor(hi) >= math.ceil(lo)  # an integer total exists in range
```

It applies to a single item or a sum of integers, not to an average of several items (that is a multiple of 1/(n * items)) and not to continuous data. Check n per group, and that no value was removed. A failure means a wrong mean or wrong n; ask the authors.

## SD, SE and CI

- SE = SD / sqrt(n); SD = SE * sqrt(n). A table headed "mean (SE)" with SDs that look like SEs is a common mislabel.
- 95% CI of a mean is about mean plus or minus t(0.975, n - 1) * SE, near 1.96 SE for large n, near 2.1 to 2.3 for n between 10 and 20.
- A difference between two independent means has SE = sqrt(SE1^2 + SE2^2).
- From a 95% interval (L, U) around a ratio such as an odds or hazard ratio, work on the log scale: SE = (ln U - ln L) / 3.92, then z = ln(estimate) / SE and p = 2 * norm.sf(abs(z)). This should agree with the reported p. If the interval excludes 1 and p is above 0.05, or the reverse, something is misreported.

## Clustering and effective sample size

If m units per cluster with intra-cluster correlation rho are analysed as independent, the effective sample size is about N / (1 + (m - 1) × rho), the design effect being 1 + (m - 1) × rho. With 20 cells per animal and rho = 0.3, the design effect is 6.7, so 200 cells carry the information of about 30. Even if rho is not reported, a plausible value shows how large the error could be. For repeated measures of the same person, treat time points as clustered within the person.

## A script

```python
import math
from scipy import stats


def check_t(t, df, p_lo, p_hi, tail=2, rounding=0.005):
    """Compare the p range implied by a rounded t with the range the reported p stands for.

    p_lo, p_hi: the interval the reported p represents, e.g. "p = .03" is [0.025, 0.035)
    and "p < .05" is [0, 0.05); ">" reports are one-sided bounds such as [0.05, 1].
    """
    lo = stats.t.sf(abs(t) + rounding, df) * tail
    hi = stats.t.sf(max(abs(t) - rounding, 0), df) * tail
    return lo < p_hi and hi >= p_lo, (lo, hi)


print(check_t(t=2.31, df=18, p_lo=0.025, p_hi=0.035))
```

The computed p is about 0.033, which a paper may correctly print as .03, so an exact-point comparison would flag a valid report. Flag a mismatch only when the two ranges do not overlap.

State the tolerance used. Run it only on numbers quoted from the paper, and keep a list of every check with its result in the review.
