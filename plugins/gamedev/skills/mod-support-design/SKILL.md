---
name: mod-support-design
description: "Decide whether and how to let players mod a game, then write the commitment down: support level (tolerated, data mods, scripted), a small versioned API the studio dogfoods, a manifest with dependencies and load-order hints, a sandboxed trust model, deterministic load order with safe mode, multiplayer mod-set matching, and a support policy for modded bug reports. Use whenever someone says \"we want to support mods\", \"Steam Workshop integration\", \"how do we sandbox mod scripts\", \"mods break every patch\", \"what do we expose to modders\" or \"players report crashes but run 200 mods\". Not for save versioning (game-save-system), web API design (api-design), auditing a third-party extension before install (agent-extension-audit), or game crash dumps and minidumps (debugging)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Mod Support Design

The work is done when the game has a written support level, a versioned modding interface that the shipped game itself uses, a manifest format with a startup validator, a trust model that says what a mod can and cannot touch, and a support policy that tells staff what to do with a bug report from a modded install.

The usual failure is exposing whatever the code happens to look like. Modders then depend on internals, every patch breaks them, the players blame the studio, and the tracker fills with crashes nobody can reproduce because each player runs a different pile of mods.

## Scope

Use for: deciding whether to support mods; designing the data format, script API, packaging and distribution; keeping mods alive across patches; sandboxing; handling reports from modded installs.

Do not use for: versioning the save format itself, which is `game-save-system` (this skill only adds the mod set to what a save records); designing a web or service API, which is `api-design`; auditing a third-party extension before install, which is `agent-extension-audit`; game crash dumps and minidumps, which is `debugging`.

## Workflow

### 1. Choose the level and write it as a commitment

Pick one deliberately and put it in a document players can read:

- **Tolerated.** No promise. Files can be replaced, nothing is documented, nothing is kept stable. Cheap, and honest if stated.
- **Data mods.** Content defined in data (JSON, tables, asset overrides) that the game loads from a mod folder. Safe because no foreign code runs.
- **Scripted.** A versioned API that mods call. The most expensive level, because every function exposed is a promise.

The level decides the rest of the work. A studio that cannot staff an API owner should ship data mods; a stated "tolerated" beats an implied "supported" that is not.

### 2. Dogfood the interface

Move game content into the same data and scripts a mod would use, and have the shipped game load them through the same path. If the studio's own items, levels or rules do not use the interface, it is untested, and the first real test is a player's. Anything the studio has to special-case to ship its own content is a hole in the interface to fix before publishing it.

### 3. Keep the API small and versioned

Expose the least that makes the target mods possible: events to subscribe to, queries, and a few commands. Do not expose internal classes or mutable engine state. State the policy once: breaking changes only in a major API version, a deprecation window of at least one released version in which the old call still works and logs a warning, and a changelog naming each change.

Every mod carries a manifest declaring its id, version, the API version it targets, dependencies with version ranges, declared conflicts and load-order hints (`loadAfter`, `loadBefore`). `references/manifest-and-support.md` has a field list and the validator checks.

### 4. Write the trust model

For scripted mods, run scripts in a sandbox that has no raw file, network or process access. Give the mod an explicit capability list in its manifest (for example, read its own folder, write its own settings file) that the player can see before enabling. Enforce time and memory limits per mod per frame or per call, so a runaway script is stopped and named rather than hanging the game. For mods distributed through the store, require signature or review before listing; say what the review covers and what it does not.

Mods never alter saves silently. A save records the active mod set with versions, so loading it without those mods warns first rather than corrupting state. Data mods carry the same duty: a content id added by a mod needs a defined fallback when the mod is gone.

### 5. Make load order deterministic and failures legible

Resolve dependencies first, then apply load-order hints, then break remaining ties by id so the same set always loads the same way. Surface explicit conflicts instead of picking silently. On startup, validate before running any mod code: missing dependencies, dependency cycles, cycles in load-order hints (report them, drop the hints involved and fall back to id order), load-order overrides that contradict a dependency, stale API versions, duplicate ids. Each failure names the mod and the fix in one line and disables that mod rather than crashing the game.

Provide a safe mode (one launch option and one menu entry) that disables every mod, and make the log name the mod behind each error. An error that says only "script error" cannot be triaged.

### 6. Decide multiplayer and ranked behaviour

Multiplayer needs the same mod set on every peer, compared by id, version and content hash at connection time, refused with a message naming the difference. Ranked or competitive modes run mod-free. Client-only mods (interface, audio) can be declared as such in the manifest and excluded from the comparison, but only if the sandbox genuinely prevents them from changing simulation.

### 7. Ship the means to build a mod

Publish documentation, one small example mod and a command-line validator that runs the same checks as step 5. Then test the interface by having someone who has not seen the code write one mod from the documentation alone, and fix whatever they had to guess. This test finds more gaps than any review.

### 8. Write the support policy

- The game writes a report block itself: build id, API version, mod list with versions, load order. Players paste it; staff never ask for it by hand.
- A bug report from a modded install needs a mod-free reproduction before it enters the game's tracker. Without one it is routed to the mod's author or the community forum.
- A launch flag takes a mod-set file, so support can bisect a load order: with N mods, about log2(N) rounds find a single offending mod. `references/manifest-and-support.md` has the procedure.

### 9. Report

```markdown
## Support level
[Tolerated, data or scripted, and the sentence players will read.]

## Interface
[What is exposed, API version, deprecation policy, dogfooded content.]

## Manifest and load order
[Fields, resolution rules, startup validation messages.]

## Trust
[Sandbox limits, capabilities, store review, save behaviour.]

## Multiplayer and support
[Mod-set matching, ranked rule, report block, bisect flag.]
```

## Anti-patterns

**Exposing the engine because it was easy.** Every exposed internal becomes a promise broken on the next patch.

**Docs written after launch.** The docs-only test in step 7 belongs before release.

**Silent sandbox escapes by omission.** A scripting language with an unrestricted standard library is not a sandbox; remove the file, network and process modules rather than asking mods not to use them.

**Accepting crash reports without a mod-free repro.** It turns the tracker into a support desk for other people's code.

## References

- `references/manifest-and-support.md` — read at steps 3, 5 and 8: manifest fields, startup validator checks, the report block and the bisect procedure.
