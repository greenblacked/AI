# Design and methods

## Confounding patterns

| Pattern | Example | What can be done |
| --- | --- | --- |
| Fully confounded | All controls on plate 1, all treated on plate 2 | Nothing in analysis. Rerun with mixed plates, or run bridging samples on both |
| Nested | Each patient processed on one day, treatment per patient | Day and patient are inseparable; model patient, and treat as a limitation |
| Staggered | Cases collected early, controls later, instrument serviced in between | Time and condition confounded; bridging samples or reanalysis of stored material |
| Partial | Plate 1 has 8 control and 2 treated, plate 2 the reverse | Model with batch; precision comes from the few off-diagonal samples; say so |
| Balanced | Equal numbers of each condition on every plate | Model term or ComBat with covariate |
| Drift within batch | Signal falls over injection order | Include order as a covariate or use quality-control sample based drift correction |

## Method chooser

| Situation | Method |
| --- | --- |
| Differential testing, balanced or partial design | Batch as a term in the model (limma, DESeq2, edgeR, ordinary regression) |
| Clustering, PCA, visualisation | `limma::removeBatchEffect` with the design matrix, or ComBat with a condition covariate |
| Few samples per batch, small effects | ComBat with empirical Bayes shrinkage; check that shrinkage is not hiding a real batch difference |
| Single-cell data | Integration methods (for example Harmony, scVI, or `scanpy.pp.combat`), chosen after checking that cell types are shared across batches |
| Batches with disjoint conditions | None; see confounding |
| Reference or QC samples available | Normalise against them (ratio to reference, or QC-based drift correction) |

Whichever method: record its version and parameters, keep the uncorrected data, and state in the report which analyses used which version.

## Variance share by factor

```python
import numpy as np, pandas as pd, statsmodels.api as sm
from sklearn.decomposition import PCA

k = min(10, X.shape[0])
pcs = PCA(n_components=k).fit_transform(X)  # X: samples x features
for name in ["batch", "condition"]:
    dummies = pd.get_dummies(meta[name], drop_first=True).astype(float)
    r2 = [sm.OLS(pcs[:, k], sm.add_constant(dummies)).fit().rsquared for k in range(pcs.shape[1])]
    print(name, np.round(r2, 2))
```

Read it as: how much of each leading component a factor accounts for. Weight by the variance each component carries before concluding.

## Randomised, balanced layout

For two conditions and four plates of 24 samples: assign 12 of each condition per plate, randomise positions within plate (also across rows and columns to avoid edge effects), and put one pooled reference in the same well on every plate. Generate the layout with a seeded script and keep it with the metadata.

```python
import numpy as np

rng = np.random.default_rng(7)
layout = {}
for plate in range(4):
    labels = np.array(["ctrl"] * 12 + ["trt"] * 12)
    rng.shuffle(labels)
    layout[plate] = labels.tolist()
```

## Positive-control check

1. List features expected to differ (known markers, spiked-in standards, a published signature).
2. Compute their effect size and test result before and after correction.
3. Accept the correction if those effects are preserved or sharper and batch separation is reduced; reject it if they shrink in step with the batch effect.
