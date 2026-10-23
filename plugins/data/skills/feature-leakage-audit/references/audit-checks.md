# Audit checks

## Contents

- Single-feature screen
- Missingness by class
- Ablation loop
- Duplicates across the split
- Reading the results

Code assumes a pandas frame `train` and `valid` built by the honest split, a binary label column `y`, and scikit-learn. Adapt the scorer for regression.

## Single-feature screen

Score each feature alone, without training a model, so the screen is fast and has no fitting of its own to leak:

```python
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def solo_auc(train, valid, label="y"):
    rows = []
    for col in train.columns.drop(label):
        if pd.api.types.is_numeric_dtype(train[col]):
            score = valid[col].fillna(
                train[col].median()
            )  # train median: valid must not shape the score
        else:
            # category mean learned on train only, applied to valid
            means = train.groupby(col, dropna=False)[label].mean()
            score = valid[col].map(means).fillna(train[label].mean())
        if score.nunique() < 2:
            continue
        auc = roc_auc_score(valid[label], score)
        rows.append({"feature": col, "solo_auc": max(auc, 1 - auc)})
    return pd.DataFrame(rows).sort_values("solo_auc", ascending=False)
```

Compare the top of the list with the full model's validation AUC. A feature alone within a few points of the full model, or above what the current business process achieves, goes on the suspect list.

## Missingness by class

A field written only when the outcome happens is missing for nearly every negative and present for nearly every positive:

```python
missing = (
    train.drop(columns="y")
    .isna()
    .groupby(train["y"])
    .mean()
    .T.rename(columns={0: "missing_when_0", 1: "missing_when_1"})
)
missing["gap"] = (missing["missing_when_1"] - missing["missing_when_0"]).abs()
print(missing.sort_values("gap", ascending=False).head(20))
```

A large gap is not proof, but it is the cheapest signal of a field populated after the fact.

## Ablation loop

Retrain the real pipeline without each suspect, under the same split, and record the drop:

```python
from sklearn.base import clone
from sklearn.metrics import average_precision_score


def ablate(pipeline, train, valid, suspects, label="y"):
    def fit_score(cols):
        model = clone(pipeline).fit(train[cols], train[label])
        return average_precision_score(valid[label], model.predict_proba(valid[cols])[:, 1])

    all_cols = [c for c in train.columns if c != label]
    base = fit_score(all_cols)
    rows = [{"dropped": "(none)", "score": base, "drop": 0.0}]
    for s in suspects:
        score = fit_score([c for c in all_cols if c != s])
        rows.append({"dropped": s, "score": score, "drop": base - score})
    score = fit_score([c for c in all_cols if c not in suspects])
    rows.append({"dropped": "all suspects", "score": score, "drop": base - score})
    return pd.DataFrame(rows)
```

The pipeline must select columns by name rather than by position, so that removing one does not shift the rest. Dropping features one at a time understates the effect when two suspects carry the same leaked signal; the "all suspects" row catches that.

## Duplicates across the split

Exact duplicates on the feature vector:

```python
feature_cols = [c for c in train.columns if c != "y"]
train_keys = set(pd.util.hash_pandas_object(train[feature_cols], index=False))
valid_hash = pd.util.hash_pandas_object(valid[feature_cols], index=False)
dup_mask = valid_hash.isin(train_keys).to_numpy()
print(f"{dup_mask.mean():.1%} of validation rows match a training row exactly")
```

Entity-level duplicates need a normalised key: lower-cased and trimmed email, phone in one format, device identifier, address normalised the way the business does it. Count validation entities whose key appears in training.

Near-duplicates depend on the data type. For text, compare shingled token sets with MinHash or a simple Jaccard threshold on a sample. For images, compare perceptual hashes. For tabular rows, round continuous features and re-hash. Whatever the method, inspect a sample of matches by eye before removing them; a threshold that is too loose removes legitimate similar cases.

Re-measure with all duplicates removed from validation and report both numbers.

## Reading the results

| Observation | Likely cause | Action |
| --- | --- | --- |
| One feature's solo AUC near the full model, available after prediction time | Leak | Remove, rebuild point-in-time if possible, re-measure |
| One feature's solo AUC high, genuinely available in time | Strong legitimate signal | Keep; document why so the next audit does not repeat it |
| Score drops sharply under a group split | Entity memorisation | Use the group split as the reported number |
| Score drops once preprocessing moves inside folds | Fitted transformation saw validation data | Keep the pipeline version |
| Many exact matches across split | Duplicate ingestion or repeated entities | Deduplicate before splitting, re-measure |
| Missingness gap large for a field | Field written after the outcome | Check its write time; treat as a suspect |
