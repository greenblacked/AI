# Usage queries

## Contents

- Snowflake
- BigQuery
- Redshift
- Views and other aliases
- Resolving service accounts
- BI usage sources
- Lineage and code search

Replace the object names. Run each query for the table and for every view or alias found over it.

## Snowflake

`ACCESS_HISTORY` needs Enterprise edition or above, keeps a year, and lags real time by up to a few hours. `base_objects_accessed` resolves a query through a view to the tables underneath; `direct_objects_accessed` shows what the query named.

```sql
with access as (
  select
    ah.query_id,
    ah.query_start_time,
    ah.user_name,
    col.value:"columnName"::string as column_name
  from snowflake.account_usage.access_history ah,
       lateral flatten(input => ah.base_objects_accessed) obj,
       lateral flatten(input => obj.value:"columns", outer => true) col
  where ah.query_start_time >= dateadd('day', -120, current_timestamp())
    and obj.value:"objectName"::string = 'ANALYTICS.CORE.ORDERS'
)
select
  a.user_name,
  q.role_name,
  q.warehouse_name,
  q.query_tag,
  a.column_name,
  min(a.query_start_time)    as first_seen,
  max(a.query_start_time)    as last_seen,
  count(distinct a.query_id) as queries
from access a
join snowflake.account_usage.query_history q
  on q.query_id = a.query_id
group by 1, 2, 3, 4, 5
order by queries desc;
```

This finds readers through every view over the table, but a query that names a view is recorded against the view in `direct_objects_accessed` and against the table underneath in `base_objects_accessed`. To find who still uses a name — a compatibility view left behind after a rename, or any alias — run the same query with `ah.direct_objects_accessed` in the first `flatten` and the alias in the `objectName` filter. Keep the base-object run for the transitive readers.

Object names in `objectName` are fully qualified and upper case unless created with quoted lower-case identifiers. Drop `column_name` from the grouping for a table-level answer. Queries that write from this table into another (`insert ... select`, `create table as select`) appear here too; they are pipelines, and their output tables need the same discovery.

## BigQuery

`INFORMATION_SCHEMA.JOBS_BY_PROJECT` keeps 180 days and is regional: query the region that holds the dataset.

```sql
select
  j.user_email,
  to_json_string(j.labels) as labels,
  min(j.creation_time)      as first_seen,
  max(j.creation_time)      as last_seen,
  count(*)                  as jobs
from `region-eu`.INFORMATION_SCHEMA.JOBS_BY_PROJECT j,
     unnest(j.referenced_tables) t
where j.creation_time >= timestamp_sub(current_timestamp(), interval 180 day)
  and j.job_type = 'QUERY'
  and t.project_id = 'analytics-prod'
  and t.dataset_id = 'core'
  and t.table_id   = 'orders'
group by 1, 2
order by jobs desc;
```

Jobs run from other projects against this table are recorded in those projects. `JOBS_BY_ORGANIZATION` covers all projects in the organisation for someone with organisation-level permission; without it, ask the owners of projects known to read the dataset. Check whether queries through a view list the view, the table or both in `referenced_tables` on your setup, and search for the view names as well. For column-level use, the data-access entries in Cloud Audit Logs record the fields a read touched; query them from a log sink if one exists.

## Redshift

The system tables keep only a few days. For a 90-day picture, enable audit logging with the user activity log (it also needs the `enable_user_activity_logging` parameter in the cluster's parameter group) and search the delivered logs for the object name. For recent activity:

```sql
select
  u.usename,
  count(*)          as queries,
  min(q.start_time) as first_seen,
  max(q.start_time) as last_seen
from sys_query_history q
join pg_user u on u.usesysid = q.user_id
where q.query_text ilike '%core.orders%'
group by u.usename
order by queries desc;
```

`query_text` is truncated for long statements, so a miss here is not proof of absence. Searching text also matches comments and similar names; check a sample of hits by hand.

## Views and other aliases

- Snowflake: `snowflake.account_usage.object_dependencies`, filtered on the referenced object, lists views and other objects built on it.
- BigQuery: search `INFORMATION_SCHEMA.VIEWS.view_definition` in each dataset for the table name.
- PostgreSQL: `information_schema.view_table_usage`. Redshift: a query over `pg_depend`, such as the `v_view_dependency` admin view published in amazon-redshift-utils. In both, ordinary views bind to the table, not its name, which matters for the rename step.

Run the access queries again for each view found.

## Resolving service accounts

| Principal | Resolve through | To |
| --- | --- | --- |
| Orchestrator or dbt service user | Query tag or job labels, if the project sets them; otherwise the warehouse and schedule | The job, then its owner in the orchestrator |
| BI service account | The BI tool's usage log, filtered on queries hitting the object | Dashboards and saved queries, then their viewers |
| Reverse-ETL or integration user | The integration's sync configuration | The sync, its destination and the destination's owner |
| Shared or personal login used by a tool | Client application and host in the query history, then asking around | A person; give the tool its own account as part of the fix |

Without query tags, matching a service account's queries to jobs is guesswork. Setting tags or labels per job is worth doing in the same change.

## BI usage sources

- Looker: the System Activity explores (History, Content Usage) give queries, dashboards and users.
- Tableau Server or Cloud: the repository's view and access data, or Admin Insights on Cloud, gives views per workbook and user.
- Power BI: the activity log gives report views per user.
- Others: the tool's audit or usage feature, where the edition includes one.

Map each dashboard back to the object through its data source or model, then list its viewers over the same window as the warehouse query.

## Lineage and code search

```bash
dbt ls --select "orders+"                          # every downstream node
dbt ls --select "orders+" --resource-type exposure  # declared dashboards and apps
```

Search code for both the qualified and the bare name, case-insensitively, across every repository the organisation keeps pipelines, notebooks and reverse-ETL configuration in. A hit in code with no matching log entry is either a rare schedule or dead code; find out which before the brownout.
