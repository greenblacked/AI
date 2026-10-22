# Sample size, ratio metrics and CUPED

## Contents

- Difference in means
- Proportions
- Unequal splits and more than two arms
- Ratio metrics: the delta method
- CUPED
- A standard-library calculator
- Worked example

## Difference in means

For a two-sided test at significance alpha and power 1 − beta, with equal arms, the units needed per arm to detect an absolute difference δ in a metric with per-unit standard deviation σ are

```text
n_per_arm = 2 * (z_{1-alpha/2} + z_{1-beta})^2 * sigma^2 / delta^2
```

At alpha 0.05 and power 0.8, z values are 1.960 and 0.842, so the multiplier is about 15.7 — the familiar "16 σ² / δ²". At power 0.9 it is about 21.0.

State δ in the metric's own units. When the plan says "a 2% relative lift", δ = 0.02 × baseline mean; write both so nobody confuses a relative MDE with an absolute one.

## Proportions

For a conversion rate with baseline p₁ and target p₂ = p₁ + δ:

```text
n_per_arm = (z_{1-alpha/2} + z_{1-beta})^2 * (p1*(1-p1) + p2*(1-p2)) / delta^2
```

Low base rates are what make conversion tests expensive: at p₁ = 2% a 5% relative lift (δ = 0.001) needs on the order of 300,000 users per arm.

## Unequal splits and more than two arms

The variance of the difference is proportional to 1/n_T + 1/n_C. With total N and a treatment share s, that is (1/N)(1/s + 1/(1 − s)), minimised at s = 0.5. A 90/10 split needs about 2.8 times the total traffic of 50/50, and 95/5 about 5.3 times.

With k treatment arms each compared with control, either correct alpha (Bonferroni: alpha/k per comparison) and size each comparison at the corrected alpha, or decide in the plan that the arms are exploratory and only the pre-named one is confirmatory.

## Ratio metrics: the delta method

A ratio metric divides two sums that both vary per randomisation unit: clicks per session, revenue per order, errors per request. With users randomised, compute per-user numerator X and denominator Y, then the ratio of means R = mean(X) / mean(Y). Its variance over n users is approximately

```text
var(R) = (1 / (n * mu_Y^2)) * (var_X - 2 * R * cov_XY + R^2 * var_Y)
```

So the per-unit variance to put into the sample-size formula in place of σ² is

```text
sigma_R^2 = (var_X - 2 * R * cov_XY + R^2 * var_Y) / mu_Y^2
```

Computing σ from the session-level values instead treats sessions as independent and understates the variance, which is the error that makes a per-user split read like a per-session one.

## CUPED

CUPED (Deng, Xu, Kohavi and Walker, 2013) adjusts each unit's outcome Y by its pre-experiment covariate X, usually the same metric over a fixed pre-period:

```text
theta = cov(Y, X) / var(X)        # estimated on both arms pooled
Y_adj = Y - theta * (X - mean(X))
```

The difference in means of Y_adj is unbiased for the same effect, and its variance is var(Y) × (1 − ρ²), where ρ = corr(Y, X). For sizing, multiply n_per_arm by (1 − ρ²) using ρ measured on history: two consecutive four-week windows for the same users. A ρ of 0.7 roughly halves the sample.

Fix the pre-period window and the covariate in the plan. Units with no pre-period (new users) take X = 0 or the population mean consistently; they get no variance reduction, so a test aimed mostly at new users gains little.

## A standard-library calculator

Runs on any Python 3.10 or later; `statistics.covariance` needs 3.10.

```python
from math import ceil
from statistics import NormalDist, covariance, fmean, variance


def z(p):
    return NormalDist().inv_cdf(p)


def n_means(sigma, delta, alpha=0.05, power=0.8, share=0.5, rho=0.0):
    """Units per arm for a difference in means; share is the treatment fraction."""
    k = (z(1 - alpha / 2) + z(power)) ** 2
    total = k * sigma**2 * (1 / share + 1 / (1 - share)) / delta**2
    total *= 1 - rho**2  # CUPED, if pre-registered
    return ceil(total * share), ceil(total * (1 - share))  # treatment, control


def ratio_sigma(xs, ys):
    """Per-unit sigma for mean(xs)/mean(ys), xs and ys per randomisation unit."""
    mx, my = fmean(xs), fmean(ys)
    r = mx / my
    v = variance(xs) - 2 * r * covariance(xs, ys) + r**2 * variance(ys)
    return (v / my**2) ** 0.5, r


if __name__ == "__main__":
    # Revenue per user: mean 4.10, sd 19.5, want to detect +2% relative.
    print(n_means(sigma=19.5, delta=0.02 * 4.10))
    print(n_means(sigma=19.5, delta=0.02 * 4.10, rho=0.6))
```

## Worked example

Revenue per user, baseline mean 4.10 and standard deviation 19.5 over four weeks of eligible users. Practical threshold +2% relative, so δ = 0.082.

- Without CUPED: 15.7 × 19.5² / 0.082² ≈ 888,000 users per arm.
- With CUPED at ρ = 0.6: × 0.64 ≈ 568,000 per arm.
- History shows 640,000 distinct eligible users in 7 days, 1.05 million in 14, 1.38 million in 21 and 1.66 million in 28. At 50/50 the CUPED design needs 1.14 million in total: three weeks. The design without CUPED needs 1.78 million, more than four weeks provide, so it would need a larger MDE.

Heavy-tailed metrics like revenue per user often have σ several times the mean. Capping (winsorising) at a high percentile fixed in the plan, such as the 99.9th, reduces σ substantially; decide the cap before launch for the same reason as CUPED.
