---
name: feature-leakage-audit
description: "Detect target leakage before trusting a model's offline score: for every feature record when its value becomes known against the moment of prediction, rebuild joins point-in-time, split by time or by entity group instead of random rows, fit encoders, scalers, imputers and feature selection inside each training fold only, flag implausibly strong single features, delete each suspect and re-measure the drop, then hunt duplicates and near-duplicates across the split. Use when a validation score looks too good to be true, when someone asks \"is there leakage in this model\", \"is our train/test split right\", \"can I target-encode before splitting\", or before a model's first launch. Not for live features that differ from training ones (serving-skew-replay), studying where an honest model makes mistakes (model-error-analysis), or choosing test cases for code (test-design)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Feature Leakage Audit

A leakage audit is done when every feature has a recorded time at which its value becomes known, every one of those times is at or before the moment of prediction, the evaluation split matches how the model will meet new data, every fitted transformation saw training folds only, and the score that remains after removing the suspects is the one reported.

The usual failure is a model that scores 0.97 offline because one column was filled in by the process that produced the label — a cancellation reason, a collections flag, a "last contacted" date refreshed after the outcome — and nobody asked when that column was written. The second is a random row split over data with many rows per customer, so the model memorises customers and the test set rewards it.

## Scope

Use for: auditing a model before launch or before trusting a new score; a validation number that looks too good; choosing an evaluation split; checking preprocessing for train/test contamination; explaining a feature that dominates importance.

Do not use for: a model whose live inputs differ from the ones it was trained on, which is `serving-skew-replay`; improving an honestly evaluated model by studying its mistakes, which is `model-error-analysis`; deciding what unit tests a code change needs, which is `test-design`; monitoring a deployed model's inputs over time, which is `model-drift-monitoring`.

This skill pre-approves no shell command. It reads feature code, notebooks and table documentation, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Define the moment of prediction and the label window

Write down, for one row: the entity, the timestamp at which the model will be called in production, and the window over which the label is observed. "Will this customer churn in the 30 days after their renewal notice" has a prediction time (the notice) and a label window (the next 30 days). Every later step compares against that timestamp; without it, "known before the prediction" has no meaning.

If the training table has no prediction timestamp per row, that is the first finding. A table built from a current snapshot with labels attached has already mixed past and future.

### 2. Build the feature timeline

List every feature with four facts: its source table or system, the timestamp that governs when it becomes available (the event time and, separately, the load time into the warehouse), whether the source row is updated in place, and a verdict.

| Feature | Source | Available at | Updated in place? | Verdict |
| --- | --- | --- | --- | --- |
| `days_since_last_login` | `users.last_login_at` | Overwritten on every login | Yes | Leak: computed at extraction, not at prediction time |
| `plan_tier` | `subscriptions` snapshot | Daily snapshot load, 02:00 | No | Safe if joined as-of |
| `cancellation_reason` | `cancellations` | Written when the customer cancels | No | Leak: exists only for positives |

Columns updated in place are the commonest source: a status, a balance, a "last seen" date or a count read from a current-state table describes the world at extraction time, which for training rows is after the outcome. Read `references/leak-patterns.md` for the catalogue of leak shapes by domain and the point-in-time join patterns.

### 3. Rebuild the joins point-in-time

Join every source on its availability time being at or before the prediction time, taking the latest value that satisfies it. Subtract pipeline latency: a table loaded nightly is not available at 09:00 for events that happened at 08:00. Windowed aggregates ("orders in the last 90 days") must end at the prediction time, not at the extraction date.

In pandas this is `pd.merge_asof(left, right, left_on="prediction_ts", right_on="available_ts", by="entity_id", direction="backward")`, with both frames sorted on their time keys; add `allow_exact_matches=False` when a value stamped at the same instant as the prediction would not yet be visible. In SQL, join on `available_ts <= prediction_ts` and pick the latest row per entity and prediction with a window function. A feature store's point-in-time retrieval does the same, provided each feature's timestamp is its availability time rather than its processing time.

### 4. Split the way the model will meet new data

| Production meets | Split | Why |
| --- | --- | --- |
| Future periods for known entities | Time: train before a cut-off, test after, with a gap at least as long as the label window | Training labels must not observe the test period |
| New entities (new customers, new patients, new devices) | Group: all rows of an entity on one side, with `GroupKFold` or `StratifiedGroupKFold` | Rows of one entity are correlated; a random split lets the model recognise them |
| Both | Time split, then drop test entities that appear in training | Measures the harder of the two cases honestly |

A random row split is defensible only when rows are independent and the world is stationary, which is rare for anything about customers or behaviour over time.

### 5. Fit every transformation inside the training fold

Anything that learns from data — scalers, imputers, category vocabularies, target or frequency encoders, PCA, feature selection, oversampling, text vectorisers — is fitted on the training fold and applied to the validation fold. Put the whole chain in an `sklearn.pipeline.Pipeline` (or `imblearn.pipeline.Pipeline` when it includes resampling) and pass the pipeline, not pre-transformed data, to `cross_validate`.

Target encoding needs one more step: on training data, encode each row with statistics from other folds. `sklearn.preprocessing.TargetEncoder.fit_transform` does this cross fitting internally; calling `fit` and then `transform` on the same training data does not, and leaks each row's own label into its feature.

Hyperparameters chosen on the same folds that report the score inflate that score; tune on an inner split or a separate validation set and report on data the search never saw.

### 6. Screen each feature on its own

Score every feature alone against the label on the validation data: for a numeric feature, the ROC AUC of the raw value as a score (take the larger of AUC and one minus AUC, since direction does not matter); for a categorical one, an out-of-fold target mean; for regression, the R² of a one-feature model. Also inspect the full model's top importances and the missing-value rate by label class.

Flag any single feature whose score approaches the full model's, any feature that beats what domain experts or the current process achieve, and any feature that is missing almost only for one class — a field filled in after the outcome shows up as a missingness pattern before it shows up as a value. Read `references/audit-checks.md` for the screen, ablation and duplicate code.

### 7. Delete each suspect and re-measure

Retrain under the honest split from step 4 without each flagged feature, one at a time, then without all of them. Record the drop in the primary metric. A large drop from a feature whose availability time is after prediction time is a confirmed leak: remove it, rebuild it point-in-time if a legitimate version exists, and report the score without it. A large drop from a feature that is genuinely available is not a leak; keep it, and write down why it is so predictive so the next reviewer does not repeat the work.

### 8. Look for duplicates across the split

Count rows in the test set whose feature vectors exactly match a training row, then look for the same entity under different identifiers (normalised email, device, address), near-duplicate text or images, and augmented copies of one original landing on both sides. Remove them from the test set and re-measure. A model that is mostly recalling duplicates scores well offline and falls apart on genuinely new inputs.

### 9. Report the honest number

Evaluate once on a time-forward holdout built with the corrected pipeline, and report that score alongside the original. When a shadow deployment or a live trial exists, compare its score with the holdout's; a gap that remains points to `serving-skew-replay` rather than to more leakage.

## What to hand back

```markdown
## Prediction setup
[Entity, prediction timestamp, label window, deployment pattern.]

## Feature timeline
[Table: feature, source, available at, updated in place, verdict.]

## Split and preprocessing
[Split used and why; transformations moved inside folds.]

## Suspects
| Feature | Solo score | Metric without it | Verdict |

## Duplicates
[Exact, entity-level and near-duplicate counts across the split.]

## Result
[Original score, corrected score on the time-forward holdout, features removed or rebuilt.]
```

## Anti-patterns

**Trusting a score because it is high.** A single feature carrying the model is a question before it is a result.

**Features from current-state tables.** A status or balance read today describes the world after the outcome for every historical row.

**Preprocessing before the split.** Scaling, encoding or selecting features on the full dataset lets the test set shape the training data.

**Random splits over repeated entities.** The model learns the customer, not the pattern, and the test set shares the customers.

**Dropping a feature without re-measuring.** Removing a suspect without measuring the drop leaves the next person unable to tell whether it was a leak or a strong legitimate signal.

## Reference files

- `references/leak-patterns.md` — read at steps 2 and 3: leak shapes by domain, the questions to ask of each source, and point-in-time join patterns in SQL and pandas.
- `references/audit-checks.md` — read at steps 6 to 8: single-feature screen, ablation loop, missingness by class and duplicate detection code.
