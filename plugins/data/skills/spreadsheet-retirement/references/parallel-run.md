# Parallel run

## Contents

- Parity pitfalls
- Loading the sheet's output
- The reconciliation query
- The difference log
- Clean-cycle rule
- The acceptance record

## Parity pitfalls

Match these to the sheet before the first comparison; each one produces small, persistent differences that waste a cycle.

| Pitfall | What to match |
| --- | --- |
| Rounding rule | Excel's `ROUND` rounds halves away from zero. Python's built-in `round()` rounds halves to even. SQL `ROUND` behaviour depends on the engine and on whether the type is exact numeric or floating point; test `ROUND(2.5, 0)` and `ROUND(-2.5, 0)` on your warehouse with both types |
| Rounding step | Whether the sheet rounds each line and sums the rounded lines, or sums and rounds the total. These differ by cents per hundred lines |
| Number type | Spreadsheets compute in binary floating point. Money in the pipeline belongs in a fixed-point decimal type; compare after rounding to the currency's minor unit |
| Blanks | A blank cell is zero in arithmetic and excluded from `AVERAGE`. Match the pipeline's null handling to each use |
| Dates | Spreadsheets store dates as serial numbers in local time with no zone. Agree the cut-off time and zone for each period |
| Exchange rates | Same source, same date, same direction, same rounding of the rate itself |
| Text keys | Leading zeros dropped by the spreadsheet (`00123` becoming `123`), trailing spaces, case. Normalise both sides the same way before joining |
| Extract timing | Both outputs must use inputs extracted at the same moment, or late-arriving rows look like defects |

## Loading the sheet's output

Export the sheet's consumer-facing tab for each cycle to CSV with values (not formulas) and load it into a comparison schema with its cycle identifier. Keep the export file as part of the evidence. Text keys are loaded as text so leading zeros survive.

## The reconciliation query

Join at the lowest grain the sheet has. Compare after rounding both sides to the minor unit. Check first that `line_key` is never blank or null on either side, since a null key never joins and would be reported as missing from the other side, and that it is unique on each side: two rows for one key on each side become four comparisons and invent differences, and equal row counts do not prove it. Run `SELECT line_key, COUNT(*) FROM <side> GROUP BY 1 HAVING COUNT(*) > 1` on both and expect nothing; if either returns rows, aggregate that side to the key first.

```sql
WITH sheet AS (
  SELECT cycle, line_key, ROUND(amount, 2) AS amount, 1 AS in_sheet
  FROM recon.sheet_output
  WHERE cycle = '2026-09'
),
pipe AS (
  SELECT cycle, line_key, ROUND(amount, 2) AS amount, 1 AS in_pipe
  FROM reporting.commission_lines
  WHERE cycle = '2026-09'
)
SELECT COALESCE(s.line_key, p.line_key) AS line_key,
       s.amount AS sheet_amount,
       p.amount AS pipeline_amount,
       COALESCE(p.amount, 0) - COALESCE(s.amount, 0) AS diff,
       CASE
         WHEN s.in_sheet IS NULL THEN 'pipeline only'   -- presence flags, not the keys
         WHEN p.in_pipe  IS NULL THEN 'sheet only'
         WHEN (s.amount <> p.amount OR (s.amount IS NULL) <> (p.amount IS NULL)) THEN 'value differs'
       END AS kind
FROM sheet s
FULL OUTER JOIN pipe p
  ON s.line_key = p.line_key
WHERE s.in_sheet IS NULL
   OR p.in_pipe  IS NULL
   OR (s.amount <> p.amount OR (s.amount IS NULL) <> (p.amount IS NULL))
ORDER BY ABS(COALESCE(p.amount, 0) - COALESCE(s.amount, 0)) DESC;
```

An empty result is a clean comparison for that measure. Compare amounts null-safely, not with `<>` alone: when one side's amount is null, `<>` yields unknown and the line silently drops out of the result. The second half of the predicate catches that case; it is written out because Redshift has no `IS DISTINCT FROM`, which is the shorter form on Snowflake, BigQuery and PostgreSQL. Run it for each figure the consumer reads, not only the headline amount. Before trusting an empty result, check that both sides have the expected row count; two empty inputs also reconcile perfectly.

## The difference log

One row per difference, or per group of differences with a single cause:

| Cycle | Line keys | Kind | Amount | Cause | Class | Resolution | Agreed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09 | 4 lines | value differs | 0.01 to 0.03 each | Sheet rounds each line before summing | Parity defect | Pipeline now rounds per line | Finance lead |
| 2026-09 | `ACME-17` | sheet only | 1,200.00 | Manual add-back after phone call | Undocumented override | Adjustment table row | Finance lead |
| 2026-09 | 12 lines | pipeline only | 3,450.00 | Test accounts removed by hand in sheet | Undocumented override | Exclusion table | Sales operations |
| 2026-10 | `NORTH` region | value differs | 310.00 | Sheet's VLOOKUP took first match on duplicated rep | Agreed bug fix | Listed change, pipeline correct | Finance lead |

Classes: parity defect (pipeline must change), undocumented override (back to the inventory), agreed bug fix (expected difference, listed in the acceptance record), input timing (align extracts and rerun), unexplained (the cycle is not clean).

If a difference turns out to be two teams defining the figure differently rather than the sheet and pipeline disagreeing, settle the definition with `metric-reconciliation` before continuing.

## Clean-cycle rule

A cycle is clean when every difference is either fixed and the rerun is empty, or is an agreed bug fix listed in the acceptance record. Require two consecutive clean cycles. If the sheet has period-end handling (quarter-end accruals, year-end true-ups), at least one compared cycle includes it. Where waiting for one is not practical, the acceptance record names the next such cycle, and the sheet stays buildable until that cycle has been compared clean.

## The acceptance record

```markdown
## Acceptance: <report name>
Owner and acceptance tester: <name, role>
Cycles compared: <cycle ids>, grain: <line key>
Clean cycles: <ids>
Agreed changes from the sheet: <list, each with reason>
Overrides now held as rules: <table names and maintainers>
Pipeline is the source from: <date / cycle>
Sheet archived read-only at: <location>, retention: <period>
Signed: <owner>, <date>
```

The owner signs. Consumers are told by the owner, with the date and the list of agreed changes, so a figure that moves because of a fixed bug is expected rather than discovered.
