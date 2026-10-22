# Estimate and payment terms

## Contents

- A worked three-point estimate
- The quote layout
- Payment schedules by project length
- Checks before sending

## A worked three-point estimate

Hours are best / likely / worst. Weighted = (best + 4 x likely + worst) / 6.

| Task | Best | Likely | Worst | Weighted | Risk line |
| --- | --- | --- | --- | --- | --- |
| Page templates (4) | 8 | 12 | 20 | 12.7 | no |
| Content entry from supplied copy | 4 | 8 | 24 | 10.0 | yes: client-supplied content |
| Booking-system integration | 6 | 12 | 40 | 15.7 | yes: third-party integration |
| Forms and email delivery | 3 | 4 | 6 | 4.2 | no |
| Testing and fixes | 4 | 6 | 10 | 6.3 | no |
| Deployment and handover | 2 | 3 | 5 | 3.2 | no |

Totals: weighted 52.0 hours (the raw estimate), worst case 105 hours. That spread is the
exposure. The order is: raw weighted hours, then the personal multiplier once, then the
buffer on the risk lines only, then the rate.

Case A, fewer than 8 finished jobs, so the multiplier is unknown and nothing automatic
applies. Plan client content at 14 hours and the integration at 24, each a stated figure
between weighted and worst case: 12.7 + 14.0 + 24.0 + 4.2 + 6.3 + 3.2 = 64.4 hours (64.3
from unrounded figures). Management at 10% of that is 6.4 hours; two revision rounds at
3 raw hours each are 6.0 hours. Total 64.3 + 6.4 + 6.0 = 76.7 hours; at an example
target rate of 70 an hour, 76.7 x 70 = 5,369.

Case B, 8 or more finished jobs and a median multiplier of 1.25 from
`estimate-actuals-review`, used here for every task type to keep the arithmetic short
(in practice use each task type's own). Multiply the raw hours once: 52.0 x 1.25 = 65.0
hours, which is 15.8, 12.5, 19.6, 5.2, 7.9 and 4.0 hours line by line. Then buffer the
risk lines from their multiplied figures, not by multiplying a buffered figure: plan
client content at 16 (between 12.5 and the worst case of 24) and the integration at 28
(between 19.6 and 40). Buffered task hours: 15.8 + 16.0 + 28.0 + 5.2 + 7.9 + 4.0 = 76.9.
Management at 10% of that is 7.7 hours, and it is not multiplied again because it is
taken from hours that already carry the multiplier. Two revision rounds at 3 raw hours
are 3 x 2 x 1.25 = 7.5 hours (the multiplier applied once, to the raw hours). Total
76.9 + 7.7 + 7.5 = 92.1 hours; at 70 an hour, 92.1 x 70 = 6,447.

Also name the worst case in the assumptions ("the booking provider's interface is
documented and stable"); for client content, state the delivery date and the rule that
late content moves the launch. Management and two revision rounds, each defined as one
consolidated set of written changes, stay as separate lines on the quote. A third round
is billed at the rate.

Price = (raw hours x multiplier once, then risk buffers, plus management and revisions)
x target rate. Never multiply the multiplier into hours that already carry it.

## The quote layout

One to two pages: the client and project name; a one-paragraph summary of what is
delivered; the price (or range); the line items grouped by milestone; the three
assumptions the price depends on most; the exclusions; the invoice schedule; the
pause and late-payment terms; the validity date; how to accept. The scope and
acceptance detail lives in the statement of work, which follows acceptance.

## Payment schedules by project length

| Length | Schedule | Why |
| --- | --- | --- |
| Under 2 weeks | 50% before start, 50% before handover | Too short for milestones to add anything |
| 2 to 6 weeks | 40% before start, 30% at "first working version on staging", 30% before handover | Cash tracks work done |
| Over 6 weeks | 30% before start, then monthly in arrears for work done, with the final 20% before handover | A stalled client cannot accumulate months of unpaid work |

Check each row with one test: at every point, is money received at least equal to the
cost of the work delivered so far? If a milestone is late through the client's doing,
the next invoice is still due on its own event, not on yours.

## Checks before sending

1. Every task is two days or less.
2. Risk lines are named and buffered; safe lines are not padded.
3. Rate comes from the rate calculation, not from habit.
4. Exclusions, top three assumptions and the milestone invoice schedule are on the page.
5. A validity date is stated.
6. Net terms longer than 30 days are reflected in the price.
