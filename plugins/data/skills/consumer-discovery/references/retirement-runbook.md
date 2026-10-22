# Retirement runbook

## Contents

- Timeline
- Announcement
- Rename with a compatibility view
- Brownout and the failed-query search
- Archive and restore
- Drop checklist

## Timeline

| Step | Typical timing | Reversible by |
| --- | --- | --- |
| Announce | Day 0 | Not needed |
| Rename, compatibility view in place | Day 0 to 7 | Renaming back |
| Brownout | One working day, announced, mid-week, after consumers have had time to migrate | Restoring the view or grant |
| Archive | Before the drop, after a clean brownout | Not needed |
| Drop | After a quiet period covering the slowest consumer's next run, and past a quarter end for financial data | Restoring from the archive |

Stretch the dates for consumers in other teams who need to rewrite pipelines. Avoid brownouts and drops near month end, quarter end and release freezes, when the readers you missed are most likely to run.

## Announcement

```text
Subject: <object> is being retired on <drop date>; use <replacement>

What changes: <object> will be renamed on <date>, unavailable for a test window on
<brownout date, hours, time zone>, and dropped on <drop date>.
Replacement: <replacement object>. Differences: <columns renamed, grain, definitions>.
How to switch: <one-line example or link>.
Known consumers contacted: <list>. If you use <object> and are not on that list,
contact <name> before <brownout date>.
```

Send it to each known consumer directly and to the general channel data users read. Put the drop date in the table comment as well, so someone browsing the catalogue sees it.

## Rename with a compatibility view

Move every writer first. A view is read-only, so a load still writing to the old name fails the moment the table is renamed; and a writer already moved to the replacement leaves a view over the renamed table serving data that no longer changes. Point the compatibility view at whatever is still loaded — the renamed table only while its writer has followed the rename, otherwise a projection of the replacement — and check its freshness against the load schedule before announcing the quiet period. The examples below assume the writer was repointed to the renamed table.

Snowflake:

```sql
alter table analytics.core.orders rename to analytics.deprecated.orders;
create view analytics.core.orders
  comment = 'Deprecated: use analytics.core.orders_v2. Dropped on 2026-12-01.'
  as select * from analytics.deprecated.orders;
```

BigQuery: a table that has received streaming writes cannot be renamed until streaming has stopped and its buffer has cleared, which can take hours. Move the streaming writer first, then wait until `bq show --format=prettyjson core.orders` no longer reports a `streamingBuffer`, and schedule the rename after that rather than in the same window. Check the dataset's default table expiration too (`bq show --format=prettyjson core`, `defaultTableExpirationMs`): a renamed table keeps its original creation time, so a table older than the default can expire the moment it is renamed. Remove or lengthen the dataset default before renaming, confirm the renamed table's `expirationTime` with `bq show`, and restore the default afterwards. A rename also drops the table's search and vector indexes and its catalogue metadata: list them first (`INFORMATION_SCHEMA.SEARCH_INDEXES` and `INFORMATION_SCHEMA.VECTOR_INDEXES` for the dataset, and the table's catalogue entry), and recreate them on the renamed table so readers through the view keep the same query path.

```sql
alter table core.orders rename to orders_deprecated;
create view core.orders
  options (description = 'Deprecated: use core.orders_v2. Dropped on 2026-12-01.')
  as select * from core.orders_deprecated;
```

Grant the view to the same roles that read the table. Readers of the old name now show up as queries on the view, which is the evidence to chase. In PostgreSQL and in Redshift without late-binding views, existing views follow the renamed table; list them from the dependency catalogue and treat their readers as readers of the old name.

## Brownout and the failed-query search

On the announced date, at the announced time, remove the compatibility view (or revoke `SELECT` on it from consumer roles). Restore it at the end of the window. Then find who failed.

Snowflake, the next day so the account usage view has caught up (for the same day, the `information_schema.query_history` table function):

```sql
select
  user_name, role_name, warehouse_name, query_tag,
  any_value(error_message) as example_error,
  count(*)                 as failures,
  min(start_time)          as first_failure,
  max(start_time)          as last_failure
from snowflake.account_usage.query_history
-- explicit offsets, so the window does not move with the session's TIMEZONE;
-- London is +00:00 in November and +01:00 in summer
where start_time >= '2026-11-18 09:00:00 +00:00'::timestamp_tz
  and start_time <  '2026-11-19 09:00:00 +00:00'::timestamp_tz
  and execution_status ilike 'fail%'          -- documented as lower-case 'fail'
  -- a dropped view says 'does not exist or not authorized'; a revoked SELECT says 'Insufficient privileges'
  and (error_message ilike '%does not exist or not authorized%'
       or error_message ilike '%insufficient privileges%')
  -- qualified, unqualified and quoted spellings: "CORE"."ORDERS", core.orders, orders
  and regexp_like(query_text, '.*(^|[^a-z0-9_$])"?orders"?([^a-z0-9_$]|$).*', 'is')
group by 1, 2, 3, 4
order by failures desc;
```

BigQuery:

```sql
select
  user_email,
  to_json_string(labels)       as labels,
  any_value(error_result.message) as example_error,
  count(*)                     as failures
from `region-eu`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
where creation_time >= timestamp '2026-11-18 09:00:00 Europe/London'
  and creation_time <  timestamp '2026-11-19 09:00:00 Europe/London'
  and regexp_contains(lower(error_result.message), r'not found|access denied')
  -- qualified, unqualified and backquoted spellings all end in the table name
  and regexp_contains(lower(query), r'(^|[^a-z0-9_])`?orders`?\b')
group by 1, 2;
```

A failed query referenced an object that did not exist, so `referenced_tables` is empty; the search has to be on the query text. Match the bare table name rather than one qualified spelling, because a consumer may write it unqualified under a default schema or quote it, and let the error filter keep the match from sweeping in every other table of the same name. Add a pattern for each alias the object had. Also check the BI tool's error log and the orchestrator's failed tasks for the window: a dashboard that failed to refresh may show stale data rather than an error.

Every failure is a consumer to contact. If any is material, restore, migrate it, and schedule a second brownout rather than proceeding.

## Archive and restore

Take the archive last, after the final write. If a writer still loads the renamed table, stop it or move it to the replacement first, wait for its last run (and, on BigQuery, for the streaming buffer) to finish, and only then clone. A clone taken while the table is still being written misses every row loaded after it, and the drop that follows breaks the writer as well.

Snowflake:

```sql
-- record the production grants first: a clone does not carry them
show grants on table analytics.deprecated.orders;
create table archive.core_orders_20261201 clone analytics.deprecated.orders;
-- test the restore before the drop, under a scratch name in the production
-- schema: the old name is still the compatibility view, and consumers have no
-- access to the restricted archive schema, so a test there proves nothing
create table analytics.core.orders_restore_test clone archive.core_orders_20261201;
-- compare row counts, replay the recorded grants on it, read it as a consumer
-- role, then drop it
drop table analytics.core.orders_restore_test;
-- real restore, after the drop: remove the view, then restore the name
drop view if exists analytics.core.orders;
create table analytics.core.orders clone archive.core_orders_20261201;
-- replay the recorded grants and test a consumer role's read
```

A dropped Snowflake table can also be recovered with `undrop table` within its Time Travel retention, which is short; the clone is the restore path that lasts.

BigQuery: record the table-level access policy before archiving (`bq get-iam-policy --format=prettyjson core.orders_deprecated > orders_policy.json`), because a restored clone takes its access from the destination dataset, not from the snapshot.

```sql
create snapshot table archive.orders_20261201
  clone core.orders_deprecated
  options (expiration_timestamp = timestamp '2027-06-01 00:00:00 UTC');
-- test the restore before the drop, under a scratch name
create table core.orders_restore_test clone archive.orders_20261201;
-- set the recorded policy on it and read it as a consumer, then drop it
drop table core.orders_restore_test;
-- real restore: remove the compatibility view first, then restore the name
drop view if exists core.orders;
create table core.orders clone archive.orders_20261201;
-- then: bq set-iam-policy core.orders orders_policy.json, and read it as a consumer
```

A table snapshot leaves out rows still in the streaming buffer. If the table took streaming inserts, wait until `bq show --format=prettyjson core.orders_deprecated` no longer reports a `streamingBuffer`, then compare the snapshot's row count with the source before dropping anything.

Redshift: `UNLOAD` the table to object storage in Parquet with the cluster's existing IAM role, and record the `COPY` command that would load it back.

Restrict access to the archive to the data team, and set an expiry: an archive without one becomes a second copy of the data that nobody owns, which matters most for personal data.

## Drop checklist

- Brownout produced no unexplained failures, or each one has migrated.
- Every known consumer has confirmed, in writing, that they have moved.
- The quiet period has passed the slowest known schedule and, for financial data, a quarter end.
- No writer targets the table any more, and the archive was taken after its last write.
- The archive exists, its row count matches the source, its restore command has been tested once, including the replayed grants, and its expiry is set.
- Dead code found during discovery is removed in the same change, so nothing re-creates a dependency.
- The drop is announced on the day, with the archive location and contact.
