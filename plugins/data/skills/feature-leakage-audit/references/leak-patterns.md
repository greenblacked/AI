# Leak patterns and point-in-time joins

## Contents

- Leak shapes
- Questions to ask of each source
- Point-in-time join in SQL
- Point-in-time join in pandas
- Splits with a gap

## Leak shapes

| Shape | Example | How it shows up |
| --- | --- | --- |
| Field written by the outcome process | Cancellation reason, refund amount, collections flag, discharge code, fraud review outcome | Populated almost only for positives; missingness alone predicts the label |
| Current-state column | `status`, `balance`, `last_login_at`, `num_orders` read from today's table | Strong importance; values for old rows reflect activity after the outcome |
| Aggregate over the whole table | Customer lifetime value, total tickets, mean of all past and future orders | Correlates with label because it includes the label period |
| Window ending at extraction date | "Logins in last 30 days" computed when the training set was built | For historical rows, the window lies after the prediction time |
| Identifier encoding time or outcome | Sequential ids issued after an event, file names containing a diagnosis, batch numbers per outcome | Tree models split on the id; high importance on a column that should be meaningless |
| Proxy for the label | Account closed date for a churn label, "follow-up scheduled" for a readmission label | Near-perfect solo score |
| Human decision made with hindsight | Agent notes, manual tags, priority set by someone who saw the outcome | Text or tag features dominate; their timestamps are after the event |
| Preprocessing on full data | Scaler, vocabulary, target encoding or feature selection fitted before splitting | Cross-validated score drops once the pipeline moves inside folds |
| Repeated entities across split | Several rows per customer, patient, device or session in both train and test | Score drops sharply under a group split |
| Duplicates and augmentations | Same record ingested twice, resized copies of one image, reposted text | Test rows match training rows exactly or nearly |
| Future information in time series | Rolling statistics centred on the row, or lags shorter than the horizon | Error far below what a live forecast achieves |

## Questions to ask of each source

1. Which timestamp says when this value became known: an event time, a write time, a load time? Is it stored, or only the latest value?
2. Is the row ever updated after it is first written? If so, is history kept (a snapshot or change table), or is the old value lost?
3. Which process writes this field, and does that process run because of the outcome?
4. How long after the event does the value reach the table the model reads from in production?
5. Would this exact value exist at prediction time for a row where the outcome has not yet happened?

A feature that fails question 5 is a leak regardless of how plausible it sounds.

## Point-in-time join in SQL

Pick, for each prediction row, the latest source row available at or before the prediction time, accounting for load latency. Window-function form, portable across most warehouses:

```sql
WITH candidates AS (
  SELECT
    p.entity_id,
    p.prediction_ts,
    s.plan_tier,
    ROW_NUMBER() OVER (
      PARTITION BY p.entity_id, p.prediction_ts
      ORDER BY s.available_ts DESC
    ) AS rn
  FROM predictions AS p
  LEFT JOIN subscription_snapshots AS s
    ON s.entity_id = p.entity_id
   AND s.available_ts <= p.prediction_ts
)
SELECT entity_id, prediction_ts, plan_tier
FROM candidates
WHERE rn = 1;
```

The `LEFT JOIN` keeps a prediction row with no snapshot yet (a new entity) and gives it a null feature, as the pandas version does; an inner join would delete those rows and leave a training set that quietly excludes new customers. `available_ts` should be the load time into the table production reads, not the business event time, unless the two are the same. If the table only stores a business time, add the typical load delay to it explicitly and write the assumption down.

Windowed aggregates end at the prediction time:

```sql
SELECT
  p.entity_id,
  p.prediction_ts,
  COUNT(o.order_id) AS orders_90d
FROM predictions AS p
LEFT JOIN orders AS o
  ON o.entity_id = p.entity_id
 AND o.available_ts <= p.prediction_ts
 AND o.available_ts > p.prediction_ts - INTERVAL '90' DAY
GROUP BY p.entity_id, p.prediction_ts;
```

Interval syntax differs between warehouses; keep the bounds, adapt the literal.

## Point-in-time join in pandas

```python
import pandas as pd

predictions = predictions.sort_values("prediction_ts")
snapshots = snapshots.sort_values("available_ts")

features = pd.merge_asof(
    predictions,
    snapshots[["entity_id", "available_ts", "plan_tier"]],
    left_on="prediction_ts",
    right_on="available_ts",
    by="entity_id",
    direction="backward",
    allow_exact_matches=False,  # a value stamped at the same instant is not yet visible
)
```

`allow_exact_matches=False` makes this join stricter than the SQL above, which accepts `available_ts = prediction_ts`; use `<` in the SQL if a value stamped at the same instant is not yet visible in production, so both versions agree. Both frames must be sorted on their time keys, and the time columns must share a dtype and time zone. Check afterwards that `available_ts <= prediction_ts` on every row and count rows with no match, which become missing features.

## Splits with a gap

For a time split, leave a gap between the end of training and the start of test at least as long as the label window. A training row predicted on 31 March with a 30-day label window has a label that depends on what happened in April; if test starts on 1 April, training labels have seen the test period.

`sklearn.model_selection.TimeSeriesSplit` takes a `gap` argument in samples, which only equals a time gap when rows are evenly spaced in time. With irregular rows, build the folds by date explicitly.
