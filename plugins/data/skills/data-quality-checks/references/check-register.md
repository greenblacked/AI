# Check register

## Contents

- Mining incidents
- The incident table
- The check register
- The firing log
- Monthly pruning

## Mining incidents

Look in this order, because each source finds a different kind of incident:

1. Postmortems and incident tickets that name the table or its upstream models. These have root causes already written.
2. Restatements: any figure that was published and later corrected. Search the reporting channel and the finance close notes for "restated", "corrected", "updated figure".
3. Consumer complaints: threads where someone said the numbers looked wrong. Many were never ticketed, and the delay between the data going wrong and the complaint is the number this exercise is trying to shrink.
4. Manual fixes in version control: commits to the model that add a filter, a dedupe or a `COALESCE` with a message like "fix duplicates". Each one is an incident that was fixed without being recorded.

Stop at ten. Older incidents often describe a pipeline that no longer exists.

## The incident table

| # | Date | What was wrong | Found by | Delay to detection | Root cause | Cheapest check at this table | Already covered? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | Revenue doubled for one day | CFO in weekly review | 4 days | Source reloaded a day without truncating | Uniqueness on `(order_id)` | No |
| 2 | | Orders missing for EU | Regional lead | 2 days | Upstream API key expired; job succeeded with zero rows | Volume per region vs weekday history | No |
| 3 | | New refund status counted as sale | Analyst | 3 weeks | Producer added `partially_refunded` | Enum drift on `status` | No; ingest defence also needed |

The rows above are illustrations of the shape. Group rows by root cause; one check per distinct cause. Where a root cause sits upstream (the producer changed something), record the check at this table and note that the ingest defence belongs to `upstream-change-defense`.

## The check register

Keep one register per table, in version control beside the model definitions, so a change to a check is reviewed like code.

| Field | Meaning |
| --- | --- |
| `check_id` | Stable name, used in the firing log |
| `table` | The table or model checked |
| `origin` | Incident number from the table above, or the baseline dimension |
| `measure` | The query or test that produces the measured value |
| `threshold` | The bound, and the history window it was derived from |
| `backtest` | Firings in the replay window, and whether it fired on the incident days |
| `action` | `block`, `warn` or `log` |
| `owner` | The team whose queue receives it |
| `override` | Who may release a block, and how |
| `added`, `last_reviewed` | Dates |

## The firing log

Every firing writes one row: `check_id`, time, measured value, threshold, and two fields filled in by the owner within a working day: `acted` (yes or no, with what was done) and `real` (was the data actually wrong). If the check runner cannot record the owner's answer, a weekly review of the owner's queue can fill it in. Without these two fields the monthly prune is guesswork.

## Monthly pruning

Once a month, for each check, read its firings since the last review:

| Firings | Acted on | Real problems | Decision |
| --- | --- | --- | --- |
| Several | None | None | Delete, or demote to `log` if the trend has value |
| Several | Some | Few | Retune the threshold by backtest; it is too tight |
| Some | All | All | Keep; consider promoting `warn` to `block` if the problem reached a consumer before anyone acted |
| None | — | — | Keep if incident-derived; for a baseline check on a column nobody uses any more, delete |

Also check the other direction: any data incident this month that no check caught gets a new row in the incident table and, usually, a new check. Record what was deleted, demoted, re-tuned and added in the register's history so the next review can see whether the suite is converging.
