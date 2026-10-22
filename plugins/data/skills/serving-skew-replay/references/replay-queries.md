# Replay queries

The served-vector log, the point-in-time replay, the per-feature diff and the swap test. SQL is written in a portable dialect; adjust the timestamp types and the sampling hash to your warehouse.

## Contents

- The served-vector log
- Building the entity frame
- The point-in-time join
- The per-feature diff
- The swap test
- Reading the result

## The served-vector log

One row per sampled request. Store the transformed vector as the model received it, and the raw inputs beside it.

```sql
CREATE TABLE served_features (
  request_id        VARCHAR   NOT NULL,
  entity_id         VARCHAR   NOT NULL,   -- one column per entity key the model uses
  request_ts_utc    TIMESTAMP NOT NULL,
  model_version     VARCHAR   NOT NULL,
  feature_set_ver   VARCHAR   NOT NULL,
  prediction        DOUBLE    NOT NULL,
  features_json     VARCHAR   NOT NULL,   -- transformed vector, keyed by feature name, in model order
  raw_inputs_json   VARCHAR,              -- inputs before transformation, where available
  PRIMARY KEY (request_id)
);
```

Key the vector by feature name rather than storing a bare array. A bare array cannot reveal a column-order defect, because the order is the thing in doubt.

Sample deterministically, so every replica picks the same requests: keep a request when a stable hash of its id, modulo 1000, falls below the sampling rate in tenths of a percent. Do not use a language's built-in string hash for this where it is salted per process (Python's `hash()` on strings is, unless `PYTHONHASHSEED` is fixed); use a named digest.

## Building the entity frame

```sql
SELECT request_id, entity_id, request_ts_utc AS event_timestamp
FROM served_features
WHERE request_ts_utc >= TIMESTAMP '2026-10-01 00:00:00'
  AND request_ts_utc <  TIMESTAMP '2026-10-08 00:00:00';
```

A week covers weekday effects and seven midnights. A few thousand rows is usually enough to rank features; take more if the features you suspect are rare (a flag set on one request in a thousand needs tens of thousands of rows to show).

## The point-in-time join

When the training pipeline reads feature tables with an event time, the replay is an as-of join: for each request, the latest feature row at or before the request time.

```sql
WITH candidates AS (
  SELECT
    e.request_id,
    f.*,
    ROW_NUMBER() OVER (
      PARTITION BY e.request_id
      ORDER BY f.event_ts DESC, f.load_ts DESC
    ) AS rn
  FROM entity_frame e
  LEFT JOIN customer_features f
    ON f.entity_id = e.entity_id
   AND f.event_ts <= e.event_timestamp
)
SELECT * FROM candidates WHERE rn = 1;
```

The `LEFT JOIN` keeps a request that has no feature row at all, with null features, so the coverage count in the diff sees it; an inner join would drop it before anyone counts. The second sort key breaks a tie between two rows with the same `event_ts` (a correction loaded later); without it `rn = 1` picks either at random and the replay differs between runs. Repeat per feature table, or let the feature store do it: Feast's `get_historical_features` takes the entity frame (with its `event_timestamp` column) and a feature list and performs this join. Many warehouses also offer a native as-of join; the semantics to confirm are "at or before" rather than "before", and what happens when no row exists (it must stay null, not fall back to the latest row overall).

Two variants are worth running once each, because they test causes directly:

- Replay at `event_timestamp - refresh_interval`, where the refresh interval is how often the online store is materialised. If the mismatch on aggregate features collapses, the online store is stale relative to training.
- Replay with the training pipeline's own snapshot time (end of the previous day, say). If that matches the served vector better than the exact time does, serving reads a snapshot and training should too, or serving should be made fresher.

## The per-feature diff

Load both sides into frames indexed by request id, with one column per feature.

```python
import numpy as np
import pandas as pd


def diff_report(
    served: pd.DataFrame, replayed: pd.DataFrame, train_std: dict, atol: float = 1e-6
) -> pd.DataFrame:
    common = served.index.intersection(replayed.index)
    print(f"replay coverage: {len(common)}/{len(served)} logged requests")
    s, r = served.loc[common], replayed.loc[common]
    rows = []
    for col in s.columns.intersection(r.columns):
        a, b = s[col], r[col]
        null_mismatch = float((a.isna() != b.isna()).mean())
        both = a.notna() & b.notna()
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            # float() so that boolean columns subtract; numpy refuses bool minus bool
            d = (a[both].astype(float) - b[both].astype(float)).abs()
            scale = train_std.get(col)
            unscaled = not scale  # missing or zero training std: flag it, do not rank on raw units
            rows.append(
                {
                    "feature": col,
                    "kind": "numeric",
                    "scaled_mad": float(d.mean() / scale) if len(d) and not unscaled else np.nan,
                    "unscaled": unscaled,
                    "mismatch_rate": float((d > atol).mean()) if len(d) else np.nan,
                    "null_mismatch": null_mismatch,
                }
            )
        else:
            rows.append(
                {
                    "feature": col,
                    "kind": "categorical",
                    "scaled_mad": np.nan,
                    "mismatch_rate": float((a[both].astype(str) != b[both].astype(str)).mean()),
                    "null_mismatch": null_mismatch,
                }
            )
    missing = set(s.columns) ^ set(r.columns)
    if missing:
        print(f"features present on one side only: {sorted(missing)}")
    return pd.DataFrame(rows)
```

Numeric features with `unscaled` true have no usable training std, so they carry no `scaled_mad`; read their differences by hand rather than ranking them. Sort numeric features by `scaled_mad` and categorical ones by `mismatch_rate`, and look at `null_mismatch` for both. For the top categorical features, list the most frequent pairs:

```python
pairs = (
    pd.DataFrame({"served": s[col].astype(str), "replayed": r[col].astype(str)})
    .query("served != replayed")
    .value_counts()
    .head(5)
)
```

A feature present on one side only is a finding in its own right: serving computes something training never saw, or the reverse.

## The swap test

The diff says where the vectors differ; the swap test says which differences move the prediction. It needs the model artefact and both vectors in model column order.

```python
def swap_impact(
    model, served_X: pd.DataFrame, replayed_X: pd.DataFrame, features: list
) -> pd.Series:
    served_p = model.predict_proba(served_X)[:, 1]
    replayed_p = model.predict_proba(replayed_X)[:, 1]
    gap = np.abs(served_p - replayed_p).mean()
    out = {}
    for f in features:
        X = served_X.copy()
        X[f] = replayed_X[f]
        p = model.predict_proba(X)[:, 1]
        out[f] = 1 - np.abs(p - replayed_p).mean() / gap if gap > 0 else 0.0
    return pd.Series(out).sort_values(ascending=False)
```

For a regressor use `predict` in place of `predict_proba(...)[:, 1]`. The value is the share of the mean prediction gap closed by correcting that one feature. Shares need not add to one, because features interact; when the top three together close most of the gap, swap them jointly to confirm.

## Reading the result

| Result | Meaning | Next |
| --- | --- | --- |
| Prediction gap near zero | Features may differ, but not in ways the model uses | Skew does not explain the live gap; return to the checks in step 1 |
| One or two features close most of the gap | A specific defect | Name the cause from the catalogue, fix that path |
| Many small differences, none dominant | A systematic difference: a library version, float precision, or a whole table read from a different snapshot | Compare environments and source snapshots before chasing features one by one |
| Replay coverage well below 100% | Training cannot see some live entities (new users, a new region, a source not yet loaded) | Find out who they are; that population is unscored territory regardless of skew |
