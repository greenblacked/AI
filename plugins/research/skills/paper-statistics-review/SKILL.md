---
name: paper-statistics-review
description: "Review the statistics of a paper, preprint, thesis chapter or internal result before relying on it, in a fixed order: estimand and primary outcome and whether prespecified; independent unit versus unit analysed; tests actually run, including forks in the garden; recomputation from the text (p from statistic and df, means and SDs against n with a GRIM-style integer check, CI against p); what the error bars are; exclusions, missing data and denominators; effect size with an interval rather than bare significance; power and any 'no difference' claim. Output a ranked list: invalidates the claim, weakens it, cosmetic. Use for \"can I trust the statistics in this result\", \"review the stats in this manuscript\", \"are these p-values right\" or \"referee report on the analysis\". Not for code review (code-review), reading a paper for its argument and contribution (paper-reading) or surveying literature (literature-scan)."
allowed-tools: Read, Glob, Grep
---

# Paper Statistics Review

This skill is done when each claim that matters has been traced to the analysis that supports it, every number that can be recomputed from the text has been, and the problems are ranked by whether they invalidate the conclusion, weaken it or only need tidying.

The usual failure is reviewing the prose. A methods section says "t-tests were used" and a results section gives p-values, and the reviewer nods. The problems sit in the gaps: the unit analysed is not the unit sampled, twelve comparisons were run and two reported, the denominator in the figure differs from the one in the abstract, a mean cannot be produced by the stated sample size. Reading in a fixed order, and recomputing, finds what reading for sense does not.

## Scope

Use for: a manuscript, preprint, thesis chapter, report or internal write-up whose conclusion rests on a statistical analysis, when someone needs to decide how far to trust it or must write a referee report.

Do not use for: reviewing analysis code (`code-review`); reading a paper for its argument and contribution (`paper-reading`); finding and summarising the literature on a topic (`literature-scan`).

## Workflow

Take the steps in order. Each one can change what the next means, and a problem found at step 2 usually makes step 4 moot. Record each finding with its location (section, table, figure, page) and a quotation or number, so the author can find it.

### 1. Estimand, primary outcome, prespecification

Write down, in one sentence each, what the paper claims, the quantity that would support it (the estimand: a difference in means, a hazard ratio, a correlation, in which population), and the single primary outcome. Then find out whether these were fixed before the data were seen: a preregistration, a protocol, a trial registry entry, a statistical analysis plan. If the outcome in the paper differs from the registered one, that is a finding. If nothing was prespecified, every result is exploratory and should be worded so; say that, and do not require a confirmatory standard of an exploratory study.

### 2. The independent unit

Identify what was independently sampled or assigned (participants, litters, plots, hospitals, sessions, papers) and what was analysed (cells, images, trials, time points, pooled samples). When they differ, the nominal n and every p-value are wrong: repeated measures, cells from the same animal, students in classrooms and sequential time points are correlated, and treating them as independent shrinks the standard error. The correction (a mixed-effects model, cluster-robust errors, averaging to the unit first) belongs in the author's revision; the reviewer's job is to show the mismatch and estimate its direction. For the check, read `references/recompute-checks.md`, the section on effective sample size.

### 3. Count the tests

List every test, model and comparison named anywhere, including supplements. Count outcomes, subgroups, time points, models and thresholds tried. The number that matters is the number the authors could have reported, since the choice of which to show after seeing results inflates false positives. A subgroup effect with no significant interaction test is not evidence of a different effect. Check for a correction (Bonferroni, Holm, false-discovery rate) and whether it covers the whole family or only the part reported.

### 4. Recompute from the text

Do the arithmetic that the paper permits (`references/recompute-checks.md` has the formulas and a script):

- p from the reported test statistic and degrees of freedom; flag a mismatch beyond rounding.
- Means and SDs against n. For integer-valued data (counts, Likert items, scores), a reported mean must be a multiple of 1/n to rounding (the GRIM test); a mean of 3.47 from 12 integer responses cannot occur.
- Confidence interval against p: an interval that excludes the null must go with p below its level, and the reverse.
- Degrees of freedom against the stated n and design; a paired test on n = 20 has 19 df.
- Percentages against counts.

An inconsistency is not proof of misconduct; it is a question for the authors, worded as one.

### 5. What are the error bars

Find each figure's legend: SD (spread of the data), SE (precision of the mean, smaller by the square root of n) or a confidence interval. Bars of unstated type cannot be interpreted. Overlapping SE bars do not mean no difference, and non-overlapping 95% intervals are a stricter standard than p below 0.05. Check that n per group is given and that individual points are shown for small groups.

### 6. Exclusions, missing data, denominators

Follow the participants or samples from enrolment to analysis. Check that the n in each table and figure matches the n in the methods and reconciles with the flow diagram, that exclusion rules were stated before the data were seen, that excluded cases are described, and that missing data are handled (complete-case analysis assumes missingness is unrelated to the outcome, which is often false). A result that reverses with the exclusions included is a finding.

### 7. Effect size with an interval

A claim needs a size and its uncertainty, not "p < 0.05". Look for the estimate with a confidence interval, on a scale that can be judged (a difference in the original units, a risk difference, not only a standardised effect). Ask whether the lower end of the interval would still matter in practice, and whether the upper end is plausible. A very small p with an immaterial effect in a large sample is a weak claim, however significant.

### 8. Power and the null claim

For a result called significant: was the study large enough that the estimate is stable, or is it an effect magnified by a small, noisy sample (small studies that reach significance overstate the effect)? For a result called "no difference" or "no effect": a non-significant p is not evidence of equivalence. Ask for the confidence interval and whether it excludes effects that would matter, or an equivalence test against a stated margin. A power calculation done after the result using the observed effect adds nothing; one done beforehand for a stated effect size does.

### 9. Rank and report

Group findings into three tiers and order inside each by consequence:

1. **Invalidates the claim:** unit of analysis wrong in a way that changes the conclusion, outcome switched, impossible numbers in the main result, an exclusion that creates the effect.
2. **Weakens it:** unadjusted multiplicity, a null claim with a wide interval, an imprecise effect, unclear error bars on the key figure.
3. **Cosmetic:** reporting style, rounding, missing units.

State what would be needed to resolve each tier-one and tier-two item (the data, an analysis, a statement from the authors), and say what you could not check and why.

## Output format

```markdown
## Claim and estimand
[The claim, the estimand, primary outcome, prespecified or not.]

## Invalidates the claim
[Each item: location, what is wrong, the evidence or recomputation, what would resolve it.]

## Weakens the claim
[Same.]

## Cosmetic
[Brief list.]

## Not checked
[Raw data not available, supplement missing, anything outside the review.]
```

## Anti-patterns

**Judging by the conclusion.** A plausible result needs the same checking as a surprising one.

**Accepting nominal n.** Count what was independent, not what was measured.

**Treating p below 0.05 as the finding.** The size and its interval carry the claim.

**Reading a non-significant result as no effect.** It is a statement about the data, not the world.

**Treating a recomputation mismatch as an accusation.** Rounding, one-sided tests and unreported corrections explain most; ask.

## Reference files

- `references/recompute-checks.md` - read at steps 2 and 4: formulas and a script for p from the statistic, the GRIM integer check, SE to SD conversion, CI to p, and the effective sample size under clustering.
