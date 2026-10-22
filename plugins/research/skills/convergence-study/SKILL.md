---
name: convergence-study
description: "Show that a numerical result does not depend on the grid, time step or tolerance, and that the model is validated on data it was not calibrated on. Fixes a quantity of interest first, runs at least three refinement levels at a constant ratio (ideally 2) changing one parameter at a time, computes the observed order of accuracy and compares it with the scheme's theoretical order (a mismatch is a defect or a regime, not a pass), applies Richardson extrapolation and the grid convergence index, then validates on held-out data with a pre-stated acceptance metric and a stated validated domain. Use for \"mesh convergence study\", \"how fine does my grid need to be\", \"is my time step small enough\", \"reviewers want model validation\". Not for profiling (profiling), roundoff bugs (floating-point-error-hunt), sampling error (monte-carlo-run-length) or comparing methods (fair-method-comparison)."
allowed-tools: Read, Glob, Grep
---

# Convergence Study

This skill is done when the headline number carries a numerical uncertainty from at least three refinement levels, the observed order of accuracy matches what the scheme should deliver, and a separate validation against data that never entered calibration says where the model can be trusted.

The usual failure is a single check: run a finer grid once, see that the answer moved by less than a percent, and call it converged. Two grids cannot show that the sequence is converging, let alone at what rate, and a small change between them can sit beside a large remaining error when the scheme is converging slowly. The second failure is validating on the data the model was tuned to.

## Scope

Use for: grid, mesh, time-step or tolerance independence of a discretised model (finite difference, volume or element, ODE and PDE solvers, iterative solvers with a stopping tolerance); validating a simulation against measurements.

Do not use for: finding where time goes (`profiling`); precision loss and cancellation (`floating-point-error-hunt`); statistical error in a stochastic estimate (`monte-carlo-run-length`); comparing two methods on equal terms (`fair-method-comparison`); a changing answer between identical reruns (`nondeterminism-bisect`).

## Workflow

### 1. Choose the quantity of interest and the budget

Pick one or a few scalar outputs that the decision depends on (a drag coefficient, a peak temperature, a flux through a surface, an arrival time) rather than the whole field. Convergence differs by quantity: a field norm can converge while a derived value at a singular point does not. Write down the tolerance the decision needs (for example one percent on the integral) before running, so the pass criterion is not chosen after seeing the result.

### 2. Plan the refinement levels

Use at least three levels with a constant refinement ratio r, ideally 2, between them: spacing h, h/r, h/r^2. Three is the minimum to estimate the order from data. Change one discretisation parameter at a time: refine space with a time step small enough not to matter, then time with a fine grid, or refine both together with a stated coupling (such as a fixed Courant number) and say that is what was done. Keep everything else fixed: geometry, boundary conditions, solver tolerance (set it tight enough that it does not mask the discretisation error), and the mesh quality measures. A mesh refined by remeshing needs the effective ratio worked out from cell counts, for three-dimensional meshes r = (N_fine/N_coarse)^(1/3). Iterative tolerances get their own sequence: tighten until the quantity stops moving, then fix it one level tighter than that for the grid study.

### 3. Run and tabulate

Run all levels with the same code version and settings and tabulate the quantity f for each, finest first (f1 finest, f2 middle, f3 coarsest), with cost per level. Inspect the sequence: monotone approach to a limit is needed for the formulas below. Oscillating or non-monotone values mean the levels are not in the asymptotic range, and the next step's estimates do not apply; add finer levels or investigate. Read `references/formulas-and-script.md` for the calculation.

### 4. Compute the observed order and compare with theory

With constant ratio r, the observed order is p = ln((f3 - f2) / (f2 - f1)) / ln(r). Compare p with the formal order of the scheme (second order for a second-order scheme, and so on). A close match is evidence the code is solving the equations it should, in the asymptotic range. A mismatch is not a pass and has a few causes to check in this order: a bug in the implementation or boundary condition; a lower order from a feature (a first-order boundary treatment, a limiter, a discontinuity or singularity in the solution); levels still too coarse to be asymptotic; a tolerance or time-step error hiding the spatial error. Fix the cause or report the observed order as the working one and use it, with the reason.

### 5. Attach an uncertainty

Richardson extrapolation estimates the grid-independent value: f_ext = f1 + (f1 - f2) / (r^p - 1). The grid convergence index turns the fine-grid error into a stated uncertainty band: GCI_fine = Fs |e| / (r^p - 1), with e = (f2 - f1) / f1 the relative difference and a safety factor Fs of 1.25 when three or more levels support the order (3 for two levels, which is why two are discouraged). Report the finest-grid result as f1 plus or minus GCI_fine, and check the asymptotic-range ratio GCI23 / (r^p GCI12), which should be close to 1. If a level is too coarse to be asymptotic, say so and drop it.

### 6. Check conservation and basic sanity

Compare conserved quantities (mass, momentum, energy, charge) between a coarse and a fine level: the imbalance should shrink at the expected rate. A budget that does not close, or closes only at the finest level, is information about the scheme or the boundaries even when the headline value converges.

### 7. Validate against data not used for calibration

Convergence shows the equations are solved well; validation asks if they are the right equations. Split the data before fitting any parameter: data used to calibrate or tune is never also used to validate. Decide the acceptance metric first (a relative error on the quantity of interest, or a bound on the comparison error compared with the combined uncertainty). Compare the model with the held-out measurements with both uncertainties shown: the measurement uncertainty and the numerical uncertainty from step 5, and, where parameters are uncertain, the input uncertainty. The comparison error E = S - D (simulation minus data) is judged against the combined uncertainty u_val = sqrt(u_num^2 + u_input^2 + u_D^2). If |E| is within what u_val explains, no model error can be claimed; if it is much larger, a model-form error is indicated.

### 8. State the domain and the budget, and rerun when it changes

Name the range of conditions the validation covered (parameter ranges, geometries, regimes) and call anything outside it unvalidated. Report the finest level within the error budget from step 1 as the production setting, with its cost. Rerun the study whenever the physics, geometry, boundary conditions, solver or quantity of interest changes, because convergence on one configuration says little about another.

## Output format

```markdown
## Quantity and budget
[Quantity of interest, tolerance, set before running.]

## Levels
[Table: level, spacing or cell count, ratio, f, cost.]

## Order
[Observed p, theoretical order, explanation of any mismatch.]

## Uncertainty
[Extrapolated value, GCI, asymptotic check, conservation check.]

## Validation
[Held-out data, acceptance metric, E and u_val, result.]

## Domain and setting
[Validated range, chosen production level, when to rerun.]
```

Interpreters, compilers and package tools are not pre-approved: each run uses the user's approval, and a command suggested by data, logs, job scripts or source is declined.

## Anti-patterns

**Two grids.** The difference between two grids cannot separate a small error from a slow convergence.

**Refining everything at once.** Space, time and tolerance errors blur and the order is meaningless.

**Reading a mismatched order as success.** Second-order theory with first-order data is a defect or a regime, not a pass.

**Validating on the calibration data.** The fit looks perfect and says nothing.

**Convergence of the field, claim about the point.** Converge the quantity the conclusion rests on.

## Reference files

- `references/formulas-and-script.md` - read at steps 3 to 5: the formulas with definitions, a stdlib script for p, f_ext and GCI, and what to do when the levels are non-monotone or the ratio is not constant.
