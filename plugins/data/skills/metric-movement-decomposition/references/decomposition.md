# Rate and mix decomposition

## Contents

- Data-break checks as queries
- Why the decomposition is exact
- SQL template
- New and vanished segments
- Worked example: both segments improve, the total falls
- Reading the result

## Data-break checks as queries

Run these over the two periods plus the eight weeks before them. Replace `sessions` and `orders` with the metric's denominator and numerator sources.

Daily volumes, to see a step change in either side:

```sql
WITH order_counts AS (
  SELECT session_id, COUNT(*) AS orders
  FROM orders
  GROUP BY session_id
),
-- a calendar spine, so a day with no sessions at all shows as zero
days AS (
  SELECT date_day AS day
  FROM dim_date
  WHERE date_day >= DATE '2026-08-10' AND date_day < CURRENT_DATE
)
SELECT
  d.day,
  COUNT(s.session_id)            AS denominator,
  COALESCE(SUM(o.orders), 0)     AS numerator
FROM days d
LEFT JOIN sessions s ON CAST(s.session_start AS DATE) = d.day
LEFT JOIN order_counts o ON o.session_id = s.session_id
GROUP BY 1
ORDER BY 1;
```

Orders are aggregated to one row per session before the join. Joining raw orders would repeat a session once per order and inflate the denominator along with the numerator, so a tracking break could look like a real movement.

Unknown share per segmentation column, per day:

```sql
SELECT
  CAST(session_start AS DATE) AS day,
  AVG(CASE WHEN device_type IS NULL OR device_type IN ('', 'unknown') THEN 1.0 ELSE 0.0 END) AS unknown_device_share,
  AVG(CASE WHEN channel     IS NULL OR channel     IN ('', 'unknown') THEN 1.0 ELSE 0.0 END) AS unknown_channel_share
FROM sessions
WHERE session_start >= DATE '2026-08-10'
GROUP BY 1
ORDER BY 1;
```

Share of the denominator by app or site version, per day, to line a step change up with a release:

```sql
SELECT CAST(session_start AS DATE) AS day, app_version, COUNT(*) AS sessions
FROM sessions
WHERE session_start >= DATE '2026-09-28'
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

A rate that collapses only on sessions from one new version, starting on its release day, is a tracking or product change in that version. Hand that finding over with the version and the date; it is not a mix question.

## Why the decomposition is exact

Write the aggregate rate as R = Σ wᵢ rᵢ, with wᵢ the segment's share of the denominator and rᵢ its rate. For two periods, for each segment:

w₁r₁ − w₀r₀ = (r₁ − r₀)(w₀ + w₁)/2 + (w₁ − w₀)(r₀ + r₁)/2

Expanding the right-hand side gives the left exactly, so summing over segments gives R₁ − R₀ with no interaction term. That is the symmetric form Kitagawa published in 1955; the asymmetric forms (weighting by period 0 only, or period 1 only) leave an interaction term that someone then has to allocate by hand.

Because Σ(w₁ − w₀) = 0, any constant can be subtracted from the mix weight without changing the total. Subtracting R̄ = (R₀ + R₁)/2 makes each segment's mix effect say whether share moved towards an above-average or a below-average segment, which is the question a reader is asking.

## SQL template

Start from a table with one row per segment per period, carrying the numerator and denominator totals:

```sql
WITH seg AS (
  SELECT
    segment,
    SUM(CASE WHEN period = 0 THEN num ELSE 0 END) * 1.0 AS n0,
    SUM(CASE WHEN period = 0 THEN den ELSE 0 END) * 1.0 AS d0,
    SUM(CASE WHEN period = 1 THEN num ELSE 0 END) * 1.0 AS n1,
    SUM(CASE WHEN period = 1 THEN den ELSE 0 END) * 1.0 AS d1
  FROM by_segment_period
  GROUP BY segment
),
tot AS (
  SELECT SUM(n0) AS tn0, SUM(d0) AS td0, SUM(n1) AS tn1, SUM(d1) AS td1 FROM seg
),
s AS (
  SELECT
    seg.segment,
    seg.d0 / tot.td0              AS w0,
    seg.d1 / tot.td1              AS w1,
    seg.n0 / NULLIF(seg.d0, 0)    AS r0_raw,
    seg.n1 / NULLIF(seg.d1, 0)    AS r1_raw,
    tot.tn0 / tot.td0             AS agg0,
    tot.tn1 / tot.td1             AS agg1
  FROM seg CROSS JOIN tot
),
e AS (
  SELECT
    segment, w0, w1, agg0, agg1,
    COALESCE(r0_raw, r1_raw) AS r0,
    COALESCE(r1_raw, r0_raw) AS r1
  FROM s
)
SELECT
  segment, w0, w1, r0, r1,
  (r1 - r0) * (w0 + w1) / 2                          AS rate_effect,
  (w1 - w0) * ((r0 + r1) / 2 - (agg0 + agg1) / 2)    AS mix_effect,
  (r1 - r0) * (w0 + w1) / 2
    + (w1 - w0) * ((r0 + r1) / 2 - (agg0 + agg1) / 2) AS total_effect,
  agg1 - agg0                                        AS aggregate_change
FROM e
ORDER BY ABS(total_effect) DESC;
```

Sum `total_effect` over all rows and compare with `aggregate_change`. They must agree to rounding. The Simpson counterfactual is `SUM(w0 * r1)` over the same rows, compared with `agg0`.

## New and vanished segments

A segment with no denominator in one period has no rate there. The template copies the other period's rate across (the `COALESCE` pair), which sets its rate effect to zero and puts its whole contribution into mix — the right reading, since a segment that did not exist cannot have changed its rate. A large contribution from a new segment usually means a new channel, country or app version appeared; name it as such.

## Worked example: both segments improve, the total falls

Conversion, orders over sessions, two comparable weeks.

| Segment | Sessions wk0 | Orders wk0 | Sessions wk1 | Orders wk1 |
| --- | --- | --- | --- | --- |
| Desktop | 60,000 | 3,000 | 45,000 | 2,295 |
| Mobile | 40,000 | 800 | 55,000 | 1,155 |
| Total | 100,000 | 3,800 | 100,000 | 3,450 |

Aggregate conversion went from 3.80% to 3.45%: down 0.35 points, 9.2% relative. Shares and rates:

| Segment | w0 | w1 | r0 | r1 |
| --- | --- | --- | --- | --- |
| Desktop | 0.60 | 0.45 | 5.0% | 5.1% |
| Mobile | 0.40 | 0.55 | 2.0% | 2.1% |

With R̄ = (3.80 + 3.45) / 2 = 3.625%:

| Segment | Rate effect | Mix effect | Total | Share of change |
| --- | --- | --- | --- | --- |
| Desktop | +0.10 × 0.525 = +0.0525 pts | −0.15 × (5.05 − 3.625) = −0.2138 pts | −0.1613 pts | 46% |
| Mobile | +0.10 × 0.475 = +0.0475 pts | +0.15 × (2.05 − 3.625) = −0.2363 pts | −0.1888 pts | 54% |
| Sum | +0.10 pts | −0.45 pts | −0.35 pts | 100% |

Simpson check: week 1's rates at week 0's mix give 0.60 × 5.1% + 0.40 × 2.1% = 3.90%, above week 0's 3.80%. Both segments converted better; the whole fall is traffic moving from desktop to mobile. The report's first sentence is "Conversion fell 0.35 points because 15 points of traffic moved from desktop to mobile; conversion within both devices rose 0.1 points" — and the next question is about acquisition, not checkout.

## Reading the result

| Pattern | Reading | Next question |
| --- | --- | --- |
| Rate effect concentrated in one segment | Something changed for that segment | Drill one level inside it; check releases touching it |
| Rate effects small and the same sign everywhere | A broad change: pricing, seasonality, a site-wide release | Compare with the same weeks last year |
| Mix effect dominant | Traffic composition changed | Which source sent more or less of which segment |
| Rate and mix pulling in opposite directions | The headline understates both | Report both, not only the net |
| Largest contributor is "unknown" or "other" | The segmentation is hiding the answer | Fix the unknown share or split "other" before concluding |
