# Manifest and support

Read this at steps 3, 5 and 8 of `SKILL.md`.

## Contents

- [Manifest fields](#manifest-fields)
- [Startup validator checks](#startup-validator-checks)
- [The report block](#the-report-block)
- [Bisecting a load order](#bisecting-a-load-order)

## Manifest fields

```json
{
  "id": "example.better-inventory",
  "name": "Better Inventory",
  "version": "1.2.0",
  "apiVersion": "2.x",
  "dependencies": [{"id": "example.core-lib", "range": ">=1.0 <2.0"}],
  "conflicts": ["example.old-inventory"],
  "loadAfter": ["example.core-lib"],
  "loadBefore": [],
  "capabilities": ["read-own-folder", "write-own-settings"],
  "clientOnly": false
}
```

- `id` is unique and stable; a rename is a different mod.
- `apiVersion` names the major API the mod was written against; the loader refuses a major it does not provide.
- `dependencies` need a version range, because "any version" is how a library update breaks its dependants.
- `capabilities` is the complete list the sandbox grants. Anything not listed is denied.

## Startup validator checks

Run all of these before any mod code executes, in the game and in the command-line validator.

| Check | Message should say |
| --- | --- |
| Missing dependency | which mod needs which id and range, and what is installed |
| Dependency cycle | the ids in the cycle |
| Cycle among `loadAfter`/`loadBefore` hints alone | the ids in the cycle; the hints involved are dropped and those mods fall back to id order |
| `loadAfter` contradicts a dependency | both mods and which rule won |
| Declared conflict present | both mods; neither loads until the player chooses |
| Stale or future API major | the mod's major, the game's majors, the mod disabled |
| Duplicate id | both file paths |
| Capability not recognised | the capability string |

Every failure disables the mod concerned and continues. A crash at startup is a bug in the validator.

## The report block

Written by the game into the log and copied by a menu button. Fixed format so staff can read it at a glance.

```text
build: 1.4.2+7731  api: 2.1  platform: windows-x64
mods (load order):
  1 example.core-lib 1.0.3
  2 example.better-inventory 1.2.0
  3 example.new-weapons 0.9.1
safe-mode: off
```

## Bisecting a load order

With a failing set of N mods and a launch flag that takes a mod-set file:

1. Run with no mods. If it still fails, the report is not a mod bug; stop.
2. Split the ordered list in half, keeping dependencies with their dependants (a mod cannot be tested without its dependencies).
3. Run each half. Keep the half that fails and repeat. If both halves fail, there are separate culprits (or a culprit in a shared dependency): bisect each half on its own. If neither half fails, the cause is an interaction across halves: hold one half fixed and bisect the other. Shared dependencies stay in both halves.
4. About log2(N) rounds identify the mod. Record its id and version in the report, and send the report to the mod's author.
