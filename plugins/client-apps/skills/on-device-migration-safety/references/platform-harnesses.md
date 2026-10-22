# Platform harnesses

How to build a fixture for every schema version and run the every-version migration test
on each common stack. The shape is the same everywhere: a list of field schema versions
from the census, a fixture per version, and one test that loops over them.

## Contents

- Room
- Core Data
- SwiftData
- Plain SQLite, GRDB, sqflite and Drift
- Comparing a migrated schema with a fresh one
- Pulling a real store off a device

## Room

Export schemas and commit them: set `exportSchema = true` on the `@Database` and give Room
a schema directory, either through the Room Gradle plugin's `schemaDirectory` or the
`room.schemaLocation` processor argument. The exported JSON for each version is what lets
the test create a historical database without the historical app. Make that directory
available to instrumented tests; the Gradle plugin does this, and with the processor
argument you add it to the `androidTest` assets yourself.

```kotlin
@get:Rule
val helper = MigrationTestHelper(
    InstrumentationRegistry.getInstrumentation(),
    AppDatabase::class.java,
)

@Test
fun migratesFromEveryFieldVersion() {
    for (from in FIELD_SCHEMA_VERSIONS) {          // from the census, not 1..LATEST blindly
        val name = "migration-from-$from"
        helper.createDatabase(name, from).apply {
            seedHostileRows(this, from)            // raw SQL against that version's schema
            close()
        }
        helper.runMigrationsAndValidate(name, LATEST, true, *ALL_MIGRATIONS)
    }
}
```

`runMigrationsAndValidate` checks the result against the exported schema for `LATEST`,
which is the "matches a fresh install" assertion. Then open the same file through
`Room.databaseBuilder(...).addMigrations(*ALL_MIGRATIONS).build()` and read through the
DAOs, so the data assertions go through the code users run. Auto-migrations
(`@AutoMigration(from = ..., to = ...)`) are covered by the same loop; a rename or delete in
an auto-migration needs an `AutoMigrationSpec`, and the test is how you find out you
forgot it.

Search the codebase for `fallbackToDestructiveMigration` before anything else. If it is
on the user-data database, that is the first finding.

## Core Data

- Keep every shipped `.xcdatamodel` version inside the `.xcdatamodeld`. A version removed
  from the bundle is a source model Core Data can no longer find, and users on it fail.
- Never edit a shipped model version; add a new one and make it current.
- Lightweight migration is inferred when `shouldMigrateStoreAutomatically` and
  `shouldInferMappingModelAutomatically` are true on the store description (the default).
  Anything it cannot infer needs a mapping model and, for transforms, an
  `NSEntityMigrationPolicy` subclass; on iOS 17 and later `NSStagedMigrationManager`
  chains lightweight and custom stages explicitly.
- To control when migration runs (off the main thread, with progress UI), set
  `shouldMigrateStoreAutomatically` to false, read the store's metadata with
  `NSPersistentStoreCoordinator.metadataForPersistentStore(ofType:at:options:)`, and ask
  the current model `isConfiguration(withName:compatibleWithStoreMetadata:)` to decide
  whether a migration is pending.

Fixtures: in a test, load an old compiled model from the app bundle's `.momd` directory
by its version name, create a store with it at a temporary URL, insert rows by entity
name and key, save, and close. Then open the same URL with the current container and
assert. Committing a fixture `.sqlite` produced by each shipped build is also fine, as long
as its WAL was checkpointed first.

## SwiftData

Wrap each shipped schema in a `VersionedSchema`, list them in a `SchemaMigrationPlan`'s
`schemas`, and describe each hop in `stages` with `MigrationStage.lightweight` or
`MigrationStage.custom`. Pass the plan when creating the `ModelContainer`. If the app
shipped without a versioned schema, the first `VersionedSchema` must describe what is
already on phones exactly. Test the same way as Core Data: create a container with an old
schema at a file URL, insert, close, reopen with the latest schema and the plan.

## Plain SQLite, GRDB, sqflite and Drift

- Track the version in `PRAGMA user_version` (or the library's own record: GRDB keeps
  applied migration identifiers in a table; sqflite passes old and new versions to
  `onUpgrade`; Drift has `schemaVersion` and a `MigrationStrategy`).
- Run each step inside one transaction and bump the version in the same transaction.
- Drift can dump each schema version and generate test helpers with `drift_dev`; use them,
  they are the Room-equivalent of creating a historical database without the old app.
- For hand-rolled stacks, generate fixtures by running each historical `CREATE` script
  from version control into an empty file and seeding it.

## Comparing a migrated schema with a fresh one

Compare normalised sets rather than `CREATE` text. Column order differs after
`ADD COLUMN`, and that difference is harmless; a missing index, a different default or a
lost `NOT NULL` is not.

```bash
set -Eeuo pipefail
dump() {
  sqlite3 "$1" "
SELECT 'column', m.name, p.name, p.type, p.\"notnull\", ifnull(p.dflt_value, '<none>'), p.pk
  FROM sqlite_master m JOIN pragma_table_info(m.name) p
  WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
UNION ALL
SELECT 'index', m.name, il.\"unique\", il.origin, il.partial,
       (SELECT group_concat(ifnull(ii.name, '<expr>'), ',') FROM pragma_index_info(il.name) ii), NULL
  FROM sqlite_master m JOIN pragma_index_list(m.name) il
  WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
UNION ALL
SELECT 'fk', m.name, f.\"from\", f.\"table\", f.\"to\", f.on_update || '/' || f.on_delete, NULL
  FROM sqlite_master m JOIN pragma_foreign_key_list(m.name) f
  WHERE m.type = 'table' AND m.name NOT LIKE 'sqlite_%'
UNION ALL
SELECT type, name, tbl_name, NULL, NULL, NULL, NULL
  FROM sqlite_master WHERE type IN ('trigger', 'view') AND name NOT LIKE 'sqlite_%'
ORDER BY 1, 2, 3, 4, 5, 6, 7" > "$1.schema"
  test -s "$1.schema"                       # an empty dump would make two broken files compare equal
}
dump migrated.db
dump fresh.db
diff migrated.db.schema fresh.db.schema
test "$(sqlite3 migrated.db 'PRAGMA integrity_check;')" = ok
test -z "$(sqlite3 migrated.db 'PRAGMA foreign_key_check;')"
```

The dump lists columns, indexes (including the implicit ones behind `UNIQUE` and primary
key constraints, which a filter on `sqlite_%` index names would hide), foreign keys with
their actions, triggers and views. A migration that drops `UNIQUE` on a column or loses
a `REFERENCES ... ON DELETE CASCADE` while rebuilding a table passes a comparison of
columns alone. `diff` and each `test` exit non-zero on a mismatch, so the script fails
instead of only printing; `PRAGMA foreign_key_check` prints nothing when clean, so its
output must be tested for emptiness rather than read by eye. `CHECK` constraints are not
exposed by a pragma; compare them through the `sql` column of `sqlite_master` for the
tables that use them.

## Pulling a real store off a device

Most stores run in WAL mode, so committed data may still be in the `-wal` file. Copying
only the main file gives a fixture that is missing recent writes or looks corrupt.

Android, debuggable build of the old version:

```bash
adb shell run-as com.example.app ls databases/
adb exec-out run-as com.example.app cat databases/app.db     > fixture-v11.db
adb exec-out run-as com.example.app cat databases/app.db-wal > fixture-v11.db-wal
sqlite3 fixture-v11.db "PRAGMA wal_checkpoint(TRUNCATE); VACUUM INTO 'fixture-v11-clean.db';"
```

`run-as` only works on a debuggable build, so build the old tag in debug rather than
pulling from a store install. The iOS simulator's data container is at the path printed
by `xcrun simctl get_app_container booted com.example.app data`; on a device, download
the container from Xcode's Devices window. In both cases take the `-wal` and `-shm` files
with the main file, then checkpoint and `VACUUM INTO` a single clean fixture. Strip or
replace any real personal data before committing a fixture.
