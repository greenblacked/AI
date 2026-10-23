# Step log

## Contents

- Log columns
- Per-customer sheet
- Weekly roll-up
- Rules in one place

## Log columns

One row per step performed, written the same day.

| Column | Example | Why it is there |
| --- | --- | --- |
| `date` | 2026-11-04 | Orders the runs and shows cycle length |
| `customer_id` | C-03 | Per-customer cost and repeat usage |
| `step` | match bank lines | Fixed verb-noun name so runs can be counted |
| `trigger` | customer emailed statement | Shows which steps start unprompted |
| `prompted` | no | Whether you nudged the customer first |
| `who` | AB | Spreads load and shows who holds the know-how |
| `minutes` | 35 | Cost and the automation rule |
| `inputs_needed` | CSV export, login to bank portal | Becomes the automated step's inputs |
| `redo` | yes: wrong date format | Shows where the hand-off breaks |
| `reaction` | "this is the bit I hate doing" | What the customer values, in their words |

Keep it in one shared sheet, not a log per person. A step name that drifts ("match lines", "bank matching") hides frequency; fix names at the weekly review.

## Per-customer sheet

| Customer | Start | Deliveries | Unprompted requests (dates) | Hours | Cost | Revenue | Cost minus revenue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-03 | 2026-10-06 | 3 | 2026-11-03, 2026-12-02 | 7.5 | 450 | 300 | 150 |

Cost is hours at a loaded hourly rate plus any tool spend for that customer. Write the rate you used at the top of the sheet.

## Weekly roll-up

From the log, per step:

| Step | Runs | Median minutes | Total minutes | Redo rate | Typical reaction | Candidate |
| --- | --- | --- | --- | --- | --- | --- |
| match bank lines | 14 | 35 | 520 | 21% | "the bit I hate" | yes |
| chase missing receipts | 22 | 10 | 240 | 5% | not noticed | no: under 15 minutes; try removing |
| categorise expenses | 6 | 40 | 250 | 50% | mixed | no: under 10 runs |

In a spreadsheet, `COUNTIF` over the step column gives runs, `MEDIAN(IF(...))` as an array formula or a pivot table gives the median, and `SUMIF` gives total minutes. Use the median rather than the mean, because one run that went wrong inflates a mean over a handful of runs.

## Rules in one place

| Rule | Value | Why |
| --- | --- | --- |
| Cohort size | 5 to 10 customers, one segment | Enough runs to count, few enough to serve by hand |
| Repeat usage | Unprompted request within two natural cycles | A nudged request measures the nudge |
| Automation candidate | 10 or more runs and median over 15 minutes | Fewer runs hide variations; shorter steps rarely repay the code |
| Automation order | Highest total minutes first | Saves the most time per step automated |
| Exit | At the time box, most customers did not repeat unprompted within two natural cycles of their first delivery | A service nobody repeats is not worth automating; a repeat in the third cycle does not count, or a long time box would pass a service the rule fails |
| Data | Written agreement, controlled storage, deletion at the end | People handling data by hand are still handling customer data |
