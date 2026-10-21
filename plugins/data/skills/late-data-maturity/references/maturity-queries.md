# Maturity queries

## Contents

- The arrivals view
- The maturity curve
- Summary across days
- The same curve in BigQuery
- From a metric log
- Equal-age comparison
- Incremental logic that keeps late rows

The queries are written for Snowflake and assume an `orders` source with an event timestamp and a first-load timestamp, both stored as UTC in `TIMESTAMP_NTZ` columns, and a reporting time zone of `Europe/London`. Replace the names; keep the shape.

## The arrivals view

Assign each row to a reporting day in the reporting time zone, and express the day's close as a UTC instant beside the UTC load time. Lags are measured between UTC instants: subtracting two local wall-clock values counts the 23- and 25-hour days at a clock change as 24 hours and puts rows in the wrong age bucket.

```sql
create or replace view analytics.stg_order_arrivals as
select
  order_id,
  source_system,
  amount,
  convert_timezone('UTC', 'Europe/London', event_ts_utc)::date as event_day,
  convert_timezone('Europe/London', 'UTC',
    dateadd('day', 1, convert_timezone('UTC', 'Europe/London', event_ts_utc)::date)::timestamp_ntz)
    as day_close_utc,
  first_loaded_at_utc as loaded_utc
from raw.orders;
```

A row loaded before its day closed has a negative lag and counts as present at every age, which is correct.

## The maturity curve

One row per event day and source. Restrict to days old enough that their totals no longer move; 30 days is a starting point, and the right floor is the longest lag the data shows.

```sql
with lagged as (
  select
    event_day,
    source_system,
    amount,
    datediff('minute', day_close_utc, loaded_utc) as lag_min
  from analytics.stg_order_arrivals
  where event_day >= dateadd('day', -120, current_date)
    and event_day <  dateadd('day', -30, current_date)
)
select
  event_day,
  source_system,
  count(*)                                                 as eventual_rows,
  count_if(lag_min <=    60) / count(*)                    as rows_1h,
  count_if(lag_min <=   360) / count(*)                    as rows_6h,
  count_if(lag_min <=  1440) / count(*)                    as rows_24h,
  count_if(lag_min <=  4320) / count(*)                    as rows_72h,
  count_if(lag_min <= 10080) / count(*)                    as rows_7d,
  sum(iff(lag_min <=  1440, amount, 0)) / nullif(sum(amount), 0) as value_24h,
  sum(iff(lag_min <=  4320, amount, 0)) / nullif(sum(amount), 0) as value_72h
from lagged
group by event_day, source_system
order by event_day, source_system;
```

Add value columns for every age you report. When rows are updated after load, this curve undercounts lateness; build the value curve from the metric log instead (below).

## Summary across days

The publish decision reads the bad days, so summarise with a low percentile beside the median.

```sql
with curve as ( /* the query above */ )
select
  source_system,
  dayname(event_day) as weekday,
  median(rows_24h)                                        as rows_24h_median,
  percentile_cont(0.05) within group (order by rows_24h)  as rows_24h_p05,
  percentile_cont(0.05) within group (order by value_24h) as value_24h_p05,
  percentile_cont(0.05) within group (order by rows_72h)  as rows_72h_p05,
  min(rows_24h)                                           as rows_24h_worst
from curve
group by source_system, weekday
order by source_system, weekday;
```

`rows_24h_p05` is the completeness 95% of days reach by 24 hours. Publish at the first age whose `p05` meets the agreed threshold. Drop the weekday grouping once you have checked it makes no difference.

## The same curve in BigQuery

```sql
with lagged as (
  select
    source_system,
    amount,
    date(event_ts, 'Europe/London') as event_day,
    timestamp_diff(
      first_loaded_at,
      timestamp(date_add(date(event_ts, 'Europe/London'), interval 1 day), 'Europe/London'),
      minute) as lag_min
  from raw.orders
  where date(event_ts, 'Europe/London')
        between date_sub(current_date('Europe/London'), interval 120 day)
            and date_sub(current_date('Europe/London'), interval 31 day)
)
select
  event_day,
  source_system,
  count(*) as eventual_rows,
  safe_divide(countif(lag_min <= 1440), count(*)) as rows_24h,
  safe_divide(sum(if(lag_min <= 1440, amount, 0)), sum(amount)) as value_24h
from lagged
group by event_day, source_system;
```

For the summary, `approx_quantiles(rows_24h, 100)[offset(5)]` gives the fifth percentile.

## From a metric log

When the figure is assembled from many tables or rows are updated after load, log each computed value and build the curve from the log:

```sql
-- metric_log: metric, period_day, segment, computed_at_utc, value
with final as (
  select metric, period_day, segment, value as final_value
  from metric_log
  qualify row_number() over (
    partition by metric, period_day, segment order by computed_at_utc desc) = 1
),
aged as (
  select
    l.metric, l.period_day, l.segment, l.value,
    datediff('minute',
      convert_timezone('Europe/London', 'UTC', dateadd('day', 1, l.period_day)::timestamp_ntz),
      l.computed_at_utc) as age_min
  from metric_log l
)
select
  a.metric, a.period_day, a.segment,
  max(iff(a.age_min <= 1440, a.value, null)) / nullif(f.final_value, 0) as share_24h
from aged a
join final f using (metric, period_day, segment)
where a.period_day < dateadd('day', -30, current_date)
group by a.metric, a.period_day, a.segment, f.final_value;
```

`max` takes the latest value at or before 24 hours only when the figure grows monotonically; when it can fall (refunds), take the value from the last computation at or before the age instead.

## Equal-age comparison

Compare yesterday as it stands now with the same weekday last week as it stood the same number of minutes after it closed.

```sql
with now_utc as (
  select sysdate() as ts  -- the current instant in UTC, as TIMESTAMP_NTZ
),
today as (
  select ts, convert_timezone('UTC', 'Europe/London', ts)::date as today_local
  from now_utc
),
age as (
  select
    today_local,
    datediff('minute',
      convert_timezone('Europe/London', 'UTC', today_local::timestamp_ntz), ts) as age_min
  from today
)
select
  a.event_day,
  count_if(a.loaded_utc <= dateadd('minute', g.age_min, a.day_close_utc)) as rows_at_same_age,
  sum(iff(a.loaded_utc <= dateadd('minute', g.age_min, a.day_close_utc), a.amount, 0))
    as value_at_same_age
from analytics.stg_order_arrivals a
cross join age g
where a.event_day in (dateadd('day', -1, g.today_local), dateadd('day', -8, g.today_local))
group by a.event_day;
```

## Incremental logic that keeps late rows

The defect: an incremental model that selects `event_ts > (select max(event_ts) from {{ this }})`. A row that arrives today for last Tuesday has an event time behind the high-water mark and is never selected.

Select new rows by load time and rebuild every day they touch (dbt):

```sql
{{ config(materialized='incremental', unique_key=['event_day', 'source_system']) }}

with new_rows as (
  select event_day
  from {{ ref('stg_order_arrivals') }}
  {% if is_incremental() %}
  where loaded_utc > (select max(max_loaded_utc) from {{ this }})
  {% endif %}
),
touched as (
  select distinct event_day from new_rows
)
select
  a.event_day,
  a.source_system,
  count(*)            as orders,
  sum(a.amount)       as revenue,
  max(a.loaded_utc)   as max_loaded_utc
from {{ ref('stg_order_arrivals') }} a
{% if is_incremental() %}
where a.event_day in (select event_day from touched)
{% endif %}
group by a.event_day, a.source_system
```

This relies on a load writing all of its rows with timestamps after the previous load's maximum; if two loads can overlap, select by a load batch id recorded on each row instead.

The simpler alternative re-processes a fixed lookback: `where event_day >= dateadd('day', -7, current_date)` on every run. It is correct only while the lookback is at least the restatement window, so derive one from the other and write both down in the same place.
