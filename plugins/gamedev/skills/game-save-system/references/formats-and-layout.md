# Choosing a save format and laying the file out

Read this at step 2, after the compatibility promise is written down and before any serialisation code exists. The promise narrows the field before taste does; this file is what is left once it has.

## Contents

- [The two disqualifiers](#the-two-disqualifiers)
- [Format by format](#format-by-format)
- [The save record pattern](#the-save-record-pattern)
- [File layout](#file-layout)
- [Compression](#compression)
- [Size, and where it stops being free](#size-and-where-it-stops-being-free)
- [Engine notes](#engine-notes)

## The two disqualifiers

**A serialiser that embeds type identity.** The file then names your classes, so a rename, a namespace move or an assembly rename invalidates saves that are already on players' disks. The same mechanism makes the file a code-execution surface: deserialising a hostile file constructs whatever types it names, and saves arrive from cloud sync, from forums and from friends. C# `BinaryFormatter` is obsolete and removed in current .NET, Java's built-in serialization has the same shape, Python's `pickle` is explicit in its own documentation that it is unsafe against untrusted input, and Godot's `FileAccess.store_var` takes a `full_objects` flag whose documentation says the same. Leave that flag false.

**A format with no room for an unrecognised field.** A fixed struct or a positional binary layout cannot be read by a build that knows a different set of fields, which forecloses forward compatibility permanently and makes every backward-compatible change a migration.

## Format by format

| Format | Best for | Watch for |
| --- | --- | --- |
| JSON | Almost everything under a few megabytes. Readable in a bug report, diffable, trivially inspectable in support | Integers past 2^53 in JavaScript-based engines; floating-point round-tripping; verbosity, which compression mostly answers |
| MessagePack, CBOR | The same data model, materially smaller and faster, when nobody needs to read it by eye | Library quality varies by engine; check that unknown keys survive a read and rewrite if forward compatibility is promised |
| Protocol buffers | A strict compatibility promise, large saves, or several clients reading the same file | The schema is a build artefact you now maintain and ship; field numbers are permanent |
| FlatBuffers, Cap'n Proto | Large saves that must load without a full parse — streaming worlds, big inventories | More machinery than a slot of player state needs |
| SQLite | A world saved in pieces, partial loads, and edits that must not rewrite the whole file. Gets durability and atomicity from the library | Migrations become schema migrations; the file is large next to a compressed blob for small saves |
| Engine-native or reflection-based | Prototypes and jam entries | See the disqualifiers above before this reaches a shipped build |

A game with a large world and a small player state is often best served by two files with different formats: a compact record for player progress, and a chunked store for the world. They version independently.

## The save record pattern

The most useful structural decision is that the persisted type is not the runtime type.

```csharp
// Persisted. Changes only when the save format changes, and every change gets
// a migration step. No behaviour, no references to live objects.
public sealed class SaveRecordV5
{
    public int Version;
    public string AreaId;          // a stable string id, not an enum ordinal
    public long PlaytimeMs;        // the unit is in the name
    public List<ItemRecord> Items;
}
```

The game converts between `SaveRecordV5` and its live state at exactly two places, load and save. What this buys:

- The runtime classes can be refactored freely, because nothing on disk refers to them.
- Every change to the file is visible as a change to one file in review, which is where a missing migration step gets caught.
- Migration steps operate on records or on the loose representation below them, so they never stop compiling when the game changes.
- The conversion is the natural place to validate ranges and drop content that no longer exists.

The cost is a second set of types and the mapping between them. For anything expected to ship a patch, it is repaid the first time a class is renamed.

## File layout

```text
[ magic 4-8 bytes ][ format version ][ checksum of payload ][ payload ]
```

- The header stays uncompressed and unencrypted even when the payload is not, so a file can be classified without being fully readable.
- The checksum covers the payload and excludes itself.
- Any metadata the front end shows in a slot list — playtime, area name, completion, a thumbnail — either belongs in the header or in a small sidecar file. A slot list that has to fully load and migrate every save to draw itself is slow on the first screen the player sees, and it runs migrations before the player has asked to load anything.

## Compression

Compress the payload, not the header. Both common choices are fine for this job: deflate or gzip is available everywhere, and zstd is faster at similar or better ratios where a library is available. Save data is repetitive, so ratios of three to ten times are usual for JSON.

Compression interacts with corruption. A single flipped byte in a compressed stream usually fails the whole decompression rather than corrupting one value, which is a better failure — as long as the checksum is checked first, so the failure is reported as a damaged file rather than as a decompression exception in a crash log.

## Size, and where it stops being free

- Under about a megabyte, nothing about size matters on any platform; choose for readability.
- Past a few megabytes, cloud sync time and console save quotas start to matter, and both are the player's problem rather than yours to measure in isolation.
- Console save quotas are per title and small. Budget the whole set — every slot, every backup, every autosave — against the quota, not against the largest single file.
- A save that grows without bound in normal play is a defect with a delayed fuse. Cap or roll anything append-only, and check the size of a near-complete save from the corpus on every release.

## Engine notes

- **Unity.** `JsonUtility` is fast and does not embed type names, but it does not serialise dictionaries, nulls behave surprisingly, and polymorphic fields need handling. A general JSON library is usually the better base for a save record. `PlayerPrefs` is a settings store, not a save system: it has no atomicity, no versioning and platform-specific size limits.
- **Godot.** `FileAccess.store_var` with `full_objects` left false writes Variants safely; `ConfigFile` suits settings. Use `user://` for anything persisted, and remember that the resource path is read-only in an exported build.
- **Unreal.** `USaveGame` with the engine's save system handles the platform details, and its property serialisation tolerates added properties. Renamed properties still need explicit handling, and the engine's own versioning is not a substitute for a format version you control.
- **Browser.** `localStorage` is small, synchronous and can be cleared by the browser without warning; IndexedDB is the durable option. Neither is a backup, so a game that matters offers an export.
