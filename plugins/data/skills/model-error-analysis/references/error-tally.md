# Error tally

## The labelling sheet

One row per sampled error. Fill the columns left to right, and fill "your label" before revealing the stored label and the prediction, so the model's answer cannot steer the judgement.

| id | inputs shown | your label | confidence | stored label | prediction | score | cause | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18823 | link to record | positive | high | negative | positive | 0.97 | label wrong | refund issued two days later, label job ran before |
| 40211 | link to record | negative | medium | positive | negative | 0.04 | information missing | fraud visible only in device history, not a model input |

Show the reviewer only what the model sees, plus the minimum context needed to judge the true label. Showing extra information (the outcome, later events) makes "information missing" errors look easy and undercounts that category.

## Cause definitions and borderline cases

- **Label wrong.** The stored label is incorrect by the labelling guidelines. If the guidelines themselves are ambiguous on this case, record it as "genuinely hard" and note the guideline gap; changing labels to match your own reading of an unclear rule just moves the noise.
- **Information missing.** The correct answer depends on information not in the inputs. Note what that information is, since the notes become the feature backlog.
- **Pipeline bug.** The model's input differs from the true state of the record: a null where the source has a value, an old value, a wrong unit, a mis-parsed category. Note the field.
- **Under-represented case.** The inputs contain the information, but the pattern is rare in training. Note the pattern so you can count how often it occurs.
- **Genuinely hard.** Two careful reviewers would disagree, or the outcome is close to random given any reasonable inputs.

When two causes apply, record the one whose fix comes first: a pipeline bug before a missing feature, a label error before anything else.

## Sample sizing

A hundred worst errors is enough to rank causes when one or two dominate, which is the usual case. As a rough guide, a cause that accounts for 30 of 100 has a 95% interval of roughly 22% to 40% (Wilson), which does not overlap the 6% to 17% of a cause at 10 of 100. To separate two causes of similar size, review more.

The random 50 from the remaining errors tell you whether the extremes are representative. If label errors are 40% of the worst 100 but 5% of the random 50, label cleaning will fix the most confident mistakes but move the metric less than the tally suggests.

For multi-class models, sample per confused pair (true class A predicted as B) for the pairs with the largest counts, since each pair usually has its own cause.

Use two reviewers on a subset of 30 and report how often they agree on the cause. Low agreement means the categories or the guidelines need sharpening before the tally can direct work.

## From tally to plan

| Dominant cause | First action | Measure of success |
| --- | --- | --- |
| Label wrong | Relabel the affected slice, fix the label job or guideline, measure labeller agreement | Fewer confident errors in the next sample; validation metric on a relabelled validation set |
| Information missing | Specify the feature or source from the notes and check it is available at prediction time | Errors of this kind fall in the next tally |
| Pipeline bug | Fix the transformation, add a data check for that field | Bug class gone from the next sample |
| Under-represented case | Collect or weight more examples of the pattern | Segment metric for that pattern improves |
| Genuinely hard | Route to a human, or accept and price in | Cost at the chosen threshold, not the metric |

Relabelling only training data and then measuring on uncorrected validation labels hides the improvement; correct validation labels with the same procedure, and say that you did.
