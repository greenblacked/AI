# Emergency runbook

An ordered checklist for a database whose age is above the page line. Record each answer
as you go; the hand-back and the postmortem need them.

## Contents

- [Before touching anything](#before-touching-anything)
- [Ordered steps](#ordered-steps)
- [Decision points](#decision-points)
- [What to record](#what-to-record)

## Before touching anything

1. Note the time, the version (`SELECT version();`), the oldest database and its age.
2. Confirm that you are looking at the primary and not a standby.
3. Check free disk and WAL volume. A stuck slot that blocks freezing often also fills disk.

## Ordered steps

1. List the blockers: open transactions, slots, prepared transactions, standby feedback.
2. End the oldest blocker you are entitled to end. Record pid, query, application name and
   owner before terminating a session; record slot name and consumer before dropping a slot.
3. Re-read the oldest `backend_xmin` age. Continue only when it has fallen.
4. List the ten oldest tables by `age(relfrozenxid)` and `mxid_age(relminmxid)`.
5. Check for a running `(to prevent wraparound)` worker on each. Leave it alone if present.
6. For tables without a worker: `VACUUM (VERBOSE, INDEX_CLEANUP off) tbl;`, oldest first.
   Leave FREEZE out: it rewrites every tuple and adds WAL when runway is shortest. Set
   `vacuum_cost_delay = 0` first only if it has been changed from the default.
7. Watch `pg_stat_progress_vacuum`. When a table finishes, re-read its age and the
   database's `datfrozenxid` age; the database figure only moves when the oldest table moves.
8. Stop writers that can be stopped (batch jobs, backfills) if the age is still rising faster
   than freezing falls.
9. After the age is under the page line, run a normal `VACUUM` on tables vacuumed with
   index cleanup off.

## Decision points

- The age does not fall after a table completes: another table, or a TOAST table, is the
  oldest. Re-run the table query including `relkind = 't'`.
- A vacuum runs for hours without progress: a blocker remains. Go back to step 1.
- The server refuses commands: follow the documentation for your exact version (see step 5
  of the skill). Do not rely on a remembered single-user procedure.
- A managed service restricts superuser actions: use the provider's documented way to drop
  slots and end sessions, and involve their support early.

## What to record

Versions, ages before and after, the blocker and its owner, commands run with timestamps,
the alert that should have fired and why it did not, and the settings changed.
