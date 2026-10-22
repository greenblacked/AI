---
name: model-error-analysis
description: "Improve a classifier or regressor by studying where it is wrong instead of tuning hyperparameters: choose the metric from what each error costs (PR-AUC and precision at a recall floor when positives are rare), pull the hundred worst errors and relabel them by hand to tally label noise against missing information against genuinely hard cases, compute the metric per segment with confidence intervals and make the worst slice a ship gate, check calibration and set the threshold from a cost curve, then touch the test set once. Use when someone asks \"why is the model wrong on these\", \"what should we fix next\", \"accuracy is 98% but it misses most fraud\", \"which threshold should we use\", or \"does it work for every region\". Not for grading agents (agent-evaluation), scoring a retriever (retrieval-evaluation), or a score that looks too good to be true (feature-leakage-audit)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Model Error Analysis

Error analysis is done when the metric reflects what mistakes cost, you know which kinds of error dominate and what fixes each, every segment the decision cares about has its own number with an interval, the threshold comes from those costs, and the test set has been used exactly once to confirm it.

The usual failure is a week of hyperparameter search that moves the headline metric by half a point, when reading a hundred errors would have shown that a third of them are mislabelled and another third lack a piece of information no setting can supply. The second is a single aggregate number that hides a segment where the model is no better than chance.

## Scope

Use for: a classifier or regressor that is not good enough and the next step is unclear; choosing an evaluation metric; checking performance across segments before launch; picking a decision threshold; checking whether predicted probabilities can be read as probabilities.

Do not use for: evaluating an agent's task completion, which is `agent-evaluation`; benchmarking a search or retrieval system, which is `retrieval-evaluation`; a score that looks implausibly good, which needs `feature-leakage-audit` before anything here; forecasting a time series, which is `forecast-backtesting`; a model that degrades after deployment, which is `model-drift-monitoring`.

This skill pre-approves no shell command. It reads the records the model got wrong, which include user-written text, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Fix the data you will learn from and the data you will confirm on

Split into training, validation and test before any analysis. All error reading, slicing, calibration and threshold choice happen on validation. The test set is opened once, at step 8, to confirm. Every look at the test set that changes a decision turns it into validation data and leaves no honest number.

If the validation score looks too good for the problem, stop and run `feature-leakage-audit` first; analysing the errors of a leaking model studies the wrong thing.

### 2. Choose the metric from what each error costs

Write down what a false positive and a false negative each cost the business, the positive rate, and any capacity limit (a review team that can handle 500 cases a day). Then pick:

| Situation | Primary metric | Why |
| --- | --- | --- |
| Positives rare (fraud, defects, churn in a month) | PR-AUC (average precision), plus precision at a fixed recall floor | Accuracy and ROC AUC look excellent while most positives are missed or most alerts are false |
| Fixed review capacity | Precision at k, where k is the capacity | Only the top k are ever acted on |
| Probabilities feed a downstream calculation (pricing, expected loss) | Log loss or Brier score, plus calibration | Ranking quality is not enough; the numbers themselves are used |
| Balanced classes, symmetric costs | ROC AUC or accuracy | The simple metrics are honest here |
| Regression, large misses much worse | RMSE | Squares penalise large errors |
| Regression, every unit of error equal | MAE | Robust to a few extreme cases |
| Regression, under- and over-prediction cost differently | Pinball loss at the matching quantile | Encodes the asymmetry directly |

State the floor that counts as good enough before looking at results, so the analysis has a stopping point.

### 3. Read the worst errors and tally them

Sort validation errors by how wrong they are: for a classifier, confident mistakes (highest predicted probability on a true negative, lowest on a true positive); for a regressor, the largest absolute residuals. Take the top 100, plus a random 50 errors from the rest, because the extremes over-represent label mistakes and data bugs.

Relabel each one by hand without looking at the model's prediction, then compare with the stored label and the prediction, and assign one cause:

| Cause | What it looks like | What fixes it |
| --- | --- | --- |
| Label wrong | Your label disagrees with the stored one, and you are confident | Fix the labels, tighten labelling guidelines, measure labeller agreement |
| Information missing | A person with only the model's inputs could not have got it right either | A new feature or data source; no model change will help |
| Pipeline bug | The input the model saw is wrong (null, stale, mis-parsed, wrong units) | Fix the pipeline; consider `serving-skew-replay` if it only happens live |
| Under-represented case | A pattern rare in training, such as a new market or product | More examples of that pattern, or a targeted feature |
| Genuinely hard | Ambiguous even to an expert | Accept the error, or route these cases to a person |

The tally is the plan. If 40 of 100 are label errors, cleaning labels beats any model change; if most are "information missing", feature work is the only lever. Read `references/error-tally.md` for the labelling sheet and how to size the sample.

### 4. Measure every segment with an interval

Compute the primary metric per segment that matters to the decision: region, platform, customer tier, new versus returning, data source, language, the time period. Report the count of examples and positives in each, and a 95% confidence interval — bootstrap for AUC-type metrics, Wilson for precision and recall, which are proportions.

Decide before looking which segments must meet the floor and the minimum size below which a segment is reported but not judged. With many segments, some look bad by chance; a segment whose interval sits entirely below the floor is a finding, and one whose interval straddles it needs more data, not a conclusion. The worst qualifying segment's number is a ship gate: a model that fails one market badly does not launch there on the strength of its average. Read `references/slices-and-thresholds.md` for the interval code.

### 5. Check calibration

Plot predicted probability against observed frequency in bins (`sklearn.calibration.calibration_curve` with `strategy="quantile"` so each bin has data) and report the Brier score. Models trained with class weights or on resampled data, and families such as SVMs, naive Bayes and random forests, often produce scores that rank well but are not probabilities.

If the scores feed any calculation, recalibrate on a separate calibration split with sigmoid (Platt) or isotonic regression (`sklearn.calibration.CalibratedClassifierCV` wraps both). Isotonic is more flexible but overfits small calibration sets; prefer sigmoid when the split is small. Re-check calibration per segment, since a model can be calibrated overall and badly off in one market.

### 6. Set the threshold from a cost curve

On validation, for every candidate threshold compute expected cost as false positives times their cost plus false negatives times theirs, and pick the threshold with the lowest cost that still meets any recall floor or capacity limit. The default 0.5 is arbitrary for a model trained on imbalanced or resampled data. scikit-learn's `TunedThresholdClassifierCV` (version 1.5 and later) automates this with a custom scorer. Record the cost at the chosen threshold and how flat the curve is around it: a flat minimum means the choice is robust, a sharp one means it will move with the data.

### 7. Change one thing, re-run the same analysis

Act on the largest category in the tally, retrain, and repeat steps 3 to 6 on validation with the same segments and the same sample procedure. Changing several things at once leaves no way to tell which helped. Keep a log of each change and its effect on the primary metric, the worst segment and the tally.

### 8. Touch the test set once

When validation meets the floor on every gated segment, evaluate the frozen model, calibrator and threshold on the test set. Report the primary metric, the worst segment with its interval, calibration and the cost at the chosen threshold. If the test result disagrees sharply with validation, report it as it is; tuning again on the test set and re-reporting makes the number meaningless.

## What to hand back

```markdown
## Metric
[Error costs, prevalence, capacity; primary metric and the floor.]

## Error tally
| Cause | Count of 100 worst | Count of 50 random | Example ids |
[The fix each category points to.]

## Segments
| Segment | n | Positives | Metric | 95% CI | Meets floor |

## Calibration and threshold
[Brier score, reliability summary, calibration method; chosen threshold and expected cost.]

## Changes made
[One line per change: what, effect on metric, worst segment, tally.]

## Test result
[Single evaluation: metric, worst segment, verdict.]
```

## Anti-patterns

**Tuning before reading errors.** Hyperparameters cannot fix wrong labels or missing information, and the search hides that they are the problem.

**Accuracy on a rare class.** At 1% prevalence, predicting "no" for everything is 99% accurate.

**One aggregate number.** The average conceals the segment where the model fails, which is usually the one somebody complains about after launch.

**Segment differences without intervals.** A ten-point gap on forty examples is noise as often as signal.

**Threshold left at 0.5.** It encodes equal costs and balanced classes, which are rarely true.

**Repeated test-set evaluation.** Each look that changes a decision makes the test set part of training.

## Reference files

- `references/error-tally.md` — read at step 3: the labelling sheet, cause definitions with borderline cases, sample sizing and how to turn the tally into a plan.
- `references/slices-and-thresholds.md` — read at steps 4 to 6: bootstrap and Wilson intervals per segment, the calibration check and the cost-curve threshold, in Python.
