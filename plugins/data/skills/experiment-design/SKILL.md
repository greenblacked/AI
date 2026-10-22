---
name: experiment-design
description: "Plan an A/B test before launch so its result can be trusted: write one primary metric and its guardrails down first, randomise on the same unit you analyse, size the test from baseline variance and a minimum detectable effect worth shipping (delta method for ratios), round the duration up to whole weeks, decide CUPED up front, fix a stopping rule against peeking, and A/A-test a new platform. Use when someone asks how long to run a test, how many users it needs, what to measure, whether to split by user or session, or says \"we want to A/B this\" or \"is two weeks enough\". Not for ramp and bake times (release-strategy), wiring a flag (feature-flag-lifecycle), reading out a finished test (experiment-readout), a painted-door test's pass threshold and sample size (fake-door-test), marketplaces where units interfere (switchback-test-design) or tuning game numbers (game-balance)."
allowed-tools: Read, Write, Glob, Grep
---

# Experiment Design

The design is done when a written plan, frozen before the first user is assigned, names the decision the test informs, one primary metric, the guardrails with their margins, the randomisation unit, the sample size and duration with the arithmetic behind them, the variance-reduction method and the stopping rule — so that the readout has nothing left to choose.

The usual failure is a test launched with a dozen metrics, no size and no end date, then read every morning until something crosses p < 0.05. Every choice left open until the data is in becomes a choice made by the data: the metric that moved, the segment that looked good, the day it happened to be significant. The plan exists to make those choices while nobody knows which answer they produce.

## Scope

Use for: a new user-level A/B or multi-arm test; choosing the primary metric and guardrails; sizing and scheduling; deciding on CUPED, triggering and sequential testing; checking a new experimentation platform with an A/A test.

Do not use for: choosing rollout percentages and bake times, which is `release-strategy`; implementing the flag the test rides on, which is `feature-flag-lifecycle`; reading out a test that has finished, which is `experiment-readout`; the pass threshold and sample size of a painted-door or fake-door demand test, which is `fake-door-test`; a traffic split that came out wrong, which is `srm-diagnosis`; drivers, inventory, queues or prices shared between users, where a user split is invalid, which is `switchback-test-design`; estimating the effect of something that was never randomised, which is `causal-inference-review`; a page whose traffic is too small for a standard user-level split to detect any lift worth acting on, which is `low-traffic-page-testing`.

This skill pre-approves no shell command. It reads plans, configs and metric definitions, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Write the decision before the metric

Write one sentence each for what you will do if treatment wins, loses, or shows nothing. If all three lead to the same action, do not run the test; it costs traffic and an analyst's week to confirm a decision already made. The decision also sets the practical threshold in step 5: the smallest effect that would change what you do.

### 2. Name one primary metric and the guardrails

Pick one primary metric that the change is meant to move and that the decision rests on. Two primaries need a multiple-comparison correction and usually signal that nobody agreed what success is.

List guardrails separately: metrics the change must not harm, each with a non-inferiority margin written as a number ("p95 page latency no worse than +50 ms", "refund rate no worse than +0.2 percentage points"). Always include the sample ratio check (expected split, flagged at p < 0.001) and the platform's own health metrics (errors, crashes, latency). Keep debugging metrics — click-through on the new button — in a third list that informs the story but never the verdict.

### 3. Make the randomisation unit the analysis unit

Randomise and analyse at the same unit, usually the user (logged-in id, or a durable device id when anonymous). If you randomise users but compute a per-session or per-page-view metric, observations within a user are correlated and a naive standard error is too small, so false positives rise. Either analyse per user, or treat the metric as a ratio of per-user sums and use the delta method (step 4).

Check two things here, because each changes the design rather than the numbers:

- **Interference.** If treated and control users compete for the same drivers, stock, ad budget or queue, or treatment changes a price everyone sees, a user split is biased. Stop and use `switchback-test-design`.
- **Triggering.** If only some users reach the changed code path, assign everyone but analyse only those who triggered, and log the trigger in control too (the point where they would have seen the change). Diluting the effect with users who never saw it costs power; triggering on something treatment influences breaks the comparison.

### 4. Measure baseline variance on the analysis population

Pull four weeks of history for the population the test will actually include, after triggering, at the analysis unit. Compute the metric's mean and standard deviation per unit. For a ratio metric (clicks per session, revenue per order, where numerator and denominator both vary per user) compute the variance with the delta method from per-user sums, not from the per-session values. Read `references/sample-size.md` for the formulas and a standard-library script.

### 5. Choose the minimum detectable effect, then the size and duration

Set the minimum detectable effect (MDE) from step 1's practical threshold — what is worth shipping — not from whatever traffic allows. Then compute the sample size per arm at two-sided alpha 0.05 and power 0.8 unless the plan says otherwise: for a difference in means, n ≈ 2 (z₀.₉₇₅ + z₀.₈)² σ² / δ² ≈ 15.7 σ² / δ².

Convert units to days from history of cumulative distinct eligible units over windows of 7, 14, 21 and 28 days, not daily traffic times days: returning users mean distinct users grow more slowly than days. Round the duration up to whole weeks, minimum one, so every weekday is equally represented. If the required duration is longer than the business will wait, the honest options are a larger MDE, a more sensitive metric, variance reduction, or not running it — not an underpowered test whose null result reads as "no effect".

Use an equal split for a two-arm test unless risk demands a small treatment arm; a 90/10 split needs roughly 2.8 times the total traffic of 50/50 for the same power.

### 6. Decide variance reduction before any data exists

Decide now whether the analysis uses CUPED (a regression adjustment on each unit's pre-experiment value of the metric) and fix the pre-period window, usually one to two weeks before assignment. It cuts variance by a factor of (1 − ρ²), where ρ is the correlation between pre-period and in-experiment values, so the required sample shrinks by the same factor. Decided after the results are visible, it is one more knob that can be turned until the answer looks right. Units with no pre-period history get a constant covariate and no reduction; record what share of the population that is.

### 7. Fix the stopping rule

Write the readout date. A fixed-horizon test is read once, at that date, and looking earlier is allowed only for guardrail harm. If people will look daily anyway, choose a sequential method before launch — a group-sequential design with an alpha-spending function, or always-valid p-values if the platform provides them — and record which. A fixed-horizon p-value checked repeatedly and stopped at the first significant reading has a false-positive rate well above its nominal 5%.

Write the early-stop rule for harm separately: which guardrail, what threshold, who decides.

### 8. Run an A/A test when the platform is new

When the assignment service, the metric pipeline or the analysis code is new or changed, run both arms on identical experiences for a week before trusting it. Expect the sample ratio check to pass and roughly 5% of metrics to show p < 0.05 at random. Many more than that, or a primary metric that is consistently "significant", means the variance calculation or the unit of analysis is wrong, and every real test on the platform inherits the error.

### 9. Freeze the plan

Write the plan using `references/preregistration.md` and store it beside the experiment configuration with a date. Changing it after launch is allowed only with the change and its reason written down, before anyone has read the results.

## Output format

Hand back the pre-registration document from `references/preregistration.md`, filled in, with the sample-size arithmetic shown.

## Anti-patterns

**Sizing from available traffic.** "We have two weeks of traffic, so the MDE is whatever that gives" produces tests that cannot detect any effect worth having, then report the null as reassurance.

**Many primary metrics.** Twenty metrics at alpha 0.05 give about one false positive per test. One primary decides; the rest are guardrails or context.

**Per-page-view analysis of a per-user split.** The standard error ignores within-user correlation and the test is more confident than its data.

**Stopping on the first green day.** Repeated looks at a fixed-horizon test inflate false positives. Pick a horizon or a sequential method before launch.

**Choosing CUPED or segments after the fact.** Any analysis decision made with the results visible is a degree of freedom spent on the answer.

**A partial-week duration.** Ten days over-weights whichever weekdays appear twice; weekday and weekend users often behave differently.

## Reference files

- `references/sample-size.md` — read at steps 4 to 6: sample size for means and proportions, the delta method for ratio metrics, unequal splits, the CUPED adjustment, and a standard-library Python calculator.
- `references/preregistration.md` — read at step 9: the plan template, and the review checklist to run on someone else's plan.
