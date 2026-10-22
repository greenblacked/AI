# Pragmas, WAL inspection and the restore drill

Reference for steps 2, 5 and 7 of the workflow. Run these through the `sqlite3` shell
against a copy or a read-only connection when the live file matters.

## Contents

- [Which pragmas persist](#which-pragmas-persist)
- [Optional pragmas and their costs](#optional-pragmas-and-their-costs)
- [Inspecting the WAL](#inspecting-the-wal)
- [Restore drill](#restore-drill)
- [Version gates](#version-gates)

## Which pragmas persist

| Pragma | Scope | Note |
| --- | --- | --- |
| `journal_mode = WAL` | Stored in the database file | Survives reconnecting; confirm the returned value is `wal` |
| `synchronous` | Per connection | Resets to the build default on every connection |
| `busy_timeout` | Per connection | Milliseconds; zero by default |
| `foreign_keys` | Per connection | Off by default; has no effect inside an open transaction |
| `cache_size` | Per connection | Negative values are kibibytes, positive are pages |
| `wal_autocheckpoint` | Per connection | Pages in the WAL that trigger an automatic checkpoint |
| `journal_size_limit` | Per connection | Bytes the WAL file may keep after a checkpoint |

## Optional pragmas and their costs

- `cache_size = -65536` gives each connection about 64 MiB of page cache. Multiply by the
  number of pooled connections before choosing the figure.
- `mmap_size` maps the file into memory for reads. It can speed large read workloads, and
  an I/O error on a mapped page can crash the process rather than return an error, so
  leave it off on flaky storage.
- `temp_store = MEMORY` keeps temporary tables and indices in RAM; large sorts then
  compete with the application for memory.
- `journal_size_limit` bounds disk use after a checkpoint. It does not make a checkpoint
  succeed.
- `wal_autocheckpoint` lower means smaller WAL and more frequent checkpoint work on the
  committing connection; higher means fewer interruptions and a larger file.

## Inspecting the WAL

```sql
PRAGMA journal_mode;                 -- expect: wal
PRAGMA wal_checkpoint(PASSIVE);      -- checkpoints what it can, never waits
PRAGMA wal_checkpoint(TRUNCATE);     -- waits for readers, then resets the file
```

Result columns are `busy`, `log` (pages in the WAL) and `checkpointed` (pages moved).
`log` staying large across repeated PASSIVE checkpoints with `checkpointed` below `log`
means a reader holds an old snapshot. Compare the `-wal` file size on disk across an
hour: steady growth with no checkpoint progress is a pinning reader; a sawtooth that
resets is healthy.

## Restore drill

Outline, to run on a schedule against the newest backup in a scratch directory:

1. Copy the backup to a scratch path; never open the backup file itself for writing.
2. `sqlite3 scratch.db "PRAGMA integrity_check;"` and require the single row `ok`.
3. `sqlite3 scratch.db "PRAGMA foreign_key_check;"` and require no rows.
4. Run one application-level query that proves the data is current, for example the
   newest row's timestamp against the age the backup should have.
5. Delete the scratch copy and record the result with the time taken.

A backup that has never been restored is a hope, not a backup.

## Version gates

| Feature | Minimum SQLite |
| --- | --- |
| `VACUUM INTO` | 3.27 |
| `STRICT` tables | 3.37 |
| `sqlite3_rsync` | 3.47 |

Check the version linked into the application with `SELECT sqlite_version();`, since the
system shell and the embedded library often differ.
