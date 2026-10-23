# Reproduction log and verdict

## What to extract from the paper (step 2)

| Item | Where it hides | Why it matters |
| --- | --- | --- |
| Data split and size | Experiments section, appendix, dataset card | A different split changes every number |
| Preprocessing | Appendix, code | Tokenisation, normalisation and filtering change results |
| Hyperparameters | Appendix tables, config files | Learning rate, schedule, batch size, epochs |
| Baselines and how they were tuned | Baselines paragraph | An untuned baseline inflates the gain |
| Metric definition | Evaluation section | Macro versus micro averaging, best versus last checkpoint |
| Seeds and variance | Tables, footnotes | Defines how close is close enough |
| Compute used | Appendix | Tells you whether the setup is affordable |
| Known issues | Repository issues, errata, later papers | Other people's failed attempts |

## The discrepancy log

One row per gap, kept as you go.

```markdown
| # | Gap or contradiction | Source | Choice made | Reason | Effect seen |
| --- | --- | --- | --- | --- | --- |
| 1 | Learning-rate schedule not stated | Sec. 4.2 | Linear decay to zero | Common default for this architecture | Not yet tested |
| 2 | Table 2 reports 84.1, text says 84.7 | Table 2, Sec. 5 | Compared against 84.1 | Table is the primary figure | None |
```

Fill "Effect seen" when a later run varies the choice. A choice that moves the result by more than the seed spread is the most important line in the report.

## The delta table

```markdown
| Setting | Paper | Ours: mean | Ours: std (n=3) | Delta (ours - paper) | Within tolerance? |
| --- | --- | --- | --- | --- | --- |
| Baseline | 78.2 | 78.0 | 0.3 | -0.2 | yes |
| Method | 81.5 | 79.9 | 0.4 | -1.6 | no |
```

State whether the paper's number is a single run, a mean or a best-of. Compare like with like. Report the seed list and the commit.

## The verdict template

```markdown
## Verdict: reproduced | partly reproduced | not reproduced

Claim tested: <method, metric, dataset>
Setup: <authors' code at commit X, or own implementation; full or reduced data; seeds>
Result: <one line with the main delta>
Where it differs: <cells or conditions>
Choices that mattered: <rows from the log>
Recommendation: <adopt, watch, drop, or retest with a change, tied to the original decision>
Time spent against the two-week box: <days>
```

## Unchanged-code check that fails

Work through, one change at a time, recording each: the dependency versions against the repository's stated ones; the data version and preprocessing; the seed handling; the hardware and precision; the evaluation script against the paper's metric definition. Stop at the first change that moves the number and log it.
