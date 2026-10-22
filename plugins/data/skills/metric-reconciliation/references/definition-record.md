# The definition record and retiring the duplicate

## Choosing the rule for each cause

Decide each cause by the decision the metric feeds, not by which team found the gap or which number is larger. Ask the people who act on the metric what they would do differently if it moved, and pick the rule that makes it move for that reason.

| Cause | Usual right answer | When it is not |
| --- | --- | --- |
| Time zone | The time zone the business runs its day in, named (not an offset) | A global product reporting per region, where each region's own zone is right and the global total is a sum of regional days |
| Snapshot time | Both sides read the same source; figures before the maturity point labelled provisional | Finance close, where a figure frozen at close is correct even after late rows land, and later rows go into the next period |
| Filter and inclusion | Exclude test, internal and fraudulent activity everywhere | A metric explicitly about operations, where internal volume is real load |
| Dedupe | One per real-world event, by a stable event id | A metric about attempts (retries, failures), which counts them on purpose |
| Join grain | The base table's grain, always | None: a fan-out is a defect |
| Currency and units | A named rate source and rate date, stored minor units | Finance reporting, which follows the accounting policy's rate rule |

## The definition record

Write it where the metric is computed — the semantic layer's metric definition, the dbt model's YAML, the metrics repository — not in a separate wiki page that drifts from the code. Keep these fields:

```yaml
metric: signups
owner: growth-analytics          # a team that answers questions about it
description: >
  New accounts created by a person, counted once per account, on the London
  calendar day the account was created.
grain: one row per account
time_zone: Europe/London
includes: all self-serve and partner-API signups
excludes: staff accounts, test accounts, accounts deleted as fraud within 24 hours
dedupe: one per account_id; a retried submission that creates no new account is not counted
maturity: provisional until 06:00 London the following day
currency_and_units: not applicable
source: models/marts/fct_signups.sql
supersedes: "marketing dashboard 'Signups' tile (retired 2026-10-21)"
reconciled: "2026-10-07 GB slice, residual 0; see the reconciliation note linked from the pull request"
```

`owner` is a team, not a person who might leave. `supersedes` is what stops the old version being rebuilt from memory.

## Retiring or renaming the duplicate

1. Repoint every dashboard tile and report that shows the metric under this name at the owned definition. Find them through the BI tool's content search and the warehouse query log for the old model or query, not from memory.
2. If the other version answers a genuinely different question, keep it under a different name that says how it differs, with its own record. Two metrics are fine; two metrics with one name are the defect.
3. Otherwise, remove it: hide the old tile or model behind a notice pointing at the new one for one reporting cycle, then delete it. Removing a table or column other teams query is its own change; find its readers first with `consumer-discovery`.
4. Tell the people who asked the question, with the reconciliation table and the new definition's location, so they stop comparing the two.
5. Re-run the reconciliation on a fresh day a week later. Both sides should now produce the same figure with no work at all; if they do not, a consumer was missed in step 1.
