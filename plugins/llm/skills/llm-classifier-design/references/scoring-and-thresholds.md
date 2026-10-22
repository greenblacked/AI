# Scoring and thresholds

## Contents

- Per-class scoring script
- TF-IDF baseline
- Calibration check
- Choosing the abstain threshold

## Per-class scoring script

Input: a JSONL file with `gold`, `pred` and optionally `score` per line.

```python
import json, sys
from collections import Counter, defaultdict

rows = [json.loads(l) for l in open(sys.argv[1])]
classes = sorted({r["gold"] for r in rows} | {r["pred"] for r in rows})
cm = defaultdict(Counter)
for r in rows:
    cm[r["gold"]][r["pred"]] += 1

print("class", "support", "precision", "recall", "f1", sep="\t")
for c in classes:
    tp = cm[c][c]
    support = sum(cm[c].values())
    predicted = sum(cm[g][c] for g in classes)
    p = tp / predicted if predicted else 0.0
    r = tp / support if support else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    print(c, support, f"{p:.3f}", f"{r:.3f}", f"{f:.3f}", sep="\t")

print("\nconfusion (rows gold, columns predicted)")
print("", *classes, sep="\t")
for g in classes:
    print(g, *[cm[g][p] for p in classes], sep="\t")
```

Report the support beside each metric; a precision of 1.0 on four items is not evidence.

## TF-IDF baseline

With scikit-learn available in the project's environment (do not add it to a validator or a shipped tool):

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
    LogisticRegression(max_iter=1000, class_weight="balanced"),
)
model.fit(train_texts, train_labels)
pred = model.predict(holdout_texts)
```

Score `pred` with the same script. A rule baseline is a list of keyword patterns per class in priority order; it often wins on classes defined by a phrase. Record cost per item for each contender: the baseline is near zero.

## Calibration check

Bin holdout items by score (for example into ten equal-count bins) and compute the share correct per bin. A usable score rises with the bin. A flat or inverted curve means the score cannot support a threshold; try another derivation (more samples for self-consistency, or logprobs where available).

## Choosing the abstain threshold

Sort holdout items by score descending. For each candidate threshold t, the automated set is items with score at least t; compute its precision and its coverage (share of all items it covers). Take the lowest t whose precision meets the downstream requirement, and report coverage there. Compute per class when classes have different costs. Keep a margin: the holdout estimate carries an interval, so pick a t slightly more conservative than the first point that qualifies, and recheck on the monthly production sample.

```python
def curve(rows):
    # One point per distinct score, emitted after the last item at that score:
    # a threshold t admits every item with score >= t, so a point inside a
    # run of tied scores describes a set no threshold can produce.
    if not rows:
        raise ValueError("no holdout rows")
    rows = sorted(rows, key=lambda r: -r["score"])
    correct = 0
    for i, r in enumerate(rows, 1):
        correct += r["gold"] == r["pred"]
        if i == len(rows) or rows[i]["score"] != r["score"]:
            yield r["score"], correct / i, i / len(rows)
```

Self-consistency over N samples gives at most N distinct scores, so expect few points and ties; a target that falls between two points is met only by the stricter one.
