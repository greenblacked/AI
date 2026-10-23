# Budget template and capture tools

Read this at steps 1 and 2 of `SKILL.md`. It has the table to copy, where each platform's ceiling comes from, and how to capture the figure that matters.

## Contents

- [The budget table](#the-budget-table)
- [Where the ceiling comes from](#where-the-ceiling-comes-from)
- [Capturing on each target](#capturing-on-each-target)
- [Checkpoint script outline](#checkpoint-script-outline)
- [Reading a staircase](#reading-a-staircase)

## The budget table

Keep it in the repository as data so CI can read it. One row per system, one block per target.

```text
target: lowest-supported-phone
ceiling_mb: 1400        # measured: highest footprint before the OS kills the process
reserve_mb: 350         # OS, runtime, engine fixed cost (empty scene, release build)
headroom_mb: 105        # 10 percent of the remainder, not allocated
system        owner       budget_mb   peak_mb   checkpoint
textures      art         415         0         level-load
meshes        art         120         0         level-load
audio         audio       90          0         level-load
animation     tech-art    60          0         level-load
scripting     gameplay    140         0         mid-level
ui            ui          50          0         main-menu
physics       gameplay    40          0         mid-level
networking    online      30          0         mid-level
```

The sample numbers are illustrative; the sum of budgets plus reserve plus headroom must equal the ceiling. Add a row for any system the game has that this list does not. Record `peak_mb` from the measured soak, and a date and build id beside the table.

## Where the ceiling comes from

- **Console**: the platform holder's documentation for the title's memory limit and for what the system reserves. It sits behind the developer programme, so read it there, and record the figure and its source in the table.
- **iOS**: there is no single published limit; it varies by device and OS version. Find the limit empirically on the lowest supported device by raising allocation in a test build until the process is terminated, and record the footprint at termination. Use `os_proc_available_memory()` at runtime to confirm the headroom.
- **Android**: the limit depends on the device's total memory, other resident apps and the low-memory killer thresholds. Test on the lowest supported device with a few other apps open. `ActivityManager` reports a memory class for the app's heap limit, which is one limit but not the killer's.
- **Desktop**: the minimum specification the store page promises. The ceiling is that machine's memory minus what the operating system and typical background applications use.
- **Browser**: the tab's practical limit is smaller than the machine's memory and varies by browser, especially on mobile. Measure on the lowest supported browser and device.

## Capturing on each target

Android, from a connected device, with the app running:

```bash
adb shell dumpsys meminfo com.example.game
```

The summary lists Java heap, native heap, graphics, code and total PSS. Run it at each checkpoint and keep the output with the build id.

Linux desktop, peak and current resident memory of a running process:

```bash
grep -E 'VmHWM|VmRSS' /proc/<pid>/status
```

`VmHWM` is the high-water mark, which is the peak. Read it after each checkpoint.

Engines, for attribution once the OS figure says there is a problem:

- **Unity**: the Memory Profiler package takes snapshots and compares two of them; capture from a development build on the device. Use it to diff loop 2 against loop 20.
- **Unreal**: `memreport -full` writes a report of allocations by category; `stat memory` shows live counters; the low-level memory tracker (started with `-llm`) attributes memory to tags, and `stat llm` shows them. Compare reports from two checkpoints.
- **Godot**: `Performance.get_monitor(Performance.MEMORY_STATIC)` and the other memory monitors give the counts at runtime; the debugger's monitors graph them. Log them at each checkpoint.
- **iOS**: Instruments with the Allocations and VM Tracker templates, with generations marked at each checkpoint to see what survived.

## Checkpoint script outline

The soak must run the same steps every time or its points are not comparable.

1. Start the release build with a fixed seed and a fixed save.
2. Reach the main menu; sample (checkpoint `menu-0`).
3. For `i` in 1 to 20: load the level; sample at load complete (`load-i`); run a scripted minute through the same route; sample (`mid-i`); unload to the menu; sample (`menu-i`).
4. Write one row per sample: build id, iteration, checkpoint, OS figure, engine figure.

Fail the soak when the slope of `menu-i` over the last ten iterations exceeds the agreed amount per loop, or any sample exceeds its budget by the margin.

## Reading a staircase

- **Rises per loop by about the same amount, never flattens**: a leak. The diff of loop 2 and loop 20 names it.
- **Rises for the first three to five loops, then flat**: caches and pools warming up. Budget for the plateau.
- **Rises and falls irregularly with no trend**: allocator and collector timing. Look at peaks rather than the trend, and consider a fixed arena.
- **Flat in the engine's counter, rising in the OS figure**: native memory the engine does not count, or fragmentation. Check native plugins, driver allocations and the allocator's own overhead.
- **Rises only after a particular action**: the leak is on that path; bisect the scripted minute.
