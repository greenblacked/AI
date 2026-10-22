---
name: model-drift-monitoring
description: "Monitor a deployed classical model and decide when to retrain: check in order input schema and null rates, feature distributions (PSI or KS statistic against the training window, per-feature thresholds from history), prediction distribution, then delayed-label performance on matured cohorts; measure label delay and pick a proxy for the gap; make the retrain trigger a performance or cost metric, never drift alone; promote a challenger only by beating the champion on the same frozen eval set, with one-command rollback. Use for \"what should we monitor now the model is live\", \"PSI is over 0.25, do we retrain\", \"labels take two months, how do we know it is getting worse\" or \"champion challenger\". Not for service objectives (slo-design), paging rules (alert-design), offline and online scores disagreeing for one request (serving-skew-replay) or weak slices (model-error-analysis)."
allowed-tools: Read, Glob, Grep
---

# Model Drift Monitoring

Monitoring is done when one deployed model has four layers of checks in a fixed order, each with a threshold, an action and an owner; when its label delay is measured and a proxy covers the weeks before labels arrive; when a written rule says what triggers a retrain and that rule names a performance or cost metric; and when a challenger can only replace the champion by beating it on the same frozen evaluation set, through a promotion that one command reverses and that has been reversed once in rehearsal.

Two failures recur. The first is a drift dashboard on every feature: with enough rows every statistical test fires, the weekly alert is ignored, and when a real break comes it is ignored too. The second is retraining on drift or on a calendar without a gate: a retrain on a window that contains a pipeline defect teaches the model the defect, and nobody notices for the length of the label delay. The order of the layers below exists because a broken upstream column shows up as feature drift, then as prediction drift, then, weeks later, as a performance drop; catching it at the first layer is the whole point.

## Scope

Use for: what to monitor on a classifier or regressor already in production; setting drift thresholds that do not fire on noise; measuring label delay and choosing a proxy; writing the retrain trigger; the champion-versus-challenger gate and rollback.

Do not use for: availability and latency objectives for the serving endpoint, which is `slo-design`; turning these checks into paging rules and routing, which is `alert-design` once the thresholds here exist; one request scored differently online and offline, which is `serving-skew-replay`; finding the segments where the model is weak, which is `model-error-analysis`; judging a time-series forecast, which is `forecast-backtesting`; the hosted model behind a feature changing version under you, which is `model-migration`.

## Workflow

### 1. Write down the decision, the cost and the label delay

Before any monitor, record three things, because every threshold later is chosen against them.

- What the model decides and what each kind of error costs: a missed fraud case against a blocked good customer, an over-forecast against an under-forecast. The performance metric follows from the costs (precision at a fixed recall, expected cost per thousand decisions), not from habit.
- The label: its exact definition and the window over which it is observed.
- The label delay, measured: for cohorts old enough that their labels are complete, the share of eventual labels that had arrived 1, 7, 30 and 90 days after prediction. The maturity point is the lag by which nearly all labels have arrived. For an outcome that is "did the event happen within N days", negatives only become final when the window closes, so maturity is at least N.

Read `references/retrain-and-promotion.md` for the label-delay query.

### 2. Layer 1: input schema and null rates

On every scoring batch, or every hour for an online model: expected columns present with expected types, enum values within the known set, null rate per feature against its training rate, and row count against the usual volume for that hour and weekday.

A failure here is a data defect, not drift. Block the batch or alert the owner of the upstream data, and do not let the model score silently on a column that has turned to nulls. Most incidents that get called model drift are found here.

### 3. Layer 2: feature distributions

Compare each feature's current window against the training window, the data the model actually learned from.

- Numeric features: PSI over bins taken from the training deciles, and the two-sample KS statistic. Use the statistic, not the p-value: at hundreds of thousands of rows the p-value is tiny for differences nobody would act on.
- Categorical features: PSI over categories, with rare ones pooled into an "other" bin, or the Jensen-Shannon distance.

Set the threshold per feature. The conventional PSI bands (below 0.1 stable, 0.1 to 0.25 moderate, above 0.25 significant) are a starting point from credit scoring, not a law. Calibrate each feature's threshold from its own history: compute PSI for each window inside the training period against the full training reference, the same comparison the live monitor makes, which gives the noise floor when nothing changed, and set the threshold above the high end of that spread. Where a feature has a weekly or annual cycle, compare against the same point in the previous cycle as well, or the cycle itself fires the alert.

Weight attention by importance. Drift on a feature the model barely uses is a note; drift on one of its top five features is an investigation.

The action at this layer is an investigation, not a retrain. Read `references/drift-statistics.md` for the formulas, binning, threshold calibration and code.

### 4. Layer 3: prediction distribution

Watch the score distribution (PSI against the validation scores), the share of decisions on each side of the operating threshold, and the mean prediction against the expected base rate. This needs no labels, so it is the earliest signal that the model's behaviour, rather than its inputs, has changed. A jump in the approval rate or the alert rate is usually what the business sees first; it should not be what the model's owner sees first.

### 5. Layer 4: delayed-label performance, and a proxy for the gap

Compute the performance metric by prediction-date cohort, only on cohorts past the maturity point, with a confidence interval. A cohort scored before maturity always looks worse because its positives have not arrived yet, which is the most common false alarm at this layer.

For the weeks before maturity, choose a proxy and validate it on history before trusting it: the partial label rate at a fixed age compared with past cohorts at the same age, the human override or appeal rate, a downstream conversion. A proxy that did not move in past periods when the matured metric fell is not a proxy.

### 6. Write the retrain trigger

The trigger is a performance or cost metric crossing a threshold on matured cohorts, for a stated number of consecutive cohorts, or the validated proxy crossing its own threshold. A scheduled retrain is acceptable, but it still passes the promotion gate in step 7.

Drift alone opens an investigation with three outcomes:

| Finding | Action |
| --- | --- |
| A pipeline or upstream defect | Fix the pipeline. Do not retrain on a window containing the defect, or the model learns it. |
| A real population change, proxy and performance steady | Record it; consider moving the reference window. No retrain. |
| A real population change with the proxy falling | Bring the retrain forward, then gate it as usual. |

### 7. Promote only through a frozen comparison, with rollback ready

Train the challenger on data up to a cutoff. Build the evaluation set from the matured period after the cutoff, freeze it, and score champion and challenger on exactly the same rows. Compare on the step 1 metric with a paired bootstrap interval on the difference, and check every agreed slice so an overall gain does not hide a regression for one segment (`model-error-analysis` sets those slices). Then run the challenger in shadow on live traffic to compare its prediction distribution and latency before it takes any decision.

Promote by moving a pointer, such as a registered-model alias, not by overwriting the artefact. Keep the previous champion and the feature code version it needs loadable. Rehearse the rollback before the promotion, so the one command is known to work.

Read `references/retrain-and-promotion.md` for the trigger policy template, the promotion checklist and the rollback drill.

## Output format

```markdown
## Model and decision
[What it decides, error costs, performance metric, label definition, measured label delay and maturity point.]

## Monitors
| Layer | Check | Window and reference | Threshold | Action | Owner |

## Proxy
[The proxy, and the historical evidence that it tracks the matured metric.]

## Retrain trigger
[The metric, threshold and number of cohorts; what drift alone does.]

## Promotion and rollback
[Frozen eval set definition, comparison and slice gate, shadow period, the rollback command and when it was last rehearsed.]
```

## Anti-patterns

**Every feature, one threshold, a p-value.** At production sample sizes everything is significant. Use effect-size statistics with per-feature thresholds from history.

**Retraining because drift fired.** Drift says the inputs moved, not that decisions got worse. If the cause is a broken pipeline, the retrain bakes it in.

**Reading immature cohorts.** Last week's precision looks terrible because its positives have not arrived. Report matured cohorts and label the rest provisional.

**A challenger judged on its own validation split.** Each model scored on different rows is no comparison. Same frozen set, paired difference.

**Promotion by overwrite.** Replacing the artefact in place leaves nothing to roll back to. Move a pointer and keep the old model loadable.

## Reference files

- `references/drift-statistics.md` — read at steps 3 and 4: PSI and KS defined, binning and empty-bin handling, categorical measures, calibrating per-feature thresholds from history, and code.
- `references/retrain-and-promotion.md` — read at steps 1, 5, 6 and 7: the label-delay query, validating a proxy, a retrain trigger policy template, the promotion checklist and the rollback drill.
