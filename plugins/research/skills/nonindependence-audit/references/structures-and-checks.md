# Structures and checks

## Which level is the unit

| Design | Unit for the treatment comparison | Rows below it are |
| --- | --- | --- |
| Cells from animals, treatment per animal | Animal | Subsamples |
| Several animals per litter, treatment per litter | Litter | Subsamples |
| Treatment per animal, litters in both arms | Animal, with litter as a grouping | Cells within animal |
| Repeated visits per patient, treatment per patient | Patient | Visits |
| Patients crossed over between treatments | Patient (paired within) | Periods |
| Pupils in classes, intervention per class | Class | Pupils |
| Many images per specimen, pixels per image | Specimen | Images, pixels |
| Same site measured weekly | Site | Weeks (also autocorrelated) |

Rule: the unit is the thing to which the treatment was assigned. Grouping above it can be modelled; grouping below it is what gets averaged over.

## Model formulas

Python (statsmodels):

```python
import statsmodels.formula.api as smf

m = smf.mixedlm("y ~ treatment", df, groups=df["animal"]).fit(reml=True)
# random slope for time within animal
m = smf.mixedlm("y ~ treatment * time", df, groups=df["animal"], re_formula="~time").fit()
# cluster-robust OLS
ols = smf.ols("y ~ treatment", df).fit(cov_type="cluster", cov_kwds={"groups": df["animal"]})
```

R (lme4):

```r
lmer(y ~ treatment + (1 | animal), data = d)
lmer(y ~ treatment + (1 | litter/animal), data = d)   # animals nested in litters
glmer(count ~ treatment + (1 | animal), family = poisson, data = d)
```

Singular fit or a variance estimated at exactly zero is a sign of too few groups or too little within-group replication; simplify the random part and report it.

## Intraclass correlation and design effect

ICC = var_between / (var_between + var_within). Design effect = 1 + (m - 1) x ICC, with m the mean rows per unit (use the mean for balanced data and say so for unbalanced). Effective n = rows / design effect. Example: 40 rows per patient and ICC 0.5 gives a design effect near 20.5, so 4,000 rows from 100 patients carry the information of about 195 independent rows.

## Permutation at the unit level

Aggregate or keep rows, but shuffle the treatment label across units: assign each unit's label to a random unit, recompute the statistic on all rows, repeat several thousand times, compare the observed statistic to that distribution. For paired designs, flip the sign of within-unit differences instead.

## Few clusters

- Fewer than about five or six units per arm: report the unit-level aggregate and a unit-level permutation test; do not report a mixed-model p-value as if the variance were known.
- Between that and about thirty to forty clusters, cluster-robust errors are still anticonservative; small-sample corrections and t-reference distributions with cluster-count degrees of freedom are the usual remedy, and statistical advice is worth getting.
- Unequal cluster sizes make cluster-robust inference worse; say so.

## Time and space checks

- Time: autocorrelation function of the residuals within each unit; a Durbin-Watson statistic near 2 is no first-order autocorrelation.
- Space: Moran's I on residuals using a stated neighbour definition; a significant value means the rows are not independent after the model.
- If either is present, add the structure (autoregressive error, spatial term) or aggregate to a scale at which neighbours no longer matter, and report the choice.
