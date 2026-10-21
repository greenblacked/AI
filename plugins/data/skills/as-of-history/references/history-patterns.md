# History patterns

## Contents

- Periodic snapshot
- Type-2 dimension
- dbt snapshots: what they do and do not record
- Append-only change log
- Bitemporal table
- As-of joins
- Integrity checks
- Warehouse time travel

SQL is written for Snowflake; the shapes carry to any warehouse. Names are illustrative.

## Periodic snapshot

One full copy of the entity per period, keyed by `(snapshot_date, entity_id)`.

```sql
insert into history.customer_daily
select current_date as snapshot_date, c.*
from core.customer c;
```

Answers "what did the table say at the end of day D" with `where snapshot_date = D`. Cheap to explain and to query; storage grows with entities times days, and any change that happens and reverts between two snapshots is invisible. Make the load idempotent per `snapshot_date` (delete then insert, or `MERGE`), because a re-run that appends a second copy doubles every count for that day.

## Type-2 dimension

One row per version of the entity: `entity_id`, attributes, `valid_from`, `valid_to`, and a surrogate key per version. The open version has `valid_to = '9999-12-31'`.

Close and open versions in one transaction so no reader sees two open rows or none. The source of `valid_from` decides what the table means: the source's own effective date gives validity, the load time gives state as the warehouse saw it. Pick one per table and name it in the column description.

## dbt snapshots: what they do and do not record

- With the `timestamp` strategy, `dbt_valid_from` is the source's `updated_at`; with the `check` strategy it is the time the snapshot ran. The first is validity as the source reports it, the second is state as the warehouse saw it.
- A snapshot records only what differs between two runs. A value that changes and changes back between runs leaves no trace; run frequency is the resolution of the history.
- The open version has a null `dbt_valid_to` by default. dbt 1.9 added `dbt_valid_to_current` to write a sentinel instead; with the default, coalesce in every join.
- Rows hard-deleted in the source are ignored by default and stay open forever. Configure the snapshot to invalidate them (`invalidate_hard_deletes` in older versions, `hard_deletes` from 1.9).
- A snapshot is a type-2 table with one time axis. It cannot record that a value was later corrected for an earlier period; that needs the bitemporal layout below.

## Append-only change log

One row per change event: `entity_id`, operation, the new values (and old values if the source supplies them), the source commit or change time, and the warehouse load time. Never update or delete it. Every other layout can be rebuilt from it, which is why it is worth capturing even when nobody queries it directly.

Rebuild a type-2 dimension from it:

```sql
select
  entity_id,
  plan,
  changed_at as valid_from,
  coalesce(
    lead(changed_at) over (partition by entity_id order by changed_at, change_seq),
    '9999-12-31'::timestamp_ntz) as valid_to
from history.customer_changes
where operation in ('insert', 'update');
```

Order ties by a source sequence number (`change_seq`, a log position), not by load time.

## Bitemporal table

```sql
create table history.customer_plan (
  customer_id    number        not null,
  plan           varchar       not null,
  valid_from     timestamp_ntz not null,  -- true in the world from
  valid_to       timestamp_ntz not null,  -- '9999-12-31' when still true
  recorded_from  timestamp_ntz not null,  -- warehouse believed this from
  recorded_to    timestamp_ntz not null,  -- '9999-12-31' while still believed
  history_source varchar       not null   -- 'captured' or 'inferred:<method>'
);
```

A backdated correction, learned at time `:now`, saying customer 42 has been on `enterprise` since 1 March and still is:

```sql
-- 1. stop believing the rows the correction contradicts
update history.customer_plan
set recorded_to = :now
where customer_id = 42
  and recorded_to = '9999-12-31'
  and valid_to > '2026-03-01';

-- 2. re-insert the unchanged part of the old belief, now known again from :now
insert into history.customer_plan
select customer_id, plan, valid_from, '2026-03-01', :now, '9999-12-31', history_source
from history.customer_plan
where customer_id = 42
  and recorded_to = :now
  and valid_from < '2026-03-01';

-- 3. insert the corrected fact
insert into history.customer_plan
values (42, 'enterprise', '2026-03-01', '9999-12-31', :now, '9999-12-31', 'captured');
```

Run the three statements in one transaction. Rows are only ever closed on the recorded axis, never deleted or edited on the valid axis, so a query with an earlier knowledge date still returns the old belief.

Two questions, two queries:

```sql
-- what was true at :v, as known now
select * from history.customer_plan
where valid_from <= :v and :v < valid_to
  and recorded_to = '9999-12-31';

-- what was true at :v, as known at :k
select * from history.customer_plan
where valid_from <= :v and :v < valid_to
  and recorded_from <= :k and :k < recorded_to;
```

## As-of joins

Join each fact to the version in force at the fact's own time:

```sql
select f.order_id, f.amount, d.segment
from core.orders f
join history.customer_scd2 d
  on d.customer_id = f.customer_id
 and d.valid_from <= f.order_ts
 and f.order_ts < d.valid_to;
```

Snowflake also has `ASOF JOIN ... MATCH_CONDITION (...)`, which picks the nearest earlier row from a table of point-in-time records. It is a good fit for a change log without explicit `valid_to`; for a type-2 table the interval join above states the intent more plainly.

For a report as known at `:k`, add the recorded-time predicate to the history side and filter facts to `loaded_at <= :k`, so facts that arrived after the report are excluded as well.

## Integrity checks

Each query should return zero rows.

```sql
-- overlaps and gaps between consecutive versions
select entity_id, valid_from, valid_to, next_from
from (
  select entity_id, valid_from, valid_to,
         lead(valid_from) over (partition by entity_id order by valid_from) as next_from
  from history.customer_scd2
)
where next_from is not null and next_from <> valid_to;

-- not exactly one open version per live entity
select entity_id
from history.customer_scd2
group by entity_id
having sum(iff(valid_to = '9999-12-31', 1, 0)) <> 1;

-- empty or inverted intervals
select * from history.customer_scd2 where valid_from >= valid_to;

-- facts that match zero or more than one version
select f.order_id, count(d.customer_id) as versions
from core.orders f
left join history.customer_scd2 d
  on d.customer_id = f.customer_id
 and d.valid_from <= f.order_ts and f.order_ts < d.valid_to
group by f.order_id
having count(d.customer_id) <> 1;
```

A gap is legitimate only when the entity did not exist for that span (closed then reopened); record that as an explicit row or an allowed-gaps list rather than tolerating every gap. For a bitemporal table, run the first three checks per `recorded` interval: restrict to rows believed at a given `:k` and repeat for a handful of knowledge dates, including just before and after known corrections.

## Warehouse time travel

Snowflake `select ... from t at(timestamp => ...)` and BigQuery `select ... from t for system_time as of ...` read a table as it was at a recent moment. The window is short: Snowflake defaults to one day and allows up to 90 on Enterprise edition and above; BigQuery defaults to seven days and can be set between two and seven. Use it to recover a day you forgot to snapshot or to seed a new snapshot table, never as the answer to a question about last quarter.
