# Convergence checks

## Batch means for one long correlated run

```python
import numpy as np


def batch_means_se(x, n_batches=None):
    x = np.asarray(x)
    N = len(x)
    b = n_batches or int(np.sqrt(N))
    m = N // b  # batch length
    means = x[: b * m].reshape(b, m).mean(axis=1)
    return means.mean(), means.std(ddof=1) / np.sqrt(b)
```

Batches must be long enough that their means are roughly independent; if the standard error keeps rising as batches are made longer, the run is too short for its autocorrelation. The effective sample size follows from the batch-means standard error: ESS = var(x) / SE^2.

## Diagnostics and what a failure means

| Diagnostic | Usual threshold | If it fails |
| --- | --- | --- |
| Split R-hat | below 1.01 | Chains disagree: run longer, check for multimodality, reparametrise |
| Bulk ESS | about 100 per chain (400 for four chains) at minimum | Draws too autocorrelated for means and medians: run longer or reparametrise |
| Tail ESS | same floor | Quantiles in the tails are unreliable: run longer |
| MCSE relative to posterior sd | small enough for the digits you report | Report fewer digits or run longer |
| Divergent transitions | zero, or understood | Geometry problem: reparametrise, raise target acceptance, do not just run longer |
| Tree-depth saturation | rare | Efficiency problem: reparametrise or rescale |
| BFMI (energy) | above about 0.3 | Poor exploration of the energy distribution |
| Trace and rank plots | chains overlap and mix | Look for stuck or drifting chains |

Thresholds are conventions from the literature on rank-normalised R-hat and ESS; treat them as floors, and tighten them when a claim depends on the third digit.

## Burn-in

Plot the chains from their starting points and find where they merge; discard before that point, or use warm-up built into the sampler and discard it. Do not discard a fixed fraction without looking. Burn-in matters little when starts are inside the typical set and a lot when they are not.

## Rare events and quantiles

For a probability p estimated from n independent runs, the relative standard error is about sqrt((1 - p) / (n p)), so a 10 percent relative half-width at 95 percent needs n close to 400 (1 - p) / p runs, about 400 expected hits. At p = 1e-4 that is about four million runs, which is why plain sampling is replaced by importance sampling or splitting there; then the effective sample size of the weights is what to report. For a quantile, precision depends on the density at the quantile; bootstrap the quantile across independent replications when in doubt.

## Common random numbers

Same stream for both configurations, one pair per replication: d_i = f(A, u_i) - f(B, u_i). Interval from the mean and standard error of d_i. Check that the correlation between f(A, u_i) and f(B, u_i) is positive; if the configurations consume random numbers in different orders, the streams drift apart after the first difference and the benefit is lost, so draw each source of randomness from its own sub-stream.
