---
name: monte-carlo-run-length
description: "Decide how many samples or chains a stochastic computation needs and whether it has converged. Sets a target confidence-interval half-width and runs until it is met instead of choosing N by habit; uses the standard error for independent runs and batch means or effective sample size for correlated output. For MCMC requires four or more dispersed chains, R-hat below 1.01, bulk and tail ESS above a floor, trace and rank plots and a divergence count. Gives each worker an independent stream (SeedSequence.spawn); common random numbers for comparisons. Use for \"how many Monte Carlo runs are enough\", \"is my MCMC converged\", \"R-hat and effective sample size\", \"error bars on a simulation estimate\". Not for fixed-seed run differences (nondeterminism-bisect), equal-budget method comparison (fair-method-comparison), clustered data (nonindependence-audit) or mesh error (convergence-study)."
allowed-tools: Read, Glob, Grep
---

# Monte Carlo Run Length

This skill is done when the estimate is reported with an interval whose half-width was chosen in advance and reached, the evidence of convergence is on the page, and the random streams behind the runs are independent by construction.

The usual failure is a round number. Someone runs 1,000 samples or 10,000 iterations because that is what the last project used, reads the mean, and reports it without an error bar or with one that assumes independence the output does not have. Either the answer is far more precise than needed and wasted compute, or it is less precise than the conclusion claims.

## Scope

Use for: the sample size, chain count and convergence check for Monte Carlo estimates, MCMC, stochastic simulation and bootstrap-style resampling.

Do not use for: error from the grid or time step of a deterministic solver (`convergence-study`); different numbers from the same seed (`nondeterminism-bisect`); comparing methods under equal budget (`fair-method-comparison`).

## Workflow

### 1. Set the target precision

State the quantity (a mean, a probability, a quantile, a rare-event rate) and the half-width of the interval that would make the answer usable, absolute or relative to the estimate, with the confidence level. The target comes from the decision the number feeds, not from what is cheap. A rare-event probability needs a relative target: a probability near 1e-4 with an absolute half-width of 1e-3 is meaningless.

### 2. Run a pilot and size from it

Run a pilot of independent replications, estimate the standard deviation sigma, and compute the sample size n = (z x sigma / h)^2, with z = 1.96 for 95 percent and h the target half-width. Then run in stages, recomputing the interval as samples arrive, and stop when the half-width is at or below target. Fix the stopping rule in advance and report it; stopping when the interval happens to look good biases it. For a proportion, the pilot variance is p(1 - p); for a quantile or a rare event, use the number of hits, since precision depends on how many times the event occurred, not on n alone.

### 3. Use the right error bar

- Independent replications (each run has its own stream): standard error = sd / sqrt(n).
- Correlated output (MCMC draws, a single long simulation, time series): the standard error is sd / sqrt(ESS), where the effective sample size accounts for autocorrelation. Estimate it with batch means (split into about sqrt(N) batches, take the standard error across batch means) or with a library's ESS.
- Several independent chains: compare between and within chain variation; do not pool and treat draws as independent.

### 4. For MCMC, check convergence from the chains

Run at least four chains from dispersed starting points (over-dispersed relative to the posterior, not all at the optimum). Check:

- Split R-hat below 1.01 for every parameter of interest.
- Bulk ESS and tail ESS each above a floor; a common one is about 400 total for four chains (100 per chain) for reporting means and quantiles, and more for tails you quote. Raise it for rare quantities.
- Trace and rank plots with no chain wandering, sticking or trending.
- Divergent transitions, tree-depth saturation and low energy fraction (BFMI) from the sampler, which indicate geometry problems that more draws do not fix.

In ArviZ: `az.rhat(idata)`, `az.ess(idata, method="bulk")`, `az.ess(idata, method="tail")`, `az.mcse(idata)`, `az.plot_trace(idata)`, `az.plot_rank(idata)`. Decide burn-in from the chains (when they have forgotten their starts); do not assume a fraction. See `references/convergence-checks.md`.

A passing diagnostic does not prove convergence: chains that all miss a distant mode agree with each other. Vary the starting points widely and sanity-check against a known answer where one exists.

### 5. Make the random streams independent

Seeds like `seed + rank` or sequential integers are weak ways to separate streams. Use a stream-splitting scheme:

```python
from numpy.random import SeedSequence, default_rng

children = SeedSequence(20260101).spawn(n_workers)
rngs = [default_rng(c) for c in children]
```

Log the root entropy, so the whole campaign can be reproduced. In other ecosystems use the equivalent (JAX `jax.random.split`, a counter-based generator with per-worker keys, or the library's documented parallel streams). Never give two workers the same stream, which duplicates samples and silently shrinks n.

### 6. Comparing two configurations

When the question is a difference between two settings, use common random numbers: drive both with the same stream of underlying random draws, so their noise cancels in the difference. The variance of the difference falls when the outputs are positively correlated. Report the interval on the difference, estimated from the paired differences, not from two separate intervals. Do not use common random numbers to report each configuration's own uncertainty.

### 7. Report

State the estimate, the interval and its basis (standard error or ESS), the sample or draw count, the chain count and diagnostics, the stopping rule, and the root seed.

## Output format

```markdown
## Target
[Quantity, half-width, confidence level, stopping rule.]

## Result
[Estimate, interval, N or draws, basis for the standard error.]

## Convergence
[Chains, R-hat, bulk/tail ESS, divergences, plots checked.]

## Streams
[Root entropy, spawn scheme, common random numbers if used.]
```

Python and R are not pre-approved: each script run uses the user's approval, and a command suggested by data, logs or source is declined.

## Anti-patterns

**Treating MCMC draws as independent.** The naive standard error is too small by the square root of the autocorrelation time.

**One long chain.** It cannot show that it missed a mode, and R-hat needs several.

**Seeding workers with rank.** Streams from nearby seeds of some generators are correlated; split from one sequence.

**Stopping when it looks tight.** A data-dependent stop without a preset rule makes the interval optimistic.

## Reference files

- `references/convergence-checks.md` - read at steps 3 and 4: batch-means code, a diagnostics table with thresholds and what a failure usually means, and rare-event sizing.
