# Thresholds and monitoring

## Contents

- [Alert tiers](#alert-tiers)
- [Settings that control freezing](#settings-that-control-freezing)
- [Monitoring queries](#monitoring-queries)
- [Estimating runway](#estimating-runway)

## Alert tiers

| Tier | Age | Page or ticket | Why |
| --- | --- | --- | --- |
| Watch | above 150 million | Dashboard only | Below the forced-freeze default of 200 million |
| Ticket | above 300 million | Ticket, same week | Forced freezes are not finishing or are blocked |
| Page | above 500 million | Page in hours | Leaves weeks of runway at typical transaction rates |
| Emergency | above 1 billion | Page now | Approaching the failsafe and the protective stop |

Tune the numbers to the transaction rate: a database that burns 100 million transactions a
day has days, not weeks, at 500 million. Apply the same tiers to `mxid_age`, but check the
actual `autovacuum_multixact_freeze_max_age` (default 400 million) before choosing them.

## Settings that control freezing

| Setting | Default | Effect |
| --- | --- | --- |
| `autovacuum_freeze_max_age` | 200 million | Table age at which autovacuum forces a freeze, even with autovacuum off; needs a restart to change |
| `vacuum_freeze_min_age` | 50 million | Row age at which vacuum freezes a row |
| `vacuum_freeze_table_age` | 150 million | Table age at which a normal vacuum scans the whole table to freeze |
| `autovacuum_multixact_freeze_max_age` | 400 million | Same trigger for multixacts |
| `vacuum_failsafe_age` | 1.6 billion (PG14+) | Vacuum skips index work and throttling to finish |
| `vacuum_multixact_failsafe_age` | 1.6 billion (PG14+) | The same for multixacts |

Verify any of these on the running server with `SELECT name, setting FROM pg_settings WHERE
name LIKE '%freeze%' OR name LIKE '%failsafe%';`, since defaults differ by version and by
managed-service parameter group.

## Monitoring queries

```sql
-- Per database, for the standing alert
SELECT datname, age(datfrozenxid) AS xid_age, mxid_age(datminmxid) AS mxid_age
FROM pg_database WHERE datallowconn;

-- Tables nearest to a forced freeze
SELECT c.oid::regclass, age(c.relfrozenxid) AS xid_age,
       age(c.relfrozenxid)::float / current_setting('autovacuum_freeze_max_age')::float AS ratio
FROM pg_class c WHERE c.relkind IN ('r','m','t') ORDER BY 2 DESC LIMIT 10;
```

A ratio above 1 means the table is past the forced-freeze point and should have a
freezing worker on it; if it does not, look for the blocker.

## Estimating runway

Record `age(datfrozenxid)` for the oldest database at two times. Growth per day is the
difference divided by elapsed days. Runway in days is (2,100,000,000 minus the current age)
divided by that growth. This is an upper bound: the server stops earlier, within a margin
that depends on the version.
