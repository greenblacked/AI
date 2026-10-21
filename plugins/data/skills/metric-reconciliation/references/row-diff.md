# The row diff and the cause tests

## Contents

- Keyed row sets
- The full outer join and buckets
- Checking the buckets add up
- Cause 1: time zone and day boundary
- Cause 2: snapshot time
- Cause 3: filter and inclusion
- Cause 4: dedupe rule
- Cause 5: join grain
- Cause 6: currency and units
- A worked reconciliation

## Keyed row sets

Rewrite each side's logic so it returns one row per entity key with that key's contribution, for the frozen slice only. Keep every rule the side applies — filters, dedupe, joins, conversions — because those rules are what you are about to compare. Add the columns the cause tests will need: the event timestamp in UTC, the load timestamp, and the attributes filters usually act on.

```sql
-- side A, as the growth dashboard computes it
CREATE TEMPORARY TABLE side_a AS
SELECT
  o.order_id                AS k,
  SUM(o.amount)             AS v,
  MIN(o.created_at)         AS event_ts_utc,
  MAX(o._loaded_at)         AS loaded_at
FROM orders o
WHERE o.created_at >= '2026-10-07 00:00:00' AND o.created_at < '2026-10-08 00:00:00'
  AND o.country = 'GB'
GROUP BY o.order_id;
```

Prove uniqueness on `k` for each side before diffing (`SELECT k FROM side_a GROUP BY k HAVING COUNT(*) > 1`). A side that is not unique on its key has a join-grain problem of its own.

## The full outer join and buckets

```sql
WITH d AS (
  SELECT
    COALESCE(a.k, b.k) AS k,
    a.v AS a_v,
    b.v AS b_v,
    CASE
      WHEN b.k IS NULL THEN 'only_a'
      WHEN a.k IS NULL THEN 'only_b'
      WHEN a.v = b.v   THEN 'match'
      ELSE 'value_differs'
    END AS bucket
  FROM side_a a
  FULL OUTER JOIN side_b b ON a.k = b.k
)
SELECT
  bucket,
  COUNT(*)                         AS keys,
  SUM(COALESCE(a_v, 0))            AS a_total,
  SUM(COALESCE(b_v, 0))            AS b_total,
  SUM(COALESCE(a_v, 0) - COALESCE(b_v, 0)) AS gap
FROM d
GROUP BY bucket
ORDER BY bucket;
```

If a value can be null on a matched key, `a.v = b.v` is not true and the key lands in `value_differs`, which is what you want; check those keys separately rather than letting a null hide inside a sum. Where the metric is a count rather than a sum, set `v` to 1 per key and the same query works.

## Checking the buckets add up

The `gap` column summed over all buckets must equal A's figure minus B's figure. If it does not, one side's keyed set does not reproduce its reported figure: go back to step 3.

## Cause 1: time zone and day boundary

Look at the hour of the event, in UTC, for keys that are only on one side:

```sql
SELECT bucket, EXTRACT(HOUR FROM event_ts_utc) AS hour_utc, COUNT(*) AS keys
FROM d_with_ts   -- the diff above, carrying event_ts_utc from either side
WHERE bucket IN ('only_a', 'only_b')
GROUP BY 1, 2
ORDER BY 1, 2;
```

Keys bunched in the few hours either side of the business time zone's midnight are a day-boundary difference. Test it by computing B's day in A's time zone and rerunning the diff. Converting a UTC timestamp to a local date:

| Dialect | Local date from a UTC timestamp |
| --- | --- |
| Snowflake | `CONVERT_TIMEZONE('UTC', 'Europe/London', created_at)::DATE` |
| BigQuery | `DATE(created_at, 'Europe/London')` |
| PostgreSQL, column `timestamp` holding UTC | `(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/London')::date` |
| PostgreSQL, column `timestamptz` | `(created_at AT TIME ZONE 'Europe/London')::date` |
| Redshift | `CONVERT_TIMEZONE('UTC', 'Europe/London', created_at)::date` |
| ClickHouse | `toDate(created_at, 'Europe/London')` |

Use a named zone, never a fixed offset: a fixed offset is wrong for half the year anywhere with daylight saving, and the gap it leaves appears only on the days either side of the change.

## Cause 2: snapshot time

Restrict A to source rows loaded before B was computed — B's extract time, or its query time from the log — using the loader's sync timestamp column. Apply the cutoff to the rows before they are summed, not to `side_a`: a key whose rows arrived partly before and partly after the snapshot would otherwise vanish whole, and its earlier rows with it. Rebuild A with the cutoff inside:

```sql
CREATE TEMPORARY TABLE side_a_at_b AS
SELECT
  o.order_id                AS k,
  SUM(o.amount)             AS v,
  MIN(o.created_at)         AS event_ts_utc,
  MAX(o._loaded_at)         AS loaded_at
FROM orders o
WHERE o.created_at >= '2026-10-07 00:00:00' AND o.created_at < '2026-10-08 00:00:00'
  AND o.country = 'GB'
  AND o._loaded_at <= TIMESTAMP '2026-10-08 06:00:00'
GROUP BY o.order_id;
```

Rerun the diff against `side_a_at_b`. Keys that leave `only_a` were late. Rows updated after B's snapshot (a refund applied, an amount corrected) show up as `value_differs`; where the table keeps no history, this is a cause you can bound but not prove, so say so. A difference of this kind is not a definition problem: both sides are right as of their time. The fix is labelling one figure as provisional until the data is mature, which `late-data-maturity` owns.

## Cause 3: filter and inclusion

For keys on one side only, profile the attributes filters usually act on, and look for one value covering most of them:

```sql
SELECT o.is_test_account, o.status, o.channel, COUNT(*) AS keys
FROM d
JOIN orders o ON o.order_id = d.k
WHERE d.bucket = 'only_a'
GROUP BY 1, 2, 3
ORDER BY keys DESC;
```

Common ones: test and internal accounts, staff purchases, refunded or cancelled orders, bot or crawler traffic, a channel or product one team excludes, orders with a zero amount. Apply B's filter to A, rerun, record the amount.

## Cause 4: dedupe rule

Matched keys with different values, or a count metric where one side counts events and the other counts distinct users or sessions. Compare the raw row count per key on each side for `value_differs` keys. Retried submissions, double-fired tracking events and replayed loads appear here. Apply one side's dedupe rule (by event id, by user per day, latest record wins) to the other.

## Cause 5: join grain

`value_differs` keys where one side's value is an exact multiple of the other's. That side joins to something that is not unique on its key. Reconcile it with `join-fanout-hunt` and come back with the corrected side.

## Cause 6: currency and units

`value_differs` keys where the ratio `a_v / b_v` is near-constant, or constant per currency:

```sql
SELECT o.currency, ROUND(AVG(a_v / NULLIF(b_v, 0)), 4) AS ratio, COUNT(*) AS keys
FROM d JOIN orders o ON o.order_id = d.k
WHERE d.bucket = 'value_differs'
GROUP BY 1;
```

A ratio of 100 is minor units against major; a ratio near a tax rate is gross against net; a ratio that varies slightly by day is an exchange rate taken at different times (transaction-day rate against month-end rate). Agree which conversion the metric uses and apply it to both.

## A worked reconciliation

Signups, 7 October, GB. A (growth dashboard, read 10:00) 12,480; B (finance report, extract 06:00) 12,115; gap 365.

| Step | Cause | Amount | Running figure | Keys moved |
| --- | --- | --- | --- | --- |
| | A as reported | | 12,480 | |
| 1 | A counts the UTC day, B the London day | -298 | 12,182 | 298 |
| 2 | 41 signups loaded after B's 06:00 extract | -41 | 12,141 | 41 |
| 3 | B excludes staff and test accounts | -87 | 12,054 | 87 |
| 4 | B counts a retried submission as a second signup; A keeps one | +61 | 12,115 | 58 |
| 5 | Join grain | 0 | 12,115 | 0 |
| 6 | Currency and units | not applicable to a count | 12,115 | 0 |
| | Residual | 0 | B: 12,115 | |

Each amount is the effect of applying B's rule for that one cause to A, so an amount can carry either sign: step 4 is positive because B's dedupe rule is the looser one, and 58 keys gain 61 extra signups between them. What must hold is that the running figure lands on B with the residual stated. Step 4 is also the first input to the definition decision: a rule that counts one person's retry as two signups is unlikely to be the one the business wants, whichever team owns it.
