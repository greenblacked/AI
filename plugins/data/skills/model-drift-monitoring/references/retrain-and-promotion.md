# Retrain and promotion

The label-delay measurement, proxy validation, the retrain trigger policy, the promotion gate and the rollback drill.

## Contents

- Measuring label delay
- Validating a proxy
- Retrain trigger policy
- Promotion checklist
- Rollback drill

## Measuring label delay

Take cohorts old enough that their labels are complete — older than the longest plausible lag, with a margin — and measure how quickly their labels arrived. PostgreSQL syntax; adjust the date arithmetic for your warehouse.

```sql
WITH labelled AS (
  SELECT p.prediction_id,
         CAST(l.label_ts AS DATE) - CAST(p.prediction_ts AS DATE) AS lag_days
  FROM predictions p
  JOIN labels l ON l.prediction_id = p.prediction_id
  WHERE p.prediction_ts < CURRENT_DATE - INTERVAL '365 days'
)
SELECT k AS days_after_prediction,
       AVG(CASE WHEN lag_days <= k THEN 1.0 ELSE 0.0 END) AS share_of_labels_arrived
FROM labelled
CROSS JOIN (VALUES (1), (7), (14), (30), (60), (90), (180)) AS t(k)
GROUP BY k
ORDER BY k;
```

Read it as a maturity curve. The maturity point is the first lag at which the share is close enough to one that later arrivals cannot change a decision; write the chosen level down. For a label that records an event (a chargeback, a churn, a default), this table covers positives only, since negatives are never "recorded": a negative becomes final when the observation window closes, so maturity is at least the window length.

## Validating a proxy

A proxy earns trust only by having tracked the matured metric in the past.

1. Pick candidates that exist before maturity: the label share at a fixed early age (day 7) compared with past cohorts at day 7; manual review overturn rate; customer appeals; a downstream conversion.
2. For each past cohort, compute the candidate at its early age and the matured metric.
3. Keep a candidate only if it moved in the same direction in the periods where the matured metric moved, including at least one known bad period. Correlation over quiet periods proves little; the bad periods are the test.
4. Record which periods were used, so the next person can re-run the check when the model changes.

## Retrain trigger policy

Fill this in and store it beside the monitor definition.

```markdown
Model: <name>, owner <team>
Performance metric: <e.g. precision at 80% recall>, computed on cohorts older than <maturity point>
Retrain when: metric below <threshold> for <n> consecutive matured cohorts,
  or expected cost per 1000 decisions above <threshold>,
  or proxy <name> beyond <threshold> for <n> days
Scheduled retrain: <cadence or none>; passes the same promotion gate
Drift alone: opens an investigation ticket; outcomes are pipeline fix, record and move on, or bring retrain forward
Training window: <rule>, excluding any span with an open data incident
```

The last line matters: a retrain window that includes a known upstream defect teaches the model the defect. Exclude the span, or wait until it has been repaired at source.

## Promotion checklist

- [ ] Challenger trained only on data before the cutoff; its features computed by the same code version serving will run.
- [ ] Evaluation set: matured rows after the cutoff, frozen (written to a versioned location with a checksum) before either model is scored.
- [ ] Both models scored on exactly the same rows; the comparison is the paired difference in the metric, with a bootstrap interval resampling rows.
- [ ] The interval excludes zero in the challenger's favour by at least the practical threshold agreed in advance, not merely "better".
- [ ] Every agreed slice checked; no slice worse than its tolerance.
- [ ] Calibration checked if downstream uses the score as a probability.
- [ ] Shadow period on live traffic: prediction distribution and decision rate compared with the champion's, latency within budget.
- [ ] Rollback rehearsed in this release, not assumed from the last one.

## Rollback drill

Promotion should be a pointer move: a registered-model alias (MLflow model registry aliases work this way), a version in a config the server reads, or a deployment tag. Rollback is the same move in reverse.

Rehearse it before promotion:

1. With the challenger in shadow, move the pointer to it in a staging environment, confirm the server reports the new version, then move it back.
2. Confirm the old champion still loads: its artefact, its preprocessing artefacts and its feature code version are all still available. A rollback that needs a vocabulary file nobody kept is not a rollback.
3. Time it, and write the exact command and the time in the promotion record.

After promotion, keep the previous champion loadable for at least one maturity period, because that is how long it takes to learn from labels whether the promotion was right.
