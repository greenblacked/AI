# Verification queries

Read this at step 5, when deciding what the canary compares and writing the queries. The
order of checks is fixed in the skill; this file is the detail behind each.

## Contents

- The watermark rule
- Counts and checksums: PostgreSQL
- Counts and checksums: MySQL
- Mutable tables
- Documented exceptions
- Physical integrity
- Recovery point age
- The canary query suite

## The watermark rule

Production keeps writing after the backup point, so compare a range that cannot have
changed since then:

```text
watermark = backup_completion_time - margin
range     = [watermark - window, watermark)
```

Pick a `margin` larger than the longest transaction plus the clock skew between the
database and the backup system (an hour is comfortable), and a `window` small enough that
the production-side query is cheap (one to seven days). Run the identical query, with
identical bounds, on the restored copy and on a production read replica, never on the
primary: the comparison should not add load to the system it protects. Bound it with a
statement timeout on both sides, and treat a timeout as a failed check rather than a skip.

Compare the two result sets as a full outer join on the bucket key (the day), never by
walking one side's rows. A day that exists on the production side and is absent from the
restored copy produces no row there to disagree with, so a loop over the restored rows
passes a restore that lost a whole day. A day on either side only is a failure. A row whose
range column is NULL falls outside every range and is never compared, so the column must
be `NOT NULL`; count NULLs separately where it is not.

The range must be selected by a column that is set once at insert and indexed: a creation
timestamp or a monotonically increasing id. A column that updates (`updated_at`) moves
rows in and out of the range between the two queries.

For a point-in-time restore to time `T`, set `backup_completion_time` to `T`.

## Counts and checksums: PostgreSQL

Bucket by day so each aggregate stays small, and order explicitly so the hash is
deterministic:

```sql
SET statement_timeout = '5min';

SELECT date_trunc('day', created_at) AS day,
       count(*)                       AS row_count,
       md5(string_agg(id::text || ':' || created_at::text, ',' ORDER BY id)) AS digest
FROM orders
WHERE created_at >= $1 AND created_at < $2
GROUP BY 1
ORDER BY 1;
```

Cast timestamps to text the same way on both sides; a different `TimeZone` setting on the
canary session changes the text and every digest with it. Set the session time zone
explicitly in the job.

## Counts and checksums: MySQL

An order-independent digest, the same construction the Percona table-checksum tools use:

```sql
SET SESSION max_execution_time = 300000;

SELECT DATE(created_at) AS day,
       COUNT(*)         AS row_count,
       BIT_XOR(CAST(CONV(SUBSTRING(MD5(CONCAT_WS('#', id, created_at)), 1, 16), 16, 10) AS UNSIGNED)) AS digest
FROM orders
WHERE created_at >= ? AND created_at < ?
GROUP BY DATE(created_at)
ORDER BY day;
```

`BIT_XOR` cancels identical inputs in pairs, so two duplicate rows hash to nothing. Include a
unique key (`id`) in the hashed columns, as above, and do not use this on a table without
one. `CONCAT_WS` skips NULL arguments, so hash `COALESCE(column, '<null>')` for a nullable
column, or a NULL and an absent value digest the same.

`max_execution_time` applies to `SELECT` statements only and is in milliseconds.
`CHECKSUM TABLE` exists but covers the whole table, so it cannot use the watermark, and its
result depends on row format; do not compare it across versions or with live production.

## Mutable tables

For a table whose rows are updated after insert (accounts, inventory, subscriptions):

- hash only the columns that never change after insert (`id`, `created_at`, the owning
  tenant), with the watermark rule as above;
- compare the full row count against yesterday's canary result, failing outside a
  tolerance derived from the table's normal daily change (for example three times the
  largest daily net change seen in the last month);
- add an invariant from the domain where one exists: ledger entries sum to zero per
  transaction, every order line has an order, no subscription has an end before its start.

An invariant check finds the restore that is complete but internally inconsistent, which
counts and digests over single tables cannot.

## Documented exceptions

Legitimate mismatches inside a closed range exist, and they must be written down rather
than absorbed into a tolerance:

- **Erasure.** Rows deleted under a data-subject request after the backup point are present
  in the copy and gone from production. Exclude ids that appear in the erasure log for the
  window, or compare only counts for tables subject to erasure.
- **Late-arriving rows** with a creation timestamp set by a client, which can land inside an
  already-closed range. Prefer the server-assigned id for the range on such tables.
- **Application hard deletes** after the backup point (cancelled carts, removed
  subscriptions). For tables where the application deletes rows, compare only ids not deleted
  since the watermark where a deletion record exists, or fall back to a count-only comparison
  against yesterday's canary with the tolerance from the mutable-table rule above.
- **Archival jobs** that move old rows out of production. Keep the window newer than the
  archival horizon.

Before comparing against a production replica, read the replica's lag and require it to be
below the margin the watermark leaves. If it is not, report the run as inconclusive rather
than passed or failed, and rerun once the replica has caught up; a lagging replica makes
valid data look wrong and teaches the team to widen tolerances.

A mismatch that matches none of the documented exceptions fails the run.

## Physical integrity

PostgreSQL 14 and later ship `pg_amcheck`, which runs the `amcheck` extension's heap and
B-tree checks:

```bash
pg_amcheck --install-missing --heapallindexed --jobs=4 \
  --table=public.orders --table=public.order_lines "$DBNAME"
```

The positional argument is the database, not a table; name the key tables with `--table`.
The exit status is nonzero when corruption is found, and the job must test it. `--heapallindexed` checks that every heap tuple has its index entry, which is the check
that catches the index silently missing rows. It reads every page, so it is also the
step that pays the hydration cost on lazily restored storage; time it.

On MySQL, `CHECK TABLE orders, order_lines;` on the key tables. On a large table run it on
the key tables only, since it holds locks; on a scratch instance that cost is acceptable.

## Recovery point age

The newest row in the restored copy says how recent the data really is, regardless of
what the backup metadata claims:

```sql
SELECT max(created_at) FROM orders;
```

`recovery_point_age = backup_completion_time - max(created_at)` on a table that is written
continuously. An empty table returns NULL, and a comparison with NULL is never true, so
test for NULL first and fail on it: a restore that lost every row would otherwise pass. A value much larger than usual means the backup captured an older state than
its timestamp suggests: a snapshot of a lagging replica, or a dump that ran against stale
data. Fail when it exceeds the RPO.

## The canary query suite

Five to fifteen read-only queries, each with an expected shape and a time limit, chosen
because the business depends on them rather than because they are easy:

| Kind | Example | Passes when |
| --- | --- | --- |
| Lookup by key | Fetch a known, long-lived customer and their latest order | One row, expected columns non-null |
| Report aggregate | Last complete month's revenue by region | Within a tolerance of the figure recorded when that month closed |
| Join across key tables | Orders with their lines and payments for one day | Every order has lines and a payment state |
| Extension or feature use | A query that uses the full-text index, PostGIS function or JSON path the application needs | Returns rows within the time limit |
| Permission | Connect as the application's read role and select from a key table | Succeeds; a lost grant or role fails here |

Keep the suite in version control beside the job, with the expected value for each query
and the date it was last reviewed. A query whose expected value nobody can explain is
removed rather than kept passing by habit.
