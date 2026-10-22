# Readout template and reviewing someone else's

## The document

Lead with the verdict. A reader who stops after the first line should leave with the right decision and the right uncertainty.

```markdown
# Readout: [experiment]   Ran: [start] to [end], [n] whole weeks   Plan: [link, frozen date]

**Verdict: [ship / hold / rerun / do not ship].** Treatment changed [primary metric] by
[+x%] (95% CI [a%] to [b%]) against a ship threshold of [t%]; guardrails [shown within margin / X not shown within margin / breach in X].

## Trust checks
- Sample ratio: [n_control] / [n_treatment] against [designed split]; chi-square p = [p] (gate: 0.001)
- Daily ratio: [steady / break on date, cause]
- Mid-run changes: [none / list]
- Pre-period balance on primary metric: [difference and interval]
- Units seen in both arms: [count, share]

## Primary metric (pre-registered)
| Arm | Units | Mean | Difference | 95% CI | Relative | 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
Estimator: [difference in means / delta method / CUPED with covariate and window, as planned]

## Guardrails
| Guardrail | Margin | Estimate | 95% CI | Within margin |
| --- | --- | --- | --- | --- |

## Novelty and primacy
Effect by week since first exposure: [w1, w2, w3 with intervals]. [Stable / fading toward x / growing].

## Exploratory segments (Benjamini-Hochberg, q = 0.05, over [k] tests)
| Segment | Units | Effect | 95% CI | Survives correction |
| --- | --- | --- | --- | --- |
Heterogeneity: [test of difference between segments, not each segment against zero].

## Not used for the verdict
[Debug metrics and anything outside the plan, labelled as hypotheses.]

## Next
[What to test next, or the holdback to measure the realised effect.]
```

## Wording

| Write | Not |
| --- | --- |
| "+1.8% (95% CI +0.6% to +3.0%)" | "significant at p < 0.05" |
| "the test could not distinguish an effect of +1% from none" | "no effect" |
| "guardrail not shown within its margin" | "no impact on latency" |
| "exploratory: Android +4.1% (CI +1.0% to +7.2%) after correction" | "it works on Android" |
| "effect fading from 6% in week 1 to 2% in week 3" | "+4% overall" when the trend is falling |

## Questions to ask of someone else's readout

1. Is the primary metric the one in the plan, defined the same way?
2. Did the sample ratio check run on randomisation units against the designed split, before any effect?
3. Was the analysis at the randomisation unit, or on events or sessions with a naive standard error?
4. Was the estimator the planned one, or was CUPED, capping or outlier removal added after?
5. Did the test run its planned whole weeks, or stop at a convenient moment?
6. Are segments defined before exposure, corrected, and labelled exploratory?
7. Does the verdict follow from the interval against the threshold, or from the p-value alone?
8. Is the effect much larger than past tests on similar changes? If so, what was re-checked?
