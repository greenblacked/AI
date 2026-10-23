---
name: on-device-migration-safety
description: "Ship a change to an app's on-device database — Core Data, SwiftData, Room, SQLite — when the store cannot roll it back and every phone migrates alone. Enumerate every app version still in the field from analytics, keep a fixture database per schema version and run migrations from every one in CI, not just the previous release, migrate inside a transaction after a backup copy, and ship a failure path that restores and degrades instead of bricking launch. Steps are forward-only; old fields stay one release. Use when the app crashes on launch after an update, someone asks how to test a Room or Core Data migration, is renaming a local column, or found fallbackToDestructiveMigration wiped user data. Not for a server database (db-migration), designing new tables (schema-design), a game's save files (game-save-system), or the store rollout (mobile-release)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# On-Device Migration Safety

Done means a fixture database from every schema version still installed in the field
migrates to the new version in CI, produces the same schema a fresh install creates, keeps
the data it should keep, and a migration that fails on a real phone restores the user's
data and opens the app in a degraded state instead of crashing on every launch.

This is harder than a server migration for one reason: there is no rollback and no
operator. A server migration runs once, watched, against one database you can restore. An
on-device migration runs millions of times, unattended, against databases that differ by
which version the user last opened, which edge-case rows they created, how full their
disk is and how long the OS lets the app take to launch. A user who skipped six releases
runs six migrations in a row on first open. Pausing the store rollout stops new installs
of the bad build; it does nothing for phones that already ran the migration. And the usual
test — upgrade from the previous release on a developer's phone — covers exactly the one
path that was least likely to break.

## Scope

Use for: adding, renaming, retyping or removing local tables and fields; Core Data model
versions and mapping models; SwiftData `SchemaMigrationPlan`; Room migrations and
auto-migrations; hand-rolled SQLite `user_version` migrations; a crash on launch after an
update; data lost after an update; deciding what a "rollback" build may do to a migrated
store.

Do not use for: a server-side relational migration, which is `db-migration`; designing a
new schema from scratch, which is `schema-design`; a game's save-file format, which is
`game-save-system`; staging the release and halting it, which is `mobile-release`.

## Hard gates

1. No migration merges without a fixture-based test from every schema version still in
   the field, not only N-1.
2. No destructive fallback on a store that holds data the user cannot re-download. Room's
   `fallbackToDestructiveMigration()` and "delete the store and recreate it" are a cache
   policy, not an error handler.
3. No shipped migration step is edited. A bug in a shipped step is fixed by a new step,
   because some phones already ran the old one.
4. No field is dropped in the same release that stops writing it.

## Workflow

### 1. Take a census of what is in the field

Pull active users by app version for the last 90 days from your analytics and the store
consoles, and map each app version to the schema version it shipped. Keep that mapping as
a table in the repository; it is the input to every later step.

| App version | Schema version | Share of active users |
| --- | --- | --- |
| 5.2 | 14 | ... |
| 4.9 | 11 | ... |

Include versions with a small share — the long tail is where skipped-version chains live —
and decide explicitly the oldest version you support. Below that, users get a defined
outcome (a forced upgrade path or a re-sync from the server), not an untested migration.
Remember two sources of old stores that analytics will not show: a device-to-device or
cloud backup restored onto a new phone, and a reinstall that restores an old backup.

### 2. Classify the change

| Change | Safe shape |
| --- | --- |
| Add a nullable field or one with a default | Single step; usually inferable (Core Data lightweight, Room auto-migration) |
| Add a table or index | Single step; index creation on a large table costs launch time — measure it |
| Rename a field or table | Add the new one, copy, keep the old one for a release, then drop. Check that the OS-bundled SQLite on your minimum OS supports `RENAME COLUMN` (3.25.0) if you use it directly |
| Change a type or split a field | New field, transform in a custom step, keep the old one |
| Drop a field or table | Stop writing it in release N, drop it in N+1 or later. Direct `DROP COLUMN` needs SQLite 3.35.0; otherwise rebuild the table |
| Anything SQLite's `ALTER TABLE` cannot express | The table-rebuild procedure from SQLite's documentation: set `PRAGMA foreign_keys=OFF` before opening the transaction (it is a no-op inside one, and with it on, dropping the old table cascades deletes into child rows), create the new table, copy, drop, rename, run `PRAGMA foreign_key_check` before commit, then turn it back on |

Write the step as forward-only and numbered. Never make one step depend on application
code that may change later; a migration that calls today's model classes breaks when
those classes change next year and the step is still in the chain.

### 3. Build a fixture for every schema version

A fixture is a real database file at that schema version with realistic and hostile data:
empty and maximum-length strings, nulls where the old schema allowed them, non-ASCII text,
duplicate-looking rows, orphaned references the old code tolerated, and enough rows to
make timing meaningful. Room can create any historical version from its exported schema
JSON; Core Data can create a store from any model version kept in the bundle; for other
stacks, build an old tag in debug and pull the file from a device.
`references/platform-harnesses.md` has the harness for each stack, including the WAL
files that a naive copy leaves behind. Fixture databases hold user-written text, so the
`sqlite3`, `adb` and `xcrun` commands it lists run with the user's approval rather than
being pre-approved.

*Gate:* one fixture per schema version from the census, checked in beside the tests.

### 4. Test every path to the new version

For each fixture: open it with the new code, let the migration run, then assert three
things.

1. The migrated schema matches a fresh install's schema. Fresh-install creation and the
   upgrade chain are two code paths, and they drift; compare normalised table, column,
   index and constraint sets, not raw `CREATE` text, because `ADD COLUMN` appends where a
   fresh `CREATE` may not.
2. The data you meant to keep is present and transformed correctly — counts per table and
   spot checks on the hostile rows.
3. `PRAGMA integrity_check` and `PRAGMA foreign_key_check` are clean.

Time the largest fixture on a low-end physical device in a release build. If it does not
finish well inside the launch budget, the migration must run after first frame with
progress UI (step 6), because a migration that the iOS launch watchdog kills is retried on
the next launch and killed again — a crash loop that lasts until a fixed build is
installed.

### 5. Wrap the migration in a transaction and a backup

The transaction and the backup protect against different failures, and you need both. The
transaction protects against the process dying mid-migration: SQLite DDL is transactional,
so an interrupted migration rolls back to the old version. The backup protects against a
migration that commits successfully and is wrong.

Before migrating: check free space, copy the store (all of it — see the WAL note in the
harness reference), and write a "migration in progress" marker with the from-version.
Migrate in one transaction, validate with step 4's checks, then remove the marker. Keep
the backup until the next successful launch at the new version, and delete it after that
so it does not double the app's footprint.

### 6. Ship a failure path that does not brick the app

On failure — an exception, a failed validation, or a marker found on launch meaning the
last attempt died — do not crash and do not silently wipe. Restore the backup, open the app
in a defined degraded state, and report the from-version, to-version, step and error to
telemetry. `references/failure-path.md` lists the degraded states in order of preference
and how to separate a re-downloadable cache store, where destructive recreation is fine,
from a user-data store, where it never is.

*Gate:* a test that injects a failure in the last step and asserts the app opens with the
user's data intact.

### 7. Release with the rollback build in mind

A "rollback" on mobile is a new build with a higher version number, often built from the
previous release's code. That build will open a store that has already migrated. Before
the rollout starts, decide what it does: either it knows the new schema version and
tolerates the extra fields (which is why old fields stay for a release and new ones are
additive), or it has an explicit downgrade step. Room throws when the stored version is
higher than the code's unless downgrade is handled, and Core Data refuses to open a store
whose model it does not have; neither failure is acceptable as the plan.

Watch migration telemetry by from-version during the staged rollout and hand the halt
criterion to `mobile-release`.

## Anti-patterns

**Testing the upgrade from last week's build.** It is the path most developers' phones
take and the least likely to break. Users who skip releases run the full chain.

**Destructive fallback as error handling.** It turns a migration bug into permanent data
loss for every affected user, silently, and the crash rate stays green.

**Editing a migration after it shipped.** Phones that already ran the old step will never
run the new one; the field now has two schemas with the same version number.

**Migrating on the main thread at launch.** Fine on a test database of a hundred rows;
a watchdog kill and a crash loop on the user who has kept five years of data.

**Calling current model code from an old step.** The step is frozen; the code it calls is
not.

## Output

Hand back: the version census and oldest supported version; each migration step with its
classification; the fixture list and the CI test that iterates over it; the measured
duration on the largest fixture on a low-end device; the backup, marker and failure path;
what a rollback build does to a migrated store; and the telemetry fields watched during
rollout.

## Reference files

- `references/platform-harnesses.md` — read at steps 3 and 4: building fixtures and the
  every-version migration test for Room, Core Data, SwiftData and plain SQLite, plus
  pulling a store off a device without losing the WAL.
- `references/failure-path.md` — read at steps 5 and 6: backup and restore mechanics,
  the degraded states in order of preference, cache versus user-data stores, and the
  telemetry a failed migration should send.
