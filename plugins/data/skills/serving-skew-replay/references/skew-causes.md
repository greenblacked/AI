# Skew causes

Each cause of train/serve skew leaves a recognisable pattern in the per-feature diff. Match the pattern, run the confirming test, then apply the fix that removes the second code path rather than the one that reconciles two.

## Contents

- The five common causes
- Less common causes
- Fixes that look right and are not

## The five common causes

| Cause | Signature in the diff | Confirming test | Fix |
| --- | --- | --- | --- |
| Null handling | High `null_mismatch`; the served side clusters on one sentinel (0, -1, empty string, "unknown") where replay is null, or the reverse | Count served rows equal to the sentinel against replayed nulls for the same requests | One imputation function used by both paths; represent "missing" explicitly (a null or an indicator column), not as a value that also occurs naturally |
| Stale join | Counts, sums and recency features differ, served values lag replayed ones; mismatch rate higher for active entities | Replay at the request time minus the online store's refresh interval; the mismatch should collapse | Either make serving fresher, or train on features as of the same lag serving sees, so the model learns what it will actually be given |
| Time zone or window boundary | Hour, weekday, "today" and rolling-window features differ, concentrated in requests within a few hours of midnight; offset equals the zone difference | Bucket mismatch rate by request hour in UTC; a spike at the local-midnight hour confirms it | Timestamps in UTC throughout; window definitions (inclusive or exclusive of the current day) in shared code |
| Categorical vocabulary | Raw strings agree, encoded values disagree; higher unknown-token rate in serving; an index offset of a constant for every category after a given one | Compare the vocabulary file loaded by serving with the one saved beside the model artefact | Version the vocabulary with the model artefact and load it from there; put case, whitespace and accent normalisation in shared code |
| Units | Served and replayed differ by a constant ratio: 100, 1000, 60, 3600, or a currency rate | Plot served against replayed; a straight line through the origin with slope other than one | Units in the schema or feature name; one conversion at ingestion, never at use |

## Less common causes

| Cause | Signature | Confirming test |
| --- | --- | --- |
| Feature order | Many features wrong at once, each holding a plausible value that belongs to another column | Compare the feature list order in the serving code with the training artefact's; the swapped pair has each other's distributions |
| Salted hashing | Hashed or bucketed features disagree on most rows while raw values agree | Check whether either path uses a per-process salted hash (Python's built-in `hash()` on strings without a fixed `PYTHONHASHSEED`); hash the same string in two processes |
| Type coercion | Integer identifiers matched as strings on one side ("0042" against 42), booleans as strings, floats truncated | Compare dtypes per column on both sides |
| Library version | Text features, tokenisation, date parsing or rounding differ slightly but widely | Compare the package versions in the serving image against the training environment's lockfile |
| Float precision | Tiny differences on every row, well under any meaningful scale | Differences of the order of float32 epsilon relative to the value; usually harmless, raise the tolerance and move on |
| Source snapshot | Every feature from one table differs together | Training read a warehouse copy, serving reads the operational database or a cache with different deduplication or late-data rules |
| Aggregation window semantics | A rolling count off by roughly one event, or one day's worth | "Last 7 days" counted as seven calendar days including today on one side and seven times 24 hours on the other |
| Default for an unseen entity | New entities get all-zero features in serving, missing rows in training | Replay coverage below 100% concentrated in recently created entities |

## Fixes that look right and are not

| Tempting fix | Why it fails |
| --- | --- |
| Retrain on fresh data | Both paths are unchanged, so the retrained model meets the same served values it was not trained on |
| Add a correction in serving (multiply by 100, map 0 to null) | Creates a third implementation that drifts when either of the other two changes |
| Drop the skewed feature | Removes the symptom and some of the model's signal; acceptable only as a stop-gap while the shared path is built, and only after measuring the offline cost |
| Compare training and serving histograms going forward | Catches population shift, misses per-row defects such as stale joins and order swaps |
| Fix the feature in training only | Correct when training was leaking future information, wrong otherwise: serving still computes the old value and the newly trained model now disagrees with it |
