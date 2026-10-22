# Ramp table

Read this at step 4, when planning the volumes and recording each day.

## Contents

- Table
- How to fill it
- Decision rule

## Table

| Day | Audience tier | Planned volume | Actual volume | Complaint rate | Hard bounce rate | Postmaster or SNDS | Deferrals | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Active in last 30 days, largest provider | 300 | | | | | | |
| 2 | Same | 600 | | | | | | |
| 3 | Same | 1,200 | | | | | | |
| 4 | Same, plus second provider | 2,400 | | | | | | |

The figures are an illustration of doubling from a few hundred; the plan is whatever your thresholds allow.

## How to fill it

Fill the planned column before day one, from the audience size and the number of days you think the ramp will take if nothing goes wrong. Record complaint rate from the feedback loops and provider dashboards, hard bounces from the platform, and deferrals from the SMTP responses. Postmaster data lags by a day or more, so a day's decision uses the previous day's dashboard reading, and it appears only once Gmail volume is substantial; before then use feedback-loop counts. Judge rates on cumulative sends over several days, or on an absolute count while daily volume is small.

## Decision rule

| Observation | Decision |
| --- | --- |
| All thresholds met | Increase for the next period |
| One metric near its limit | Hold at the same volume |
| Any limit breached | Step back one level, find the cause |
| Dashboard drops a rating | Pause that provider, engaged recipients only |
| Complaints at the stop level | Stop sending, begin diagnosis |

Write the decision and the reason in the table each day, so the record shows why volume moved.
