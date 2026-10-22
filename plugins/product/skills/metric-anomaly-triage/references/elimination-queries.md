# Elimination queries

## Contents

- Conventions
- Baseline: how unusual is the move
- 1\. Tracking or tag change
- 2\. Pipeline lag or late data
- 3\. Definition or filter change
- 4\. Bot or internal traffic
- 5\. Mix shift
- 6\. Seasonality or calendar
- Locating a real change
- Recording the result

## Conventions

The sketches are written in PostgreSQL. Other warehouses differ in date functions,
interval syntax and regular-expression operators; on BigQuery, for example,
`date_trunc('hour', ts)` becomes `TIMESTAMP_TRUNC(ts, HOUR)`, `interval '7 days'`
becomes `INTERVAL 7 DAY` and `~*` (case-insensitive) becomes
`REGEXP_CONTAINS(user_agent, r'(?i)pattern')`, because `REGEXP_CONTAINS` alone is case-sensitive. Table and
column names are placeholders: `events(event_name, user_id, ts, platform, app_version,
lib_version, user_agent, country, channel, plan)`, `accounts(account_id, created_at,
is_internal, is_test)` and a load-metadata table `loads(table_name, partition_date,
loaded_at, row_count)`. Adapt them to your warehouse; keep the shape of the question.

`:start` is the hour the move began. Every query compares a window after it against the
same window one week earlier, so weekday effects cancel. `:end` is the end of the after
window: `:start` plus seven days, or the latest fully loaded hour if that is sooner. The
after window is `[:start, :end)` and the before window is that same window shifted back
seven days, `[:start - 7 days, :end - 7 days)`, so a move that began on Monday is
compared Monday and Tuesday against the previous Monday and Tuesday. The two windows have
equal length and the same weekdays; comparing two days of counts against seven would show
a "drop" that is only a shorter window.

## Baseline: how unusual is the move

```sql
-- Daily value of the metric's source event on the same weekday for the last 8 weeks.
select date_trunc('day', ts) as day, count(*) as n
from events
where event_name = 'signup_completed'
  and ts >= :start - interval '56 days'
  and extract(dow from ts) = extract(dow from :start::timestamp)
group by 1
order by 1;
```

Days with no events return no row, so a missing weekday is a zero; count the rows before
reading the range. Read the spread. If the new value is inside the range of the last eight same weekdays,
say so and stop calling it an anomaly.

## 1. Tracking or tag change

```sql
select date_trunc('hour', ts) as hour, platform, app_version, lib_version, count(*) as n
from events
where event_name = 'signup_completed'
  and ts between :start - interval '2 days' and :start + interval '1 day'
group by 1, 2, 3, 4
order by 1, 2, 3, 4;
```

It is the cause when the drop is confined to one platform or version, begins when a
version starts to roll out, or a property the metric filters on starts arriving null or
renamed. Check the release log and the tag manager's publish history for the same hour.
Also check whether the event moved from client-side to server-side (or back), which
changes ad-blocker loss overnight.

## 2. Pipeline lag or late data

```sql
select partition_date, loaded_at, row_count
from loads
where table_name = 'events'
  and partition_date >= current_date - 14
order by partition_date, loaded_at;
```

Compare the latest days' row counts to the same weekday a week before, and check the
newest `loaded_at`. It is the cause when recent partitions are short and fill in over
the following hours, or a scheduled job failed or ran late. Re-run the metric after the
next load and see whether the dip moves.

## 3. Definition or filter change

There is no single query. Diff these against their state before `:start`:

- the dashboard's query or semantic-layer definition (most BI tools keep a version
  history);
- the transformation model that feeds it (the repository history for that model);
- any filter, status list, deduplication key, join or timezone setting;
- any upstream source column whose meaning changed (for example a status value split
  into two).

Then compute the metric both ways over the same window. It is the cause when the old
definition shows no move.

## 4. Bot or internal traffic

```sql
select
  case
    when a.is_internal or a.is_test then 'internal_or_test'
    when e.user_agent ~* '(bot|crawler|spider|headless)' then 'bot_ua'
    else 'other'
  end as traffic_class,
  date_trunc('day', e.ts) as day,
  count(*) as n,
  count(distinct e.user_id) as users
from events e
left join accounts a on a.account_id = e.user_id
where e.event_name = 'signup_completed'
  and e.ts between :start - interval '7 days' and :start + interval '1 day'
group by 1, 2
order by 2, 1;
```

User-agent matching catches only declared bots. Also look for a small number of IP
ranges, networks or accounts producing a large share of events, and for sessions that
complete a flow faster than a person can. A spike is often bots; a drop can be a new bot
filter, or a load test that ended.

## 5. Mix shift

```sql
with seg as (
  select channel,
         case when ts >= :start then 'after' else 'before' end as period,
         sum(case when event_name = 'signup_started'   then 1 else 0 end) as started,
         sum(case when event_name = 'signup_completed' then 1 else 0 end) as completed
  from events
  where (ts >= :start and ts < :end)
     or (ts >= :start - interval '7 days' and ts < :end - interval '7 days')
  group by 1, 2
)
select channel, period, started, completed,
       completed::numeric / nullif(started, 0) as rate,
       started::numeric / nullif(sum(started) over (partition by period), 0) as share
from seg
order by channel, period;
```

It is mix shift when each segment's `rate` is steady but `share` moved towards a
lower-rate segment. Repeat for country, platform and plan. Mix shift is not a
measurement error, but it is not a change in how any group behaves either; report it
as a change in who arrived.

## 6. Seasonality or calendar

Align the window with the same weekdays one week, four weeks and 52 weeks earlier
(364 days keeps the weekday). Mark on the same chart: public holidays in the main
markets, month and quarter ends, billing and payroll dates, school holidays where they
matter, the start and end of paid campaigns, and app-store featuring. It is the cause
when last year shows the same shape on the aligned dates.

## Locating a real change

Once steps 1 to 6 are cleared:

```sql
-- Which segment carries the move: contribution of each segment to the change.
with w as (
  select country,
         sum(case when ts <  :end - interval '7 days' then 1 else 0 end) as before_n,
         sum(case when ts >= :start then 1 else 0 end) as after_n
  from events
  where event_name = 'signup_completed'
    and ((ts >= :start and ts < :end)
      or (ts >= :start - interval '7 days' and ts < :end - interval '7 days'))
  group by 1
)
select country, before_n, after_n, after_n - before_n as delta,
       (after_n - before_n)::numeric / nullif(sum(after_n - before_n) over (), 0) as share_of_move
from w
order by abs(after_n - before_n) desc;
```

`share_of_move` is only meaningful when the segments move the same way: if one country
rose and another fell, the total delta is small and the shares blow up past 100%. In
that case read `delta` alone. Then repeat by funnel step to find where the move first appears, and confirm the
segment's change in a table outside the analytics pipeline (production accounts,
payments, the email or app-store console).

## Recording the result

| # | Cause | Query run (link) | Result | Cleared | Share of move explained |
| --- | --- | --- | --- | --- | --- |
| 1 | Tracking or tag change | | | yes / no | |
| 2 | Pipeline lag | | | | |
| 3 | Definition or filter | | | | |
| 4 | Bot or internal | | | | |
| 5 | Mix shift | | | | |
| 6 | Seasonality or calendar | | | | |
