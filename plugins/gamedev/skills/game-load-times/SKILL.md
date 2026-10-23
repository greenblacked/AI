---
name: game-load-times
description: "Cut boot and level load times and streaming hitches, measured on the slowest storage the game supports with the OS file cache cleared. Breaks a load into a phase timeline (read, decompress, deserialise, instantiate, GPU upload, initialisation scripts, shader warm-up) on cold and warm runs, so the ratio shows I/O or CPU; then packs by real access order, moves construction off the main thread, defers non-visible work, and gates a 10 percent regression in CI. Use whenever someone says \"loading takes forty seconds on a hard drive\", \"boot to menu is too slow\", \"level streaming hitches\", \"slow to start on a Steam Deck SD card\" or \"load screen budget\". Not for frame budget (game-performance), import size and the build-is-huge version of slow loading (game-assets), streaming seam placement (game-level-design), or shader warm-up alone (shader-compile-stutter)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Game Load Times

The work is done when boot-to-menu and level-load times are recorded per phase on the slowest supported storage, each phase has a named owner and a fix or a reason it stays, and CI fails a build that regresses a measured load by more than 10 percent.

The usual failure is optimising on a developer SSD with a warm cache. The game feels fine there, and the hard drive, SD card or console disc that players actually have is dominated by something else entirely.

## Scope

Use for: long boot or level loads; hitches while streaming; load budgets; choosing what to optimise first in a load.

Do not use for: frame rate during play, which is `game-performance`; a build that is simply too big, import settings and compression choices, which is `game-assets` (it already owns "loading takes forever" when the cause is import size); where to put streaming seams in a level, which is `game-level-design`; shader compilation on its own, which is `shader-compile-stutter`.

## Workflow

### 1. Measure on the worst storage, cold

Pick the slowest storage the game supports: a spinning disk, a slow SD card for a handheld, the minimum-spec console storage. Clear the OS file cache before each cold run, or the numbers measure memory. On Linux, run `sync` and then write `3` to `/proc/sys/vm/drop_caches` as root; on Windows, restart or empty the standby list with a tool built for it; on consoles use the platform's cold-boot procedure. Run at least five times and keep the median and the worst.

Record a warm run too (second run, cache populated). The cold-to-warm ratio is the first diagnosis: a cold run far slower than warm means I/O-bound; similar times mean the CPU is the limit.

### 2. Build the phase timeline

From a trace, not from log timestamps scattered by hand, split one load into phases and record wall time for each on the cold and the warm run: read bytes, decompress, deserialise, instantiate objects, upload to the GPU, run initialisation scripts, shader warm-up. Use the engine's profiler or trace capture, and the OS file-I/O trace where the engine hides reads (Windows Performance Recorder, `strace -f -tt -e trace=openat,read,pread64` on Linux). `references/load-phases.md` has the table layout and the per-phase fixes.

Fix the phase that is largest on the worst storage. Do not start with the one that is easiest.

### 3. If I/O-bound

- Pack assets that load together contiguously, in the order they are requested. Record the real access order from a trace of a typical load and sort the archive by it, so a spinning disk reads sequentially instead of seeking.
- Size compression for read speed rather than ratio. A fast codec that halves the bytes can win; a slow one that saves a further 5 percent loses on a CPU-limited machine.
- Remove data duplicated across bundles. The same texture packed into ten level bundles is read ten times.
- Check small-file overhead: thousands of tiny loose files are slower than a few archives on every platform.

### 4. If CPU-bound

- Move deserialisation and object construction off the main thread; hand finished objects back in one step.
- Prefer prebuilt binary formats to parsing text (JSON, XML, source scripts) at load time.
- Defer every non-visible initialisation past the first frame: audio banks for distant areas, tooltips, achievements, analytics.
- Look at instantiation counts. Ten thousand identical objects built one at a time often want a pool or a baked batch.

### 5. Hide the remainder honestly

Stream the area behind the player rather than lengthen the progress bar. Do not call loading asynchronous while it still blocks the main thread: check the frame times during the load, and if frames stall in lumps, the work is still on the main thread. A load screen should show real progress and cost the minimum the measurements allow.

### 6. Set budgets and gate them

Set per-game numbers; as examples, boot under 15 seconds and a level load under 10 on minimum spec. Run the load scenario in CI on a fixed machine with the same storage class every time, cold-cache, and fail the build when a measured load regresses more than 10 percent against the stored baseline. Move the baseline only deliberately, after a measured improvement, and record the new number in the same change; a baseline that never moves lets later regressions give an earlier gain back, and one that moves every run never sees slow drift. A shared or varying runner makes the gate noise, so use dedicated hardware or report only.

### 7. Report

```markdown
## Setup
[Storage, cache state, build, number of runs.]

## Timeline
[Phase table, cold and warm, with the cold/warm ratio.]

## Changes
[Per phase: what changed, before and after on the worst storage.]

## Budget
[Targets, where enforced, current baseline.]
```

## Anti-patterns

**Timing on the developer machine.** The fast SSD hides the problem the player has.

**Optimising the first thing in the profiler.** Fix the biggest phase on the worst storage, not the most visible one.

**Async in name only.** A loading call that blocks the main thread behind a spinner is still blocking.

**Raising compression to cut I/O.** On a CPU-limited machine this moves the wait rather than removing it.

## References

- `references/load-phases.md` — read at steps 2 to 4: the phase table, how to record access order, and the fix list by phase.
