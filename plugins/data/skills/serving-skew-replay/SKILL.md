---
name: serving-skew-replay
description: "Find why a model scores well offline and badly live by proving or ruling out train/serve skew: log the exact served feature vector with a request id and timestamp, replay the same entities through the training feature pipeline as of that timestamp, diff column by column, ranked by scaled mean absolute difference and prediction impact, and pin each gap on null handling, a stale join, time zone, categorical vocabulary or units. The fix is one shared feature code path, not a retrain. Use when someone says \"great in validation, bad in production\", \"online scores don't match the batch scores\", \"same user, different score\" or \"is this training-serving skew\". Not for leakage that made offline scores too good (feature-leakage-audit), inputs shifting over time (model-drift-monitoring), stale cached responses (application-caching) or finding weak slices (model-error-analysis)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Serving Skew Replay

The investigation is done when, for a sample of real requests, you hold two vectors per request — the one the model was actually served and the one the training pipeline produces for the same entity at the same instant — a ranked table of where they differ, a named cause for every feature near the top of it, a fix that leaves exactly one code path computing each feature, and a replay check on a schedule so the next divergence is caught by a job rather than by a business metric.

The usual failure is a retrain. Live performance comes in below the offline number, someone calls it drift, and the model is retrained on the same training-path features it was trained on before. It is then served the same different features, and the gap survives the retrain. The second failure is comparing feature histograms between training and serving, finding them alike, and declaring no skew. A join on a lagged snapshot or a shuffled vocabulary index can leave every marginal distribution untouched while every row is wrong. Only a diff on the same request key sees it.

## Scope

Use for: a model that validated well and underperforms live; an online endpoint and a batch job that score the same entity differently; a migration of feature computation (to a feature store, a new service, a rewritten job) after which outcomes moved with the model unchanged; adding the logging that makes skew measurable.

Do not use for: offline scores that are too good to believe, which is target leakage and belongs to `feature-leakage-audit`; inputs whose population is genuinely shifting over weeks, which is `model-drift-monitoring`; a cache returning stale responses, which is `application-caching`; finding the segments where a correct model is weak, which is `model-error-analysis`; a slow inference endpoint, which is `profiling`.

This skill pre-approves no shell command. It reads request logs, feature code and configuration, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Rule out the cheaper explanations

Skew replay costs a logging change and a few days of traffic. Spend ten minutes first on the explanations that cost nothing to check, because each one would make the replay show matching vectors and leave you with the same gap.

| Check | How | If it fails |
| --- | --- | --- |
| The served artefact is the evaluated one | Compare the hash of the model file and of every preprocessing artefact (scaler, encoder, vocabulary, feature list) loaded in serving against what the evaluation used | A deployment defect. Fix the release, stop here. |
| The offline number was honest | Was the evaluation split by time or entity, with every feature as of prediction time? | A random split or a suspiciously strong feature means the offline number was inflated. Go to `feature-leakage-audit`. |
| Live traffic is the evaluated population | Compare segment mix (new versus returning, country, channel, bot share) between the evaluation set and live requests | A coverage gap, not skew. The model is being asked about people it never saw. |
| The live outcome is the offline label | Same definition, same window, and the live labels have matured | Compare matured cohorts only; an immature cohort always looks worse. |

### 2. Log the served vector at the model boundary

Log, for a deterministic sample of requests, the exact array passed to the model's predict call, after every transformation, together with the request id, the entity keys, the request timestamp in UTC, the model version, the feature-set version and the prediction. Log the raw inputs before transformation too where you can, because that is what separates a skew in feature computation from a skew in encoding.

Sample by hashing the request id, so the same requests are chosen on every replica and the sample is reproducible. Cover peak and off-peak hours and at least one midnight in both UTC and the business's local time, since time-boundary bugs live there.

Do not reconstruct served values afterwards from the online store. The store has been overwritten since, and recomputing "what it would have served" runs the very code you are testing. If the logging does not exist, ship it and wait for the traffic. Served features are often personal data; give the log the retention and access rules of its source, and see `data-privacy` if that is undecided.

Read `references/replay-queries.md` for the log table layout.

### 3. Replay through the training pipeline at the request timestamp

Build an entity frame from the log: entity keys plus the request timestamp as the event time. Run it through the code that built the training set — the same job at the same version, not a rewrite of it for the purpose — with a point-in-time join, so each feature takes the latest value whose event time is at or before the request time. In Feast this is `get_historical_features` with an entity dataframe carrying an `event_timestamp` column; elsewhere it is an as-of join, written out in the reference file.

If the training pipeline cannot take an arbitrary timestamp because it only produces daily snapshots, write that down as the first candidate cause: training saw features as of snapshot time, serving sees them as of the request, and those are different values for every feature that changes within a day.

Score the replayed vectors with the same model artefact and keep both predictions per request.

### 4. Diff column by column and rank

Join served and replayed on request id. Report first how many logged requests the replay found at all: entities the training pipeline cannot see are a finding, not rows to drop.

Then, per feature:

- Numeric: mean absolute difference divided by the feature's standard deviation in the training set, so a column in pence does not outrank one in years; share of rows that differ beyond a tolerance; null mismatch rate (null on one side, a value on the other).
- Categorical: mismatch rate, and the five most frequent served-versus-replayed pairs.

Then at the prediction level: the mean absolute difference between the served and the replayed prediction. If it is negligible, the features may differ but the model does not care; the live gap is not skew, and you are back at step 1's table.

Where predictions do differ, run the swap test: for each high-ranked feature, replace the served column with the replayed one, re-score, and record what share of the prediction gap closes. Rank the final table by that share, because a large difference on a feature the model ignores is a curiosity and a small one on its strongest feature is the incident. Interactions mean the shares need not sum to one.

Read `references/replay-queries.md` for the as-of join, the diff and the swap test.

### 5. Name the cause of every feature near the top

Each cause leaves a signature in the diff, so read the pattern before reading code.

| Signature in the diff | Usual cause |
| --- | --- |
| Null mismatch high, or the served side holds 0, -1 or an empty string where replay is null | Null handling: serving fills a default, training imputes or leaves the gap for the model to learn |
| Aggregates and counts differ; the mismatch collapses when you replay at the request time minus the store's refresh interval | Stale join: the online store is materialised on a schedule, training joins at the exact instant |
| Hour, weekday and "today" features differ, concentrated on requests near midnight | Time zone or window boundary: one path uses local time, or one window includes the current day |
| Raw strings agree, encoded indices disagree; unknown-token rate higher on the served side | Categorical vocabulary: rebuilt at retrain but serving loads the old one, or normalisation differs |
| Served and replayed differ by a constant ratio (100, 1000, 60, 3600) | Units: percent versus fraction, pence versus pounds, milliseconds versus seconds |
| Many features wrong at once, values that look plausible but belong to a neighbouring column | Feature order: the serving vector is assembled in a different column order |

Read `references/skew-causes.md` for the full catalogue, including hashing, type coercion and library-version causes, with the confirming test for each.

### 6. Fix by sharing one code path

Choose, in this order:

1. One transformation, imported by both training and serving from the same package at the same pinned version, or computed once and read by both from a feature store. Two implementations of the same feature diverge again the next time either is edited.
2. Log-and-train: train on the features you logged at serving time, so training sees exactly what serving computed. This is rule 29 of Google's *Rules of Machine Learning*, and it removes the class of defect for every feature it covers.
3. When the defect is on the training side — the training join used a value that was not yet available at request time — fix training and retrain. That is leakage, not skew, and `feature-leakage-audit` owns the rest of it.

Do not patch serving to imitate training with a second copy of the logic, and do not retrain without changing either path. A retrain fixes nothing unless the training-side values changed.

### 7. Prove the fix and keep checking

Re-run steps 3 and 4 on traffic logged after the fix. The features you named should now sit inside tolerance and the prediction difference near zero. Then wait for the live outcome to mature and compare it with the offline number on the same period; skew fixed but a gap remaining means a second cause, usually from step 1.

Keep the replay as a scheduled job on a daily sample, with a per-feature threshold on mismatch rate and on scaled difference, routed to the model's owner; `alert-design` decides what pages. Distribution comparisons between training and serving statistics, such as TensorFlow Data Validation's skew checks, are a useful second layer but do not replace the per-request diff, for the reason in the opening.

## Output format

```markdown
## Verdict
[Skew confirmed or ruled out, and how much of the offline-to-live gap it explains.]

## Evidence
[Sample size and window, replay coverage, the ranked feature table with scaled difference, mismatch rate and swap-test share.]

## Causes
[One line per top feature: signature, cause, the code location on each path.]

## Fix
[Which shared path replaces which duplicate, whether a retrain is needed and why.]

## Guard
[The scheduled replay: sample, thresholds, owner.]
```

## Anti-patterns

**Retraining to fix skew.** The retrained model learns training-path features again and is served the same serving-path features. The gap survives; a week is gone.

**Histograms instead of a keyed diff.** Lagged or mis-joined values keep their distribution. Diff by request id.

**Reconstructing the served vector after the fact.** The online store has moved on, and the reconstruction runs the code under suspicion. Log at the boundary.

**Ranking by raw difference.** A column in milliseconds dominates every table. Scale by training standard deviation, then rank by prediction impact.

**A serving-side shim.** Translating units or filling nulls in serving to match training creates a third implementation. Delete one of the two instead.

## Reference files

- `references/replay-queries.md` — read at steps 2 to 4: the served-vector log table, a point-in-time join in SQL, the per-feature diff and the swap test in Python.
- `references/skew-causes.md` — read at step 5: every skew cause with its signature in the diff, the test that confirms it and the fix that removes it.
