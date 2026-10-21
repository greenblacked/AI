# Detection checks

## Contents

- Setup and conventions
- Schema diff for a semi-structured landing table
- Schema diff for a replicated table
- Enum drift
- Unit shift
- Time zone shift
- Key match rate
- Null rate
- Setting thresholds

## Setup and conventions

SQL is Snowflake. The landing table is `raw.orders_landing` with a `payload` `VARIANT` column, `batch_id` and `loaded_at`. The expected schema lives in `contracts.expected_fields (source, field, expected_type, required)`, loaded from the contract file in version control. `:batch_id` is the batch under test; the baseline is the trailing 30 days excluding it.

Each check returns rows only when something needs attention, so an orchestrator task can fail on a non-empty result.

## Schema diff for a semi-structured landing table

```sql
with observed as (
  select
    f.key as field,
    iff(typeof(f.value) in ('INTEGER', 'DECIMAL', 'DOUBLE'), 'NUMBER', typeof(f.value))
      as observed_type,
    count(*) as rows_with_field
  from raw.orders_landing r,
       lateral flatten(input => r.payload) f
  where r.batch_id = :batch_id
  group by 1, 2
),
expected as (
  select field, expected_type, required
  from contracts.expected_fields
  where source = 'orders'
)
select
  coalesce(o.field, e.field) as field,
  e.expected_type,
  o.observed_type,
  case
    when e.field is null                        then 'additive: new field'
    when o.field is null and e.required         then 'breaking: required field missing'
    when o.field is null                        then 'warn: optional field absent'
    when o.observed_type = 'NULL_VALUE'         then 'check: field present but null'
    when o.observed_type <> e.expected_type     then 'breaking: type changed'
  end as finding
from observed o
full outer join expected e on o.field = e.field
where finding is not null;
```

`TYPEOF` reports the type of each value (`INTEGER`, `DECIMAL`, `DOUBLE`, `VARCHAR`, `BOOLEAN`, `OBJECT`, `ARRAY`, `NULL_VALUE`). The query folds the three numeric types into `NUMBER`, because a producer's JSON serialiser writes `10` and `10.5` for the same field; record expected types in that folded vocabulary. A field seen both with a value and as `NULL_VALUE` in one batch returns two rows, which is correct: the null rows are worth a look. For nested objects, flatten with `recursive => true` and compare the `path` instead of the key.

## Schema diff for a replicated table

```sql
select column_name, data_type, is_nullable
from raw_db.information_schema.columns
where table_schema = 'APP' and table_name = 'ORDERS'
order by ordinal_position;
```

Store the result after each accepted change and compare each run with the stored copy, column by column, with the same additive and breaking classification. A rename shows as one column dropped and one added in the same run; treat that pair as breaking even though half of it looks additive.

## Enum drift

```sql
with batch as (
  select payload:status::string as status, count(*) as n
  from raw.orders_landing
  where batch_id = :batch_id
  group by 1
),
baseline_daily as (
  select
    loaded_at::date as d,
    payload:status::string as status,
    count(*) / sum(count(*)) over (partition by loaded_at::date) as share
  from raw.orders_landing
  where loaded_at >= dateadd('day', -30, current_timestamp())
    and batch_id <> :batch_id
  group by 1, 2
),
baseline as (
  select status, min(share) as min_share, max(share) as max_share, count(*) as days_seen
  from baseline_daily
  group by status
)
select
  coalesce(b.status, h.status) as status,
  b.n / sum(b.n) over () as batch_share,
  h.min_share, h.max_share, h.days_seen,
  case
    when h.status is null then 'new value'
    when b.status is null and h.days_seen >= 25 then 'value vanished'
    when b.n / sum(b.n) over () not between h.min_share and h.max_share then 'share outside 30-day range'
  end as finding
from batch b
full outer join baseline h on b.status = h.status
qualify finding is not null;
```

A new value is the strongest signal of a semantic change and should block until someone maps it. A vanished value is often a rename: look for a new value that appeared in the same batch. Small batches swing shares widely; compare shares only above a minimum batch size.

## Unit shift

```sql
with batch as (
  select median(payload:amount::number(38, 4)) as m
  from raw.orders_landing where batch_id = :batch_id
),
baseline as (
  select median(payload:amount::number(38, 4)) as m
  from raw.orders_landing
  where loaded_at >= dateadd('day', -30, current_timestamp()) and batch_id <> :batch_id
)
select b.m as batch_median, h.m as baseline_median, b.m / nullif(h.m, 0) as ratio
from batch b, baseline h
where b.m / nullif(h.m, 0) not between 0.2 and 5;
```

Run it per currency and per product line, because a mix shift moves a blended median. A ratio near 100, 1000 or their reciprocals is a unit change; anything else outside the band needs a person to look. Adjust the band to the field's own variation.

## Time zone shift

```sql
with hours as (
  select
    iff(batch_id = :batch_id, 'batch', 'baseline') as side,
    hour(payload:created_at::timestamp_ntz) as h,
    count(*) as n
  from raw.orders_landing
  where loaded_at >= dateadd('day', -30, current_timestamp())
  group by 1, 2
)
select side, h, n / sum(n) over (partition by side) as share
from hours
order by side, h;
```

Compare the two hourly profiles. A whole profile displaced by one or more hours, with the same shape, is a time zone or daylight-saving handling change in the producer. Check the payload for an offset suffix that appeared or disappeared at the same time.

## Key match rate

```sql
select
  count(*) as rows_in_batch,
  count_if(c.customer_id is null) as unmatched,
  count_if(c.customer_id is null) / count(*) as unmatched_share
from staging.orders s
left join core.customer c on c.customer_id = s.customer_id
where s.batch_id = :batch_id
having count_if(c.customer_id is null) / count(*) > :max_unmatched_share;
```

Set `:max_unmatched_share` from history; some unmatched rows are normal when the dimension loads later. A step change is a re-keyed, prefixed or recycled id. Late-arriving dimension rows look the same for a few hours, so re-run before escalating if the dimension loads on a different schedule.

## Null rate

```sql
select
  count_if(payload:customer_id is null or is_null_value(payload:customer_id)) / count(*) as null_share
from raw.orders_landing
where batch_id = :batch_id
having null_share > :max_null_share;
```

`payload:field is null` is true when the key is absent; `is_null_value` is true when the key is present with a JSON null. Producers changing one into the other is itself a change worth flagging.

## Setting thresholds

Derive each threshold from the trailing baseline's own spread, not from a round number, and keep a month end inside the window. Give each check an action (block publish, warn, log) and an owner. The general method for thresholds, actions and pruning checks nobody acts on belongs to `data-quality-checks`; this file covers only the checks aimed at upstream change.
