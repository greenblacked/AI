# Pilot and projection

## Contents

- Drawing the stratified sample
- Failure-cause log
- Projection arithmetic
- Go or no-go

## Drawing the stratified sample

Pick two or three strata that change how the prompt behaves, for example length bucket and source system. Allocate the 200 items equally across the strata cells (200 divided by the number of cells, at least ten each), so a rare shape is not drawn zero times; if 200 divided by the number of cells is below ten (more than twenty cells), set ten per cell and accept a pilot above 200. A cell holding fewer items than the per-cell count contributes all of them; say so in the pilot record. Fix the random seed and store the item ids, so the pilot can be rerun after a prompt change on the same items.

```sql
-- :per_stratum from the allocation above, repeatable ordering by a hash of the id
SELECT id, source, length_bucket
FROM (
  SELECT id, source, length_bucket,
         ROW_NUMBER() OVER (PARTITION BY source, length_bucket
                            ORDER BY md5(id || 'pilot-seed-1')) AS rn
  FROM items
) t
WHERE rn <= :per_stratum;
```

Use the dialect's own hash function if `md5` is missing. If the cells total more than 200, trim afterwards while keeping at least ten per stratum, except for cells that hold fewer items than that.

## Failure-cause log

Run the 200, then record one line per failure:

| Item id | Stratum | Raw output (first 200 characters) | Cause | Fix |
| --- | --- | --- | --- | --- |
| 1042 | long, email | truncated JSON | stop reason was max tokens | raise output cap or shorten schema |
| 1187 | non-English | label not in enum | instruction written for English | add a rule and an example |

Count by cause. Fix the largest cause, rerun the same 200, and repeat until the failure rate is stable and the remaining causes are individually small. Keep the final failure rate: it feeds the projection.

## Projection arithmetic

Record these from the pilot logs, not from estimates:

- mean and 95th percentile input tokens per item
- mean and 95th percentile output tokens per item
- attempts per item = total model calls made in the pilot (from the logs, counting every retry and repair call) / items in the pilot
- sustained requests per minute actually achieved, and the 429 rate at that level

Then:

```text
cost = items x attempts x (mean_in x price_in + mean_out x price_out)
time_minutes = items x attempts / sustained_requests_per_minute
```

Prices are per token (or per million tokens: convert once and keep the unit in the cell label). If the batch endpoint is used, apply its documented discount to the affected tokens only after confirming it covers the model and mode in use. Add the audit labelling effort and the dead-letter review time to the plan; they are real costs that the token arithmetic omits.

Report the 95th percentile alongside the mean. A mean hides a long tail of large inputs that drive both the cost and the truncation failures.

## Go or no-go

| Pilot result | Decision |
| --- | --- |
| Validation failure rate above the bar, one dominant cause | Fix that cause and rerun the pilot |
| Failure rate acceptable, projection within budget | Go, with the stop rule set |
| Projection far over budget | Shorten the prompt, trim the input, use a smaller model on a re-piloted sample, or reduce scope |
| Throughput too low for the deadline | Raise concurrency within the limit, move to the batch endpoint if the deadline allows, or request a higher quota |
| Hand-read outputs look wrong although valid | Do not scale; fix the prompt, then run the audit step on the pilot itself |
