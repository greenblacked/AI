# Activation queries

## Contents

- Conventions
- Cohort retention curves
- Scoring candidate actions
- Out-of-sample check
- A worked candidate table
- Drop-off record

## Conventions

PostgreSQL. Placeholder tables: `users(user_id, signed_up_at, is_internal)` and
`events(user_id, event_name, ts)`. `core_action` is the action chosen in step 1 as real
use. Week 1 is days 0 to 6 after sign-up, so week 8 is days 49 to 55. Exclude internal
and test users (write the filter as `is_internal is not true`: `not is_internal` also drops users
whose flag is null, silently shrinking the cohort), and exclude cohorts too young to have reached the last week you plot or
score: 56 days for week 8, 84 days for week 12.

## Cohort retention curves

```sql
with cohort as (
  select user_id, date_trunc('week', signed_up_at) as cohort_week, signed_up_at
  from users
  where is_internal is not true
    and signed_up_at < current_date - interval '84 days'
),
activity as (
  select distinct c.user_id,
         floor(extract(epoch from (e.ts - c.signed_up_at)) / 604800)::int + 1 as week_n
  from cohort c
  join events e on e.user_id = c.user_id
  where e.event_name = 'core_action'
    and e.ts >= c.signed_up_at
)
select c.cohort_week,
       w.week_n,
       count(distinct a.user_id)::numeric / count(distinct c.user_id) as retained_share
from cohort c
cross join generate_series(1, 12) as w(week_n)
left join activity a on a.user_id = c.user_id and a.week_n = w.week_n
group by 1, 2
order by 1, 2;
```

The week series is generated rather than taken from the activity rows, so a week in
which nobody in a cohort was active returns 0. Joining straight to the activity rows
drops that week instead, and a curve that falls to zero then looks like one with gaps.

The cohort-age filter and the plotted horizon must match: 84 days for week 12. If you
shorten the filter to admit younger cohorts, leave the weeks a cohort has not reached
blank rather than zero, or the chart draws a cliff at the cohort's age that looks like a
curve that never flattens.

Plot one line per cohort. Flattening means the week-to-week loss approaches zero while
the share stays above zero. Write down the week where it flattens and the level.

## Scoring candidate actions

```sql
with base as (
  select u.user_id, u.signed_up_at
  from users u
  where u.is_internal is not true
    and u.signed_up_at between :train_from and :train_to
    and u.signed_up_at < current_date - interval '56 days'
),
retained as (
  select distinct b.user_id
  from base b
  join events e on e.user_id = b.user_id
  where e.event_name = 'core_action'
    and e.ts >= b.signed_up_at + interval '49 days'
    and e.ts <  b.signed_up_at + interval '56 days'
),
early as (
  select b.user_id, e.event_name, count(*) as n
  from base b
  join events e on e.user_id = b.user_id
  where e.ts >= b.signed_up_at
    and e.ts <  b.signed_up_at + interval '7 days'
    and e.event_name in ('created_project', 'connected_source', 'invited_member', 'exported_report')
  group by 1, 2
),
flags as (
  select b.user_id, c.event_name, k.threshold,
         coalesce(early.n, 0) >= k.threshold as did_it,
         r.user_id is not null as is_retained
  from base b
  cross join (select distinct event_name from early) c
  cross join (values (1), (3)) as k(threshold)
  left join early on early.user_id = b.user_id and early.event_name = c.event_name
  left join retained r on r.user_id = b.user_id
)
select event_name, threshold,
       avg(case when did_it then is_retained::int end)     as retention_if_did,
       avg(case when not did_it then is_retained::int end) as retention_if_not,
       avg(case when is_retained then did_it::int end)     as share_of_retained_who_did,
       avg(did_it::int)                                    as share_of_all_who_did
from flags
group by 1, 2
order by avg(case when did_it then is_retained::int end)
       - avg(case when not did_it then is_retained::int end) desc nulls last;
```

The ordering repeats the two averages because PostgreSQL does not accept output column
aliases inside an `order by` expression. `nulls last` matters: a threshold that every
user met, or none did, has no comparison group, its gap is null, and PostgreSQL sorts
nulls first in a descending order, which would put the least informative rows at the
top.

Add a threshold for "on two separate days" by counting distinct dates instead of
events. Keep the early window and the retention window fixed across candidates, or the
comparison is between different questions.

## Out-of-sample check

Choose the winner on `:train_from` to `:train_to`, then run the same query on later
cohorts it was not chosen on. Keep a candidate only if its ordering and its retention
gap hold. A winner that loses its lead out of sample was fitted to noise.

## A worked candidate table

| Action, threshold, first 7 days | Retained if did | Retained if not | Share of retained who did | Share of all who did |
| --- | --- | --- | --- | --- |
| Connected a data source, 1 | 41% | 5% | 78% | 30% |
| Invited a member, 1 | 52% | 13% | 26% | 8% |
| Created a project, 1 | 20% | 5% | 92% | 74% |
| Exported a report, 3 | 48% | 14% | 15% | 5% |

The rows describe one cohort whose overall week-8 retention is about 16%, and each row
reconciles to it within rounding: overall = retained if did × share who did + retained
if not × (1 − share who did), and share of retained who did = retained if did × share
who did ÷ overall. Run the same check on your own table; a row that does not reconcile
has a filter or window that differs from the others.

Reading it: "Invited a member" separates most strongly but covers under a third of
retained users, so it describes a power-user segment. "Created a project" covers almost
everyone, including most who leave, so it separates weakly. "Connected a data source"
separates strongly and covers most retained users while under a third of new users
reach it, which leaves room to move it. It is the candidate to take into a nudge test.
These figures are illustrative; your own table decides.

## Drop-off record

| Step | Users reaching | Users lost | Retention gap, passed vs stopped | Tracking check | Hypothesis | Test |
| --- | --- | --- | --- | --- | --- | --- |
| Connect source | | | | Server-side count matches: yes / no | Users stop because ...; if so, ... | |
