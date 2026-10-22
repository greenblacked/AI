# Failure path

What the app does when a migration fails on a real phone. The goal is that no failure
mode ends in either a crash on every launch or a silently empty app.

## Contents

- Split cache from user data
- Taking the backup
- The in-progress marker
- Degraded states, in order of preference
- Telemetry

## Split cache from user data

Keep data the app can re-download (feeds, catalogues, thumbnail metadata) in a separate
store from data only the device holds (drafts, unsynced edits, offline queues, settings,
anything the user created). For the cache store, destructive recreation on a failed
migration is a legitimate policy and simplifies everything. For the user-data store it is
data loss. A single store holding both forces the stricter policy onto all of it, so split
them before the next risky migration if they are not split already.

## Taking the backup

- Check free space first: the backup and a table rebuild can each need roughly the size
  of the store again. On iOS read `volumeAvailableCapacityForImportantUsage`; on Android
  use `StatFs` or `File.getUsableSpace()`. If there is not enough room, do not start; show
  the user how much space the update needs.
- SQLite: `VACUUM INTO '<backup path>'` (SQLite 3.27.0 and later) or the online backup
  API produce a consistent single-file copy from an open database. A plain file copy is
  only safe with every connection closed, and must include the `-wal` and `-shm` files.
- Core Data: copy with the coordinator's `replacePersistentStore` rather than copying the
  `.sqlite` file alone, so the WAL comes with it.
- Keep the backup until the first successful launch at the new version, then delete it.
  A backup kept forever doubles the app's storage footprint, which users see in settings.

## The in-progress marker

Before migrating, write a small marker (a file or a key in the app's preferences) holding
the from-version, to-version and an attempt count. Remove it after validation passes.

On launch, a marker that is still present means the previous attempt died: watchdog kill,
memory-pressure kill, or the user swiped the app away. Increment the attempt count. On the
first retry, run the migration again off the main thread with progress UI. From the second,
go to the degraded path rather than retrying a third time, because whatever killed the
process is likely to kill it again.

## Degraded states, in order of preference

1. **Retry off the launch path.** Show the first frame and a "finishing the update"
   screen, run the migration on a background thread, and on iOS request extra time with
   `beginBackgroundTask` in case the user leaves. This covers the watchdog case.
2. **Restore and re-sync.** If the server is the source of truth: restore the backup,
   extract anything not yet synced (outbox rows, drafts) through a minimal read of the old
   schema, create a fresh store, re-download, and replay the extracted writes. Keep the
   backup file until the replay succeeds.
3. **Restore and export.** If nothing is server-backed: restore the backup, open a
   read-only view if the code can read the old schema, and offer the user an export or a
   support path. Keep the backup.
4. **Last resort.** Open with an empty store, keep the backup file on disk, tell the user
   their data is kept and that an update will recover it, and ship a fixed migration that
   looks for that file.

Never delete the backup automatically on a failure path. It is the only copy of what the
user cannot get back.

## Telemetry

Send one event per migration attempt with no user content in it:

| Field | Why |
| --- | --- |
| `from_schema`, `to_schema` | Failures cluster by starting version; this is how a long-tail chain shows up |
| `step` | Which numbered step failed |
| `outcome` | `success`, `failed_restored`, `failed_resynced`, `interrupted` (marker found), `insufficient_space` |
| `duration_ms` | Watch the p95 against the launch budget |
| `store_size_bucket` | Duration and failure rate both scale with size |
| `error_class` | The exception type or SQLite result code, not the message text, which may contain data |

During a staged rollout, chart failure and interruption rates by `from_schema`. A rise in
one old version's rate is the halt signal to hand to `mobile-release`; the crash-free
rate will not show it if the failure path is doing its job.
