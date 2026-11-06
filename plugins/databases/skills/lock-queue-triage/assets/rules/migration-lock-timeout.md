---
paths:
  - "migrations/**"
  - "db/migrate/**"
  - "**/migrations/**/*.sql"
---

# Migrations run DDL under a lock timeout

Planning a schema change belongs to the `db-migration` skill; this rule is only the guard
that loads when a migration file is open.

- Set `lock_timeout` (PostgreSQL) or `lock_wait_timeout` (MySQL) before every DDL
  statement, so a waiting ALTER gives up instead of queueing every later reader behind it.
- Wrap each DDL statement in a bounded retry with a pause between attempts, never an
  unbounded loop.
- Show the timeout in the migration file itself, so a reviewer can see it without
  running anything.
