# Versioning a save schema and migrating between versions

Read this at step 3 when the version scheme is being set, and again at step 9 when the migrations are being tested. The rules here are the ones that are cheap to follow before a version ships and impossible to apply afterwards.

## Contents

- [The version header](#the-version-header)
- [What does and does not need a migration step](#what-does-and-does-not-need-a-migration-step)
- [The migration chain](#the-migration-chain)
- [Rules that only hold if they are never broken](#rules-that-only-hold-if-they-are-never-broken)
- [Forward compatibility in practice](#forward-compatibility-in-practice)
- [The real-save corpus](#the-real-save-corpus)
- [Asserting on invariants](#asserting-on-invariants)
- [Retiring a version from the window](#retiring-a-version-from-the-window)

## The version header

Three things belong at a fixed offset at the start of the file, readable without parsing the body:

| Field | Size | Why it is here |
| --- | --- | --- |
| Magic bytes | 4 to 8 | A file that fails this is the wrong file, not a corrupt save, and the message to the player differs |
| Format version | 2 or 4 bytes, unsigned | Lets the loader refuse a save from the future before it half-parses one |
| Payload checksum | Fixed width | See `durability-and-corruption.md`; it is read before the payload is trusted |

Keep the header uncompressed and unencrypted even when the payload is neither. A support engineer who can read the version and the checksum of a file a player sent can classify the problem in a minute.

If the game writes more than one kind of file — profile, per-slot save, settings — version each independently. Settings and saves change shape at different rates, and one shared version number forces a migration for the other every time.

## What does and does not need a migration step

| Change | Step needed | Why |
| --- | --- | --- |
| New field with a safe default | No | The reader supplies the default for saves that lack it |
| Field removed | No, if readers ignore unknown fields | Old saves carry it; new readers skip it |
| Field renamed | Yes | The reader cannot know the old name maps to the new one |
| Type changed (int to float, string to id) | Yes | Silent coercion is how a value ends up wrong rather than missing |
| Unit changed (seconds to milliseconds) | Yes | The shape is identical, which is what makes it dangerous |
| Meaning changed with no rename | Yes, and it is the one that is missed | Nothing about the file looks different |
| One field split into several, or several merged | Yes | The mapping is game logic, not serialisation |
| Enum values reordered or renumbered | Yes, and prefer not to do it at all | Every existing save now points at a different value |

The rule underneath the table: a step is needed whenever a save written before the change would be read as valid and mean something else.

## The migration chain

Each step is a function from one version to the next, and nothing else:

```python
MIGRATIONS = {
    3: migrate_3_to_4,
    4: migrate_4_to_5,
    5: migrate_5_to_6,
}


def migrate(save: dict, target: int) -> dict:
    version = save["version"]
    if version > target:
        raise SaveFromTheFuture(version, target)
    while version < target:
        step = MIGRATIONS.get(version)
        if step is None:
            raise NoMigrationPath(version)
        save = step(save)
        version += 1
        save["version"] = version
    return save
```

Properties worth keeping:

- **Each step is pure.** It takes the previous representation and returns the next. It does not read the game's current constants, its balance tables or the player's settings, because those change and the step must not.
- **Each step runs against dictionaries or an equivalent loose representation**, not against the game's live classes. A step that constructs today's `PlayerState` stops compiling the first time that class changes, and the fix is always to edit the step, which is the thing you must not do.
- **A missing step is an error, not a skip.** `NoMigrationPath` with the version in it is a bug report; silently continuing is a save that is half-migrated.
- **A save from the future is refused with its own message.** A player on two devices at different patch levels will hit this, and "this save was made by a newer version of the game" is a complete answer.

## Rules that only hold if they are never broken

- Never reuse a version number, including one that only existed in a beta or an internal branch. Somebody has that save.
- Never renumber existing versions to close a gap.
- Never edit a step after a build containing it has left the team. Add a new version and a new step instead, even when the new step corrects the old one.
- Never make a step depend on anything outside the save: no clock, no random source, no network, no player settings. A migration must produce the same output on every machine and on every rerun.
- Back up before migrating, tagged with the source version, and keep it until the player has saved successfully afterwards.

## Forward compatibility in practice

An old build reading a new save can only work if unknown data survives a read and a rewrite. Two mechanisms do this:

- **A format that preserves unknown fields by construction.** Protocol buffers keep them in the message and re-emit them on serialisation.
- **An explicit passthrough.** The reader stores every key it did not recognise in a side map and merges it back when writing. This is a few lines in a JSON-shaped format and it is worth writing on day one, because retrofitting it does not help the saves already written by the old build.

Both fail against a field whose meaning changed rather than whose name did. If forward compatibility is promised, that promise is the reason a meaning change gets a new field name rather than a new interpretation of the old one.

## The real-save corpus

Capture files from play, not from the writer:

```text
tests/saves/
  v3/early-game.save
  v3/full-inventory.save
  v4/near-complete.save
  v4/mid-cutscene.save
  v5/bugged-quest-flag.save
  README.md
```

The `README.md` beside them records, for each file, which build wrote it and what makes it interesting. Without that the corpus becomes a directory of opaque blobs nobody dares delete.

What to capture:

- One ordinary mid-game save per shipped version, at minimum.
- The boundaries: a brand new save, and one at or near full completion.
- The awkward states the game allows — mid-cutscene, mid-transaction, in a menu that owns the player state.
- Anything written by a build with a known defect. These are the files that fail migrations that all the clean ones pass.
- A save from each platform that has its own save path or encoding, because platform-specific writers diverge.

Saves can contain player names and other personal data. Scrub them before committing, and say in the README that they were scrubbed.

## Asserting on invariants

Field-by-field comparison against an expected file fails on every legitimate change, so the suite gets disabled. Assert on what must survive:

- Totals that a player would notice: currency, experience, completion percentage, unlocked count.
- Identity: the same items, the same quests at the same stages, the same position in the world.
- Structural sanity after migration: no dangling ids, no value outside its declared range, no duplicate unique key.
- That the migrated save re-serialises and reloads to the same thing — a round trip that catches a step producing a representation the writer cannot express.

Run every corpus file through the full chain on every commit. The chain is cheap; the failure it catches is not.

## Retiring a version from the window

When the promise is "the last N versions", the retirement is a shipped change with its own work:

1. Decide the cut-off and say it in the patch notes before the build that enforces it.
2. Keep the refusal path specific: the version of the save, the version required, and what the player can do — which is usually installing an intermediate build, so say which one.
3. Keep the retired steps in the repository with the corpus that exercises them, even when unreachable, as documentation of what the file used to mean.
4. Check telemetry for how many players are actually below the cut-off before enforcing it. The number is almost always larger than the estimate.
