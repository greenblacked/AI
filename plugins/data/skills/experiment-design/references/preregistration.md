# Pre-registration template and review checklist

## The template

Fill every field. A field left as "TBD" at launch is a decision the data will make.

```markdown
# Experiment: [name]   Plan frozen: [date]   Owner: [name]

## Decision
- If treatment wins: [action]
- If treatment loses: [action]
- If no detectable difference: [action]
- Practical threshold: [smallest effect that changes the action, absolute and relative]

## Hypothesis
[Change] will move [primary metric] by at least [threshold] because [mechanism].

## Population and trigger
- Eligible: [who can be assigned]
- Trigger: [event that marks a unit as exposed; logged in both arms at the same point]
- Exclusions: [internal users, bots by the platform's existing rule, regions]

## Randomisation
- Unit: [user id / device id / account]; analysis unit: [same]
- Arms and split: [control 50 / treatment 50]
- Salt or seed: [value], so assignment is independent of other running tests
- Interference check: [why units do not share a constrained resource]

## Metrics
- Primary: [name, exact definition, unit, aggregation, ratio or mean]
- Guardrails: [name, direction, non-inferiority margin] (one line each)
- Sample ratio check: chi-square against the design split, flagged at p < 0.001
- Debug metrics (not used for the verdict): [list]

## Sizing
- Baseline: mean [x], sd [s] (or delta-method sd for a ratio), from [window]
- MDE: [delta] absolute, [pct] relative; alpha [0.05] two-sided; power [0.8]
- Variance reduction: [CUPED on (covariate) over (pre-period) / none]; rho [value]
- Capping: [metric capped at (percentile) / none]
- Units per arm: [n]; distinct eligible units per week from history: [table]
- Duration: [whole weeks]; start [date]; readout [date]

## Stopping
- Rule: [fixed horizon, read once on readout date / sequential method and its spending]
- Early stop for harm: [guardrail, threshold, who decides]

## Analysis
- Estimator: [difference in means / delta method / CUPED-adjusted]
- Segments to report, all exploratory: [pre-treatment attributes only]
- Correction for segments: [Benjamini-Hochberg at q = 0.05 / Holm]
- Novelty check: effect by week since first exposure

## Changes after launch
[date, change, reason — written before anyone reads results]
```

## Review checklist

Use this to review someone else's plan before launch. Each "no" is a finding.

| Check | Why it matters |
| --- | --- |
| The three decision lines lead to different actions | Otherwise the test cannot change anything |
| Exactly one primary metric | Several primaries without correction inflate false wins |
| Every guardrail has a numeric margin | "Must not hurt latency" cannot be evaluated |
| Randomisation unit equals analysis unit, or the ratio is analysed by delta method | Otherwise standard errors are too small |
| No shared resource between arms | Interference biases a user split; see switchback designs |
| Trigger logged in control at the same point as treatment | Otherwise the arms are compared on different populations |
| Baseline variance measured on the triggered population | Whole-population variance misstates the size needed |
| MDE equals the practical threshold, not the traffic-limited minimum | A test too small for the threshold cannot support a decision |
| Duration in whole weeks, from cumulative distinct units | Day-of-week mix and returning users are otherwise mis-weighted |
| CUPED, capping and segments decided now | A choice made after the results is a forking path |
| Stopping rule written | Repeated looks at a fixed-horizon test inflate false positives |
| A/A run if the platform, assignment or metric code is new | A broken platform corrupts every test that follows |
