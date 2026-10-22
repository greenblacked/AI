---
name: game-memory-budget
description: "Set and enforce per-system memory budgets and find leaks and fragmentation on memory-constrained targets. Writes the platform ceiling less the OS reserve as one budget table in the repository, measures peak (not average) memory in a release build on the real target at fixed checkpoints, runs a twenty-loop load-play-unload soak to tell a staircase leak from a plateau cache, diffs snapshots by type and allocation site, and fails CI when a checkpoint exceeds its budget. Use whenever someone says \"out of memory on Switch\", \"the phone kills the game after twenty minutes\", \"memory grows every level load\", \"console TRC memory limit\" or \"heap fragmentation\". Not for import settings that shrink textures and audio or a one-shot import-size kill (game-assets), frame time (game-performance), download size (game-patch-size), or memory growth in a non-game app (debugging)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Game Memory Budget

The work is done when every system has a written memory budget in the repository, a release build on the real target stays under the platform ceiling at every checkpoint across a twenty-loop soak, and CI fails when a checkpoint exceeds its budget by more than the agreed margin.

The usual failure is profiling before budgeting. A team opens a memory snapshot, sees forty megabytes of textures, shrinks some, and has no way to know whether that was enough, what to give up next, or whether the next feature fits. The second failure is measuring the wrong number: the editor's figure, an average, or the engine's own count of what it allocated, when the thing that kills a game on a phone is the operating system's figure for the process, and on a console the fixed limit in the platform's rules.

## Scope

Use for: out-of-memory crashes and the OS killing the game; memory that grows across level loads or over a session; a console certification memory limit; deciding what a new feature may cost; heap fragmentation on a long-running session.

Do not use for: shrinking a texture or audio import, or a game that is too large on first launch or killed once at import, which is `game-assets` and which owns the import settings. Frame time and hitches, even when caused by garbage collection, are `game-performance`; this skill owns how large the heap grows, that one how often it collects. Download and patch size are `game-patch-size`. Memory growth in a non-game app is `debugging`.

## Workflow

### 1. Budget before profiling

Write the budget table first, in a file in the repository (`docs/memory-budget.md` or a data file CI can read).

1. **Ceiling.** The memory available to the game on the lowest supported device or the dev kit's documented limit for the title. Read it from the platform's documentation or tool, not from the spec sheet's total RAM; the total is not what the game gets.
2. **Reserve.** Subtract the operating system, the runtime and the engine's own fixed cost (measure an empty scene in a release build for the last).
3. **Allocate** the remainder across systems: textures, meshes, audio, animation, scripting heap, UI, physics, networking, and any other the game has. Keep 10 percent unallocated as headroom; it is what absorbs the player who does something unexpected.

One row per system, with the owner, the budget in megabytes and the measured peak beside it. A budget with no owner is a number nobody defends. `references/budget-and-tools.md` has a template and the per-platform sources for the ceiling.

### 2. Measure the number that kills the process, on the target

Use a release build on the real device or dev kit. The editor adds its own allocations and keeps assets resident differently, so its memory figure is not the game's.

Record the peak, not the average, at fixed checkpoints: boot, main menu, each level load complete, mid-level at a scripted moment, and after returning to the menu. An average hides the spike during a level transition, where old and new assets are both resident, and that spike is what exceeds the ceiling. A checkpoint snapshot misses it too, so also poll the OS figure continuously (for example every 100 ms) through each transition and record the maximum, or read a high-water mark where the OS has one, such as `VmHWM` on Linux. The gate in step 6 compares that per-transition maximum, not the checkpoint snapshot, against the ceiling.

Use the figure the platform enforces, which differs by target:

- **iOS**: the footprint the system measures per process, against the jetsam limit; Instruments and Xcode's memory gauge report it, and `os_proc_available_memory()` reports the remaining headroom at runtime.
- **Android**: `adb shell dumpsys meminfo <package>` reports proportional set size by category, but only at the instant it runs, so loop it through transitions; the low-memory killer decides by process memory and priority, so test with other apps resident.
- **Consoles**: the dev kit's memory tool and the title's fixed limit from the platform documentation, which is under the platform holder's access terms.
- **Desktop**: resident set size, and the peak on Linux in `VmHWM` of `/proc/<pid>/status`.

The engine's own counters are useful for attribution, not as the verdict: Unity's Memory Profiler package, Unreal's `memreport -full` and the low-level memory tracker, Godot's `Performance` monitors. Take the OS figure for the pass or fail and the engine figure to explain it. Record both in the same table.

### 3. Leak test as a loop

A single snapshot cannot distinguish a leak from a cache. Script the loop: load a level, play a scripted minute, unload to the menu, and repeat twenty times, sampling resident memory at the same checkpoint each time. `automated-playthrough` is the way to drive this unattended.

Plot the checkpoint value against the iteration. A plateau after the first few loads is a cache filling and stopping. A staircase, rising by roughly the same amount per loop and never levelling, is a leak. Fit a line to the last ten points and flag a slope above a small fraction of the budget per loop; do not eyeball it, because 3 MB per loop over 20 loops is invisible on a graph and a crash at loop 200.

On mobile also run a long single session, because the report "killed after twenty minutes" is usually growth within a level, not across loads.

### 4. Find what grew

Take a snapshot at the same checkpoint on loop 2 and loop 20 and diff them. Rank the growth by type and by allocation site: which asset type or object class grew, and which call stack allocated it. A texture count that rises by one per load is a reference held by something static or an event handler never unsubscribed. A scripting heap that grows with no matching object is fragmentation or a collector that cannot run; a heap that shrinks nowhere after unload suggests objects kept reachable by a static list.

Fix the cause the diff shows. Do not clear caches by hand to hide a staircase.

### 5. Fix in order of size

Take the biggest line in the table first, and re-measure after each change:

1. Textures and the streaming pool: resolution, compression, mip streaming budget, and textures resident that no scene uses.
2. Audio: banks and long streams loaded fully into memory that could stream.
3. Duplicated assets across bundles or packages: the same texture shipped in three bundles is resident once per loaded bundle that holds a separate copy.
4. Then scripting-heap churn and fragmentation: pool and reuse short-lived objects, preallocate large fixed arenas, and avoid growing and shrinking big buffers in the middle of play.

Fragmentation is real when free memory in total is enough and no single block is. Fixed arenas for known-lifetime data (per level, per frame) fix it by construction.

### 6. Make CI enforce it

Add a check that runs the checkpoint script on the target or the nearest reproducible stand-in and fails when any checkpoint, or the per-transition maximum from step 2, exceeds its budget by more than the agreed margin (start at 5 percent; tighten when the numbers are stable). Print the table in the failure, with the system that grew. Store the measured peaks per commit so a regression is bisectable. A budget no build can fail is a document.

### 7. Report

```markdown
## Budget
[Target, ceiling, reserve, per-system table with owners.]

## Peaks
[Checkpoint, OS figure, engine figure, budget, headroom.]

## Soak
[Loops run, the slope, and the verdict: leak or plateau.]

## Growth
[Top types and sites from the diff, and the cause.]

## Changes
[One line each: what, MB saved, quality cost.]

## Gate
[The CI check, its margin, and what still exceeds it.]
```

## Anti-patterns

**Judging by the editor's number.** It is a different process with different residency.

**Using the average.** Level transitions set the peak, and the peak is what the OS kills.

**Calling a cache a leak, or the reverse.** Only the repeated loop separates them.

**Shrinking textures until a number looks fine.** Without a budget table there is no way to say whether that was the right system to cut.

**Clearing everything on level unload and calling it fixed.** A reference that keeps an asset alive then reloads it next time, and the soak shows the cost as hitching instead of memory.

## References

- `references/budget-and-tools.md` — read at steps 1 and 2: the budget table template, where to get the ceiling on each platform, and the capture commands per engine and OS.
