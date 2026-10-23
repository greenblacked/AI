# Compatibility scan

Read this at step 2. Run every check against production, or a fresh restore of it,
because extensions, settings and collations drift between environments.

## Contents

- [PostgreSQL](#postgresql)
- [MySQL](#mysql)
- [Clients and drivers](#clients-and-drivers)
- [Collation after an operating system change](#collation-after-an-operating-system-change)
- [Reading the release notes](#reading-the-release-notes)

## PostgreSQL

Installed extensions, on the current server:

```sql
SELECT extname, extversion FROM pg_extension ORDER BY extname;
```

Then, on any instance already running the target version (a scratch container, or a
managed instance created for the purpose), list what is available and compare:

```sql
SELECT name, default_version FROM pg_available_extensions ORDER BY name;
```

An extension missing from the target list blocks the upgrade. One available only at a
different version is upgraded after the server move with `ALTER EXTENSION name UPDATE`,
following the extension's own notes; PostGIS in particular has its own upgrade steps.

`pg_upgrade --check` runs the tool's own compatibility tests without changing anything.
It needs the target binaries installed and a freshly initialised target data directory:

```bash
pg_upgrade --old-bindir="$OLD_BIN" --new-bindir="$NEW_BIN" \
  --old-datadir="$OLD_DATA" --new-datadir="$NEW_DATA" --check
```

It reports, among other things, shared libraries the old cluster loads that the new
binaries lack, and data types the new version cannot read in user tables. A clean
`--check` is necessary, not sufficient: it says nothing about configuration parameters
your `postgresql.conf` sets that the target removed, which the server only reports when
it refuses to start.

Version-specific traps worth checking by name:

| Crossing | Check |
| --- | --- |
| Into 14 | `password_encryption` defaults to `scram-sha-256`; drivers that predate SCRAM cannot authenticate with newly set passwords |
| Into 15 | New databases no longer grant `CREATE` on the `public` schema to everyone; upgraded databases keep their existing grants, so environments diverge |
| Into 16 | `promote_trigger_file` is removed; failover tooling that relied on it must call `pg_promote()` or `pg_ctl promote` |
| Into 17 | `old_snapshot_threshold` and `db_user_namespace` are removed |
| Into 18 | `initdb` enables data checksums by default and `pg_upgrade` requires both clusters to match, so initialise the target with `--no-data-checksums` if the old cluster has none, or enable checksums on the old cluster first; MD5 password authentication is deprecated |

From 18, `pg_upgrade` carries most planner statistics across; run
`vacuumdb --all --analyze-in-stages --missing-stats-only` afterwards to fill what it did
not, including extended statistics.

## MySQL

MySQL Shell's upgrade checker reads the server and reports errors, warnings and notices
for the target version:

```js
util.checkForServerUpgrade('admin@db-host:3306', {"targetVersion": "8.4.0", "outputFormat": "JSON"})
```

Treat every error as a blocker and read every warning; the checker's output is
version-specific and is the closest thing to a complete list.

| Crossing | Check |
| --- | --- |
| 5.7 to 8.0 | Query cache removed; new reserved words break unquoted identifiers; default character set becomes `utf8mb4` with `utf8mb4_0900_ai_ci`; implicit sorting for `GROUP BY` removed |
| 8.0 to 8.4 | `mysql_native_password` is no longer loaded by default; `default_authentication_plugin` is replaced by `authentication_policy`; the `MASTER` and `SLAVE` forms of replication statements (`CHANGE MASTER TO`, `SHOW SLAVE STATUS`) are removed in favour of `CHANGE REPLICATION SOURCE TO` and `SHOW REPLICA STATUS`; several InnoDB defaults change |

The replication-statement removal breaks automation silently: a failover script or
monitoring check that runs `SHOW SLAVE STATUS` fails on the first call after the
upgrade. Search scripts, runbooks and exporters for the old forms before the upgrade.

## Clients and drivers

List the drivers and versions actually connecting, from the server's own view where it
offers one (`pg_stat_activity.application_name`, MySQL's `performance_schema.session_connect_attrs`),
and check each against the target's authentication default and protocol requirements.
A connection pooler such as PgBouncer or ProxySQL sits in this list too, with its own
supported authentication methods.

## Collation after an operating system change

When the upgrade method lands the data on a new host or image (blue/green, logical
replication, a new managed instance class), the C library's collation rules may differ.
A changed sort order makes existing text indexes silently wrong: lookups miss rows and
unique constraints admit duplicates. On PostgreSQL 15 and later:

```sql
SELECT datname, datcollversion, pg_database_collation_actual_version(oid) AS actual
FROM pg_database WHERE datcollversion IS DISTINCT FROM pg_database_collation_actual_version(oid);
```

Any row returned means reindex the text indexes in that database, then
`ALTER DATABASE name REFRESH COLLATION VERSION`. The `amcheck` extension's
`bt_index_check` verifies a suspect index. Logical replication rebuilds indexes on the
target, so it avoids carrying corrupted indexes but not the changed sort order itself.

## Reading the release notes

Each PostgreSQL major's release notes open with a "Migration to Version N" section
listing incompatibilities; MySQL publishes "Changes in MySQL N" and an upgrade guide per
series. Read every major between current and target. For each item, write one line:
applies to us or not, and why. That list is the step 2 deliverable, and the "why" is
what lets a reviewer check it.
