# Log and multiplier

## Log layout

One row per project per task type. A spreadsheet is enough.

| project | closed | task type | est h | tracked h | client-added h | rework h | ratio | reconstructed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Acme site | 2026-03-14 | build | 40 | 58 | 0 | 0 | 1.45 | no |
| Acme site | 2026-03-14 | revisions | 8 | 14 | 6 | 0 | 1.00 | no |
| Birch shop | 2026-04-30 | build | 60 | 57 | 0 | 0 | 0.95 | no |

Every task type gets a row, including those that came in on or under estimate, so the sample is not made only of overruns. Record client-added and rework hours in their own columns. Ratio = (tracked hours - client-added hours - rework hours) / estimated hours, so it measures only your own estimating error and can be below 1.0. A task type estimated at 0 hours (unplanned work) has no ratio: log it as a missing estimate on a separate line and leave it out of the median.

## Worked median

Build ratios from non-reconstructed rows across eight projects: 1.1, 1.2, 1.25, 1.3, 1.4, 1.45, 1.5, 2.6.

- Sorted, the middle two are 1.3 and 1.4, so the median is 1.35.
- The mean is (1.1+1.2+1.25+1.3+1.4+1.45+1.5+2.6) / 8 = 1.475, pulled up by the 2.6.

Applying 1.475 would overprice a typical project because of one disaster. Apply 1.35, and look at the 2.6 project separately for its cause.

Multiplier use: raw build estimate 40 hours x 1.35 = 54 hours quoted. Pass the 54 into `fixed-price-quote` as the estimate, and say in the quote notes which multiplier was applied.

## Effective hourly rate

effective rate = fee / tracked hours

Example: fee 6,000, tracked hours 80 (including 9 hours of email and calls) gives 75 per hour. Had the 9 hours been left out, 71 hours gives 84.51, which flatters the job.

With a subcontractor: you charged 6,000 in total, paid 1,500 for their part, and spent 55 of your own hours. Your rate is (6,000 - 1,500) / 55 = 81.82. Subcontract margin is what you charged the client for their part minus the 1,500 paid; if the client was charged 2,000 for it, the margin is 500.

## Reading the table

- A ratio near 1.0 across three reviews in a row means the multiplier can fall.
- A task type with a high ratio and a high spread (some projects 1.1, some 2.2) usually hides two kinds of work under one label. Split the label.
- Project management and communication are the types most often under-tracked, and their multiplier is usually the highest.
