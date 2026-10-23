# Protocol checklist

Contents: protocol template, deviation log, paired bootstrap.

## Protocol template (write before the final runs)

```text
Claim:                     one sentence
Metric and implementation: name, library and version, higher or lower better
Practical threshold:       smallest difference that matters, and why
Data:                      dataset release, train/validation/test split, how created
Baselines:                 name, source, commit, published number
Tuning:                    search space, trials per method, search method, compute cap
Selection data:            validation only / cross-validation inside train
Test policy:               touched once, after configuration is frozen
Seeds / splits:            count, how generated, same for every method
Analysis:                  paired difference, interval method, multiple-comparison handling
Cost reported:             wall time, parameters, compute
Ablations planned:         each claimed component
```

Date it and keep it with the code. Deviations after the final runs begin go in the deviation log, not in a rewritten protocol.

## Deviation log

| Item | Published / expected | Used | Reason | Measured effect on baseline number |
| --- | --- | --- | --- | --- |
| Library version | 1.4 | 2.1 | 1.4 does not build | +0.2 |
| Preprocessing | Lowercase and strip | Lowercase only | Script missing | -0.5 |
| Split | Authors' fixed | Re-created with seed 0 | Split file unavailable | Not measured |

"Not measured" is a valid entry; leaving the table out is not.

## Paired bootstrap on per-seed or per-dataset differences

```python
import numpy as np


def paired_bootstrap(a, b, higher_is_better=True, n_boot=10000, seed=0, level=0.95):
    """a, b: scores per seed (or per dataset), same order. Returns mean diff and interval,
    oriented so that positive always means the proposal is better."""
    d = np.asarray(a, float) - np.asarray(b, float)
    if not higher_is_better:
        d = -d
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return d.mean(), (lo, hi)


mean_diff, (lo, hi) = paired_bootstrap(proposal_scores, baseline_scores)
```

With five seeds the bootstrap interval is optimistic because it can only resample five differences; a t-interval on the differences (`scipy.stats.t.interval`) is wider and more honest at that size. For the Wilcoxon signed-rank test over datasets use `scipy.stats.wilcoxon(a, b)`; it needs enough non-tied pairs and says nothing about the size of the difference, so report the interval beside it.

Take `higher_is_better` from the protocol template, so an error-rate reduction is a positive difference. Compare the interval with the threshold from the protocol: lower bound above the threshold is a win; lower bound above zero but below it is a smaller gain than claimed; spanning zero is no detectable difference; an interval wholly below zero means the proposal is worse.
