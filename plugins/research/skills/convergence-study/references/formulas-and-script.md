# Formulas and script

Contents: definitions, script, non-monotone sequences, non-constant ratio, report table.

## Definitions

Levels are numbered finest first: f1 (spacing h1), f2 (h2 = r h1), f3 (h3 = r^2 h1).

| Quantity | Formula |
| --- | --- |
| Observed order, constant r | p = ln((f3 - f2) / (f2 - f1)) / ln(r) |
| Extrapolated value | f_ext = f1 + (f1 - f2) / (r^p - 1) |
| Relative difference | e12 = (f2 - f1) / f1 |
| Grid convergence index, fine | GCI12 = Fs \|e12\| / (r^p - 1) |
| Asymptotic check | GCI23 / (r^p GCI12), close to 1 |
| Comparison error | E = S - D |
| Validation uncertainty | u_val = sqrt(u_num^2 + u_input^2 + u_D^2) |

Fs is 1.25 for three or more levels and 3 for two. Use the formal order in place of p only for a stated reason, and then report both.

## Script

```python
import math


def convergence(f1, f2, f3, r, fs=1.25):
    d32, d21 = f3 - f2, f2 - f1
    if d21 == 0 or d32 / d21 <= 0:
        raise ValueError("non-monotone or flat sequence: order is undefined")
    if d32 / d21 < 1:
        raise ValueError(
            "divergence: differences grow as the grid refines, observed order is negative"
        )
    p = math.log(d32 / d21) / math.log(r)
    if abs(p) < 1e-12:
        raise ValueError("observed order is zero: differences do not shrink with refinement")
    f_ext = f1 + (f1 - f2) / (r**p - 1)
    # relative GCI needs a nonzero value; otherwise report it in absolute units
    n12 = abs(f2 - f1) / (abs(f1) if f1 != 0 else 1.0)
    n23 = abs(f3 - f2) / (abs(f2) if f2 != 0 else 1.0)
    gci12 = fs * n12 / (r**p - 1)
    gci23 = fs * n23 / (r**p - 1)
    asym = gci23 / (r**p * gci12)
    return {"p": p, "f_ext": f_ext, "gci12": gci12, "gci23": gci23, "asym": asym}


print(convergence(f1=0.9712, f2=0.9701, f3=0.9657, r=2.0))
```

A ratio d32 / d21 less than or equal to zero means the sequence changes direction; the formula does not apply. A ratio below 1 gives a negative p: the differences are growing as the grid refines, which is divergence.

## Non-monotone sequences

Oscillating values across levels usually mean one of: levels not asymptotic (too coarse), a mesh whose quality changes between levels (so refinement is not systematic), a tolerance too loose, or a feature such as a shock or a limiter switching. Add a finer level, regenerate meshes with a controlled ratio, tighten the tolerance, and repeat. If the sequence stays non-monotone, report the spread across the finest levels as the numerical uncertainty and say the order could not be determined.

## Non-constant ratio

With unequal ratios, p solves a nonlinear equation (the standard procedure iterates on it). Rather than do that by hand, refine with a constant ratio. If the meshes are given, compute the representative spacing h = (V / N)^(1/3) in three dimensions and use the ratios from that, noting the mesh is not geometrically similar.

## Time-step and tolerance studies

The same method holds for a time step (h is dt) and for an iterative tolerance (a sequence of tightening tolerances, where convergence is judged by the quantity of interest stopping to change relative to the budget, not by an order). For an adaptive solver, vary the controlling tolerance, not the step.

## Report table

```markdown
| Level | h or N | f | f - f_ext | Cost (core-hours) |
| --- | --- | --- | --- | --- |
```

Finish with the extrapolated value, GCI, observed and formal order, and the chosen production level.
