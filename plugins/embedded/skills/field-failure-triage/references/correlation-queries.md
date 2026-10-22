# Correlation queries

## Contents

- Principle
- Last-seen distribution
- Rate by dimension
- Age at failure
- Small samples

## Principle

Rate is failures in a bucket divided by units in the field in that bucket over the same period. Both come from the same population definition. A bucket with no units in the field has no rate. Run one dimension at a time, then cross the two that separate failures.

## Last-seen distribution

Define silent from the fleet's check-in interval, for example two missed intervals, and pass it as the parameter; a fixed 24 hours hides a cohort that went quiet overnight until the next day.

Given a table `devices(id, last_seen, firmware, hw_rev, lot, line, carrier, region, shipped_at, failed, failed_at)`, the count of silent units per hour of last contact shows a step or a slope:

```sql
SELECT date_trunc('hour', last_seen) AS hour, count(*) AS units
FROM devices
WHERE last_seen < now() - :silent_after  -- for example two missed check-in intervals
GROUP BY 1
ORDER BY 1;
```

A spike in one hour is a step. Then read the broker, authentication and DNS logs for that hour. If the units are silent by lot or carrier, group by that column in the same query.

## Rate by dimension

```sql
SELECT firmware,
       count(*) FILTER (WHERE failed) AS failed,
       count(*)                       AS in_field,
       round(100.0 * count(*) FILTER (WHERE failed) / count(*), 2) AS pct
FROM devices
WHERE shipped_at < now() - interval '30 days'
GROUP BY firmware
ORDER BY pct DESC;
```

Repeat with `hw_rev`, `lot`, `line`, `carrier` and `region` in place of `firmware`. Restrict to units old enough to have had a chance to fail, as above, so a recent lot is not flattered by its short exposure. To cross two dimensions, group by both and read each cell's own rate.

## Age at failure

```sql
SELECT width_bucket(extract(epoch FROM (failed_at - shipped_at)) / 86400, 0, 365, 26) AS bucket,
       count(*) AS failures
FROM devices
WHERE failed
GROUP BY 1
ORDER BY 1;
```

An early spike is a batch defect, a flat shape a design or random cause, a climbing tail wear-out. Compare it against units still working in the same bucket by dividing by the units that reached that age, otherwise a young lot looks better only because it has not aged.

## Small samples

With a handful of failures a rate is noise. Report the counts beside the percentage, widen the bucket until it holds enough units to mean something, and avoid declaring a cause from a bucket with a few failures. State the sample size in the conclusion.
