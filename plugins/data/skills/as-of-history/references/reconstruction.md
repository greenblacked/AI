# Reconstructing history that was never captured

Contents: where the past may still exist, how to rebuild from each source, how to mark inferred spans, and what to tell the people who use the figures.

## Where the past may still exist

Search in this order, because earlier sources are usually more precise and cheaper to read:

| Source | What it gives | Typical limit | Precision |
| --- | --- | --- | --- |
| Application audit or history tables | Each change with old and new value and a timestamp | As long as the application kept them; check for purge jobs | Exact, if every write path goes through the audited code |
| CDC stream or database log retention (Kafka topic, binlog, WAL archive) | Each change in commit order | The retention configured on the topic or log, often days | Exact within retention |
| Restored database backups | Full state at each backup time | Backup retention; monthly or yearly copies may reach further | State at backup instants only, nothing between |
| Object-store versions and old extract files | Full or partial copies at file time | Lifecycle rules on the bucket | State at file instants |
| Warehouse time travel and fail-safe | Recent state | Days, see the patterns reference | Exact within window |
| SaaS field history (CRM, billing system) | Changes to tracked fields | The vendor's retention and the fields that were tracked | Exact for tracked fields only |
| Published reports, exports, emails | Aggregates at publish time | Whatever was kept | Aggregates only; useful as a reproduction target, not a source of rows |

Ask the application team before assuming nothing exists. Audit tables are often there for compliance and unknown to the data team.

## Rebuilding from each source

- **Change events** (audit table, CDC): rebuild a type-2 table with `lead()` over the change time, as in the change-log section of the patterns reference. Check that every write path was audited by comparing the rebuilt current state with today's table; any mismatch means changes bypassed the audit.
- **Point-in-time copies** (backups, extracts, snapshots of files): load each copy as a periodic snapshot, then derive versions by comparing consecutive copies. A change between two copies is dated to the later copy, and a change that reverted between copies is lost. Record the copy interval: the history's resolution is that interval, not a day.
- **Aggregates only** (reports): do not try to invent rows that produce the aggregate. Keep the reports as reproduction targets and as a check on the rebuilt history.

Restore a backup into an isolated environment with no route to production, read the tables you need, and remove it afterwards; a forgotten restored copy of production data is its own data-protection problem.

## Marking inferred spans

Every rebuilt row carries:

- `history_source`: `captured` or `inferred:` followed by the method (`inferred:audit_table`, `inferred:monthly_backup`).
- The resolution where it is coarser than the captured data: the dates of the two copies a change was found between.

Record, per table, the date capture began. Below that date every row is inferred; above it every row is captured. Show the boundary on any chart that crosses it.

## What to tell the people who use the figures

Write one paragraph per table: which span is inferred, from what, at what resolution, and what kinds of change it cannot see (reverted changes between backups, untracked fields, writes that bypassed the audit). Attach the reproduction result for a published report inside the inferred span, if one exists; a match there is the strongest evidence the rebuild is usable.
