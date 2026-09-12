---
name: game-performance
description: "Make a game hold a frame budget on the hardware it ships to. Convert the target frame rate into a per-frame millisecond budget, capture frame times from a real build on the target device, judge the 1% low and the 99th percentile rather than an average, prove whether the frame is CPU-bound or GPU-bound before changing anything, then attack that side alone — draw calls, per-frame allocation and garbage-collection hitches, physics tick rate, overdraw, fill rate, shadows, texture bandwidth — one change at a time, re-measuring after each. Use this skill whenever a game stutters, hitches, drops frames or misses its target frame rate: \"my game stutters\", \"frame drops on the steam deck\", \"why is this 20fps on mobile\", \"GC spike every few seconds\", \"is this CPU or GPU bound\". Not for building a game or fixing floaty controls, and not for server or backend latency."
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(godot:*), Bash(python:*), Bash(node:*), Bash(git:*)
---

# Game Performance

A game that holds its budget on the worst device it claims to support, measured from a build on that device, with the number that failed and the number that replaced it both written down.

Frame-rate work goes wrong in two predictable ways. The first is optimising the wrong half of the frame: a week spent on multithreading the AI in a game whose GPU was drawing the same pixel eleven times, which is the most common wasted week in this discipline and is entirely preventable by a ten-minute measurement. The second is optimising for the wrong statistic: an average frame rate that reads 60 while the player feels a stutter every few seconds, because the average is computed over exactly the frames that were fine. This skill exists to stop both, by fixing the budget in milliseconds first, measuring the distribution rather than the mean, and naming the bound before touching a line of code.

## Scope

Use for: a game missing its frame rate, stuttering, hitching or dropping frames; a frame-time regression; deciding whether the target hardware can run what is being built; a performance pass before a release or a platform certification.

Do not use for: building a game, choosing an engine, or fixing controls that feel floaty or unresponsive, which is `game-builder` — a floaty jump at a steady 16 ms is a design problem, not a performance one. A wrong result rather than a slow one is `debugging`. Server frame time, matchmaking latency, tick-rate cost on a dedicated server and load headroom are `capacity-planning` and `instrumentation`.

## Workflow

### 1. Fix the budget in milliseconds, on named hardware

Frames per second is a rate, and rates do not add up: you cannot subtract 5 fps from a budget, but you can subtract 5 ms. Convert before anything else.

| Target | Frame budget | Typical reason |
| --- | --- | --- |
| 30 fps | 33.3 ms | Console quality mode, low-end mobile |
| 40 fps | 25.0 ms | Handhelds with a 40 Hz mode, such as the Steam Deck LCD |
| 60 fps | 16.7 ms | The default expectation for anything with a character in it |
| 72 fps | 13.9 ms | Standalone VR floor |
| 90 fps | 11.1 ms | VR comfort, high-refresh handhelds |
| 120 fps | 8.3 ms | Console performance mode, competitive play |

Then write down three things and get them agreed before measuring:

- **The device.** Not "PC" — the specific worst machine the game claims to run on. Steam Deck, iPhone SE, a 2019 laptop with integrated graphics, base PS5. Budgets are meaningless without one.
- **The resolution and settings** that device runs at, because GPU cost scales with pixels and a budget at 720p says nothing about 1440p.
- **The working budget**, which is the frame budget minus headroom. Take 80% of it on anything that throttles — handhelds, phones, laptops — because a device that holds 16 ms cold drops to 20 ms once it is warm. Measure after ten minutes of play, not thirty seconds.

Anything the frame has to do that is not the game — the compositor, an overlay, a recording hook — comes out of the same budget.

### 2. Measure a build on the target device

The editor is not the game. Its numbers are wrong in a specific and unhelpful direction: it renders the scene view as well as the game view, it runs interpreted or debug-configuration scripts rather than the optimised build, it holds every asset uncompressed with hot-reload watchers attached, it compiles shaders on first use so hitches appear that a cooked build never has, and it is running on a workstation rather than the thing in the player's hands. The result is a mix of costs that do not exist in the build and costs that are hidden in the editor, which is why an editor profile can point at exactly the wrong system.

Profile in the editor only to get a first list of suspects. Confirm every one of them on the device, from a build, before acting on it. `references/profilers.md` has the exact build flags and connection steps per engine — read it before capturing.

Two setup details decide whether the capture means anything:

- **Uncap the frame rate** for the diagnostic capture. A vsync-locked 60 tells you the frame took at most 16.7 ms, not whether it took 16 or 5, so it hides all your headroom and every near-miss. Cap it again before judging perceived smoothness, because tearing and pacing are their own problem.
- **Capture real play**, two minutes minimum, including the scenes people complain about — the wave spawn, the boss room, the busy town. A capture of an empty menu is an empty capture.

### 3. Judge the distribution, not the mean

Export the per-frame times and compute: mean, 95th percentile, 99th percentile, the 1% low, the single worst frame, and the count of frames over budget. The 1% low as the community uses it is the mean of the worst 1% of frames; the 99th percentile frame time is the same idea from the other end, and either one is what the player actually feels.

```python
frames = sorted(ms)  # per-frame times in milliseconds, from the capture export
p99 = frames[int(len(frames) * 0.99)]
one_percent_low = sum(frames[int(len(frames) * 0.99) :]) / max(
    1, len(frames) - int(len(frames) * 0.99)
)
over = sum(1 for f in ms if f > budget_ms)
```

The pass condition is a sentence, not a vibe: *99th percentile under the working budget, and no frame over twice the budget outside a level load.* A game averaging 12 ms with a 180 ms hitch every eight seconds passes every average-based check and is the one players call unplayable, because a single frame four times over budget is visible and a thousand frames slightly under are not.

Keep the raw capture. It is the before number, and without it the after number proves nothing.

### 4. Prove the bound before changing anything

Every fix below belongs to one side of the frame. Applying a CPU fix to a GPU-bound frame changes nothing, which is usually read as "the optimisation did not help much" rather than "this was the wrong half".

The fast tell per engine — `stat unit` in Unreal, the wait markers in the Unity Profiler, the Visual Profiler in Godot, the main-thread flame chart against the GPU track in Chrome — is in `references/cpu-or-gpu.md`, along with the two engine-independent experiments that settle it when the tooling is unavailable: halve the render resolution, and halve the entity count, separately, and see which one moves the frame time. Read it at this step and record the verdict, the evidence and the number in one line before continuing.

A frame can also be bound by neither in the steady state and still hitch. A periodic spike with a low average is an event — garbage collection, an asset load, a shader compile, a physics catch-up — and the diagnosis is the frequency and the alignment of the spike, not the average load. `references/cpu-or-gpu.md` covers that case too.

### 5. Fix the bound side, one change at a time

`references/frame-costs.md` is the catalogue: every common cost on each side, how to confirm it is yours, and the fix with a starting number. The short version of what is usually there:

- **CPU** — draw call and batching behaviour, per-frame allocation causing garbage-collection hitches in C# and GDScript, a physics tick rate set faster than the game needs, and per-frame work that belongs in a cache or spread across frames.
- **GPU** — overdraw and layered transparency, fill rate at the target resolution, shader complexity, shadow-casting light count, and texture bandwidth.

Order by measured cost, not by how interesting the fix is. Then change one thing, re-capture on the device, and compare the 99th percentile — not the average, and not the feel. Two changes at once and a win of 4 ms tells you nothing about which one to keep, and one of them is often negative.

Re-capture twice before believing a small win. A 3% improvement is inside the run-to-run variance of a thermally throttling device.

### 6. Lock it in

A budget that is met once is met until the next content drop.

- Record the pass condition, the device and the numbers in the repository, next to the code, so the next person knows what the budget was.
- Keep one repeatable capture route: a scripted replay, a benchmark scene, or a written five-step path through the busiest level. A capture nobody can repeat cannot show a regression.
- When frame time regresses and the capture route is repeatable, `git bisect` over it is faster than reading the diff, because the cost is usually in an asset or a setting rather than in code.

### 7. Report

```markdown
## Budget
[Device, resolution and settings, target frame rate, budget in ms, working budget.]

## Before
[Mean, p99, 1% low, worst frame, frames over budget, and how the capture was taken.]

## Bound
[CPU or GPU, the evidence that proved it, and the specific thing that dominated.]

## Changes
[One line per change: what, the measured delta in ms at p99, and what it cost in quality.]

## After
[The same statistics as Before, from the same capture route.]

## Still over, or at risk
[What remains, what it would cost to fix, and what will break the budget next.]
```

## Anti-patterns

**Micro-optimising before profiling.** Rewriting a function into branchless arithmetic to save 0.2 ms of a 40 ms frame, while a shadow cascade costs 14 ms. The reason this is so common is that the micro-optimisation is the fun part and needs no measurement; it is also the part that makes the code harder to change for the rest of the project.

**Pooling everything by reflex.** Object pooling is the right fix for a profile that shows allocation in the update path, and a source of new bugs everywhere else: a pooled object carries the previous owner's state, so respawned enemies keep old health, particles restart mid-animation, and the leak becomes a stale-state bug that reproduces once in fifty. Pool what the profiler named — usually projectiles, particles and enemies — and leave the rest.

**Chasing average frame time.** The average is dominated by the frames that were already fine. Optimise for the worst 1%, because that is the set the player perceives as the game's performance.

**Trusting the editor's number.** Covered in step 2 and worth repeating because it is the easiest mistake to make: editor overhead and editor-only costs push the profile toward different systems than the build does, so an editor-guided fix can be measurably correct and completely irrelevant.

**Turning on every optimisation setting at once.** Batching, occlusion culling, LOD bias, texture compression and a lower shadow distance applied in one commit produce a win nobody can attribute and a visual regression nobody can bisect. One at a time, with a number each.

**Optimising for the machine under your desk.** A developer workstation hides every cost that matters on an integrated GPU or a phone, and it hides them in the direction that makes the game ship broken.

**Declaring victory from one run.** Thermal state, background processes and shader caches move the number. Two clean captures agreeing, or it did not happen.

## References

- `references/cpu-or-gpu.md` — read at step 4, before any fix: the per-engine tell for CPU-bound versus GPU-bound, the two engine-independent experiments, and how to diagnose a periodic hitch that has no steady-state bound.
- `references/profilers.md` — read at step 2, before capturing: how to open, connect and export from the Unity Profiler, Unreal Insights and `stat unit`, Godot's debugger and visual profiler, and Chrome DevTools, plus the device-side tools and the build flags each one needs.
- `references/frame-costs.md` — read at step 5, once the bound is known: the CPU and GPU cost catalogue, how to confirm each one, and the fix with a starting number.
