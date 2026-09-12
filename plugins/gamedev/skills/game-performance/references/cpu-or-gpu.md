# Is the frame CPU-bound or GPU-bound

Read this at step 4, before applying any fix. The frame is produced by two processors working in a pipeline, and the one that finishes last sets the frame time. Every fix in `frame-costs.md` belongs to one side; applied to the other it changes nothing, and "it barely helped" gets recorded as a property of the fix rather than of the diagnosis.

## Contents

- [What bound means](#what-bound-means)
- [The engine tells](#the-engine-tells)
- [The two experiments that settle it](#the-two-experiments-that-settle-it)
- [When the answer is neither: periodic hitches](#when-the-answer-is-neither-periodic-hitches)
- [Recording the verdict](#recording-the-verdict)

## What bound means

A frame runs roughly as three stages that overlap across frames: the game thread simulates, the render thread translates the scene into commands for the graphics API, and the GPU executes them. Because they overlap, the frame time is close to the longest of the three rather than their sum. The longest one is the bound, and lowering anything else moves nothing until it becomes the longest.

Three consequences worth holding on to:

- **CPU-bound** means the GPU spent part of the frame idle, waiting for work. Lowering the resolution will not help. Reducing draw calls, allocation or per-frame logic will.
- **GPU-bound** means the game thread finished early and then blocked waiting to submit or present. Optimising AI will not help. Lowering resolution, overdraw, shader cost or shadow work will.
- **Render-thread-bound** is a third case that looks like CPU-bound and is not fixed like it. The game thread is fine and the GPU is fine, but the thread building draw commands cannot keep up — almost always too many unique draws. Unreal separates it explicitly as `Draw`; Unity shows it as a render-thread timeline longer than the main thread; in Godot 4 and in browsers the equivalent cost mostly sits in the same measurement as the rest of the CPU frame.

## The engine tells

**Unreal.** The console command `stat unit` is the whole diagnosis in one line. It prints `Frame`, `Game`, `Draw`, `GPU` and `RHIT`. `Frame` is the total; the largest of `Game` (game thread), `Draw` (render thread) and `GPU` is the bound, and it will sit very close to `Frame`. Add `stat unitgraph` to see the four values over time, which is how a spike gets attributed. Disable the frame cap first with `t.MaxFPS 0` and `r.VSync 0`, or every number is pinned to the refresh interval and the comparison is meaningless.

**Unity.** Open the Profiler with Window > Analysis > Profiler and look at the CPU Usage module's timeline view, not the hierarchy. The tell is which thread is waiting:

- The main thread sitting in `Gfx.WaitForPresentOnGfxThread` means it has run out of work and is waiting on the render thread and the GPU. That is GPU-bound or render-thread-bound.
- The render thread sitting in `Gfx.WaitForGfxCommandsFromMainThread` means the opposite: the GPU and render thread are starved while the main thread simulates. That is CPU-bound.
- Neither waiting much, with both busy across the whole frame, means the two are balanced and both need work.

The GPU Usage module adds a GPU time per frame when the platform supports it; where it does not, the wait markers are still the answer.

**Godot 4.** The Debugger bottom panel has the two views you need. The Profiler tab attributes CPU frame time to functions and to the engine's own steps, with `Physics Process` and `Process` broken out. The Visual Profiler tab shows CPU and GPU time per frame side by side, which is the direct comparison — a GPU bar longer than the CPU bar is a GPU-bound frame. The Monitors tab carries the supporting counters: frames per second, draw calls per frame, objects drawn, video memory.

In code, `Performance.get_monitor(Performance.TIME_PROCESS)` and `Performance.TIME_PHYSICS_PROCESS` give the CPU halves of the frame, so a build can log them without the editor attached.

**Browser.** Open DevTools, go to the Performance panel and record a few seconds of play. Then read two tracks against each other: the main thread's flame chart under each animation frame, and the GPU track below it. Long `requestAnimationFrame` callbacks with a short GPU track is CPU-bound JavaScript; a short callback with the frame still stretching to 30 ms is the GPU or the compositor. The Frames track above both shows the actual frame durations, and hovering a long frame names what delayed it.

`requestAnimationFrame` timing is what matters here, not `setInterval` and not an FPS counter: the callback receives the frame's timestamp, so the interval between consecutive callbacks is the true frame time as the compositor saw it. Measure the work inside the callback with `performance.now()` at its start and end — the difference between that and the callback-to-callback interval is everything the browser did that your code did not.

You cannot uncap a browser game the way you can uncap an engine build; `requestAnimationFrame` is bound to the display refresh. That is why the inside-the-callback measurement matters: it is the only way to see headroom.

## The two experiments that settle it

They need no profiler at all and they work in every engine. Run them one at a time, from a build, on the target device, and compare against the same capture route.

**Halve the pixels.** Drop the render resolution to 50%, or the window to a quarter of its area. In Unreal, `r.ScreenPercentage 50`. In Unity, lower `ScalableBufferManager` scale or simply run the build at a lower resolution. In Godot, set the viewport scale (Project Settings > Rendering > Scaling 3D > Scale, or `Viewport.scaling_3d_scale`). In a browser, shrink the canvas backing store while keeping its CSS size.

- Frame time improves substantially: GPU-bound, and most likely fill rate, overdraw or a full-screen pass.
- Frame time barely moves: not fill-bound. Either CPU-bound, or GPU-bound on something resolution-independent such as vertex processing, shadow map rendering or too many draws.

**Halve the work.** Put back the resolution, then remove half the entities, or disable AI, or stop the physics simulation.

- Frame time improves substantially: CPU-bound on simulation or on the per-entity draw submission that came with those entities.
- Frame time barely moves: the cost is in the scene, not the population.

The pair together is diagnostic where either alone is ambiguous: an entity carries both a CPU cost and draw calls, so the second experiment can move a render-thread-bound frame. Resolution does not, which is why it is the first one.

## When the answer is neither: periodic hitches

A steady 8 ms frame with a 200 ms spike every few seconds has no steady-state bound to find. The diagnosis is the pattern, not the load.

| Pattern | Almost always | Confirm by |
| --- | --- | --- |
| Regular spike every few seconds, memory graph sawtooths up to each one | Garbage collection from per-frame allocation | Memory timeline aligned to the hitch; an allocation profile of the update path |
| Spike exactly when something appears for the first time | Shader or pipeline compilation | It happens once per effect per session and never again after a warm-up pass |
| Spike when a thing spawns, every time | Instantiation, asset load or scene load at spawn | Profile the spawn call; check whether the asset is loaded synchronously |
| Spike after a slow frame, then a run of slow frames | Physics catch-up: the step budget is being exhausted and steps pile up | Physics step count per frame; the max-steps setting |
| Spike on a timer with no visible cause | Autosave, telemetry flush, an analytics upload, a level-streaming boundary | Log the timer; correlate the timestamps |
| Spike only on the device, never on desktop | Thermal throttling or a memory-pressure event | Frame times over ten minutes; the platform's thermal state API or overlay |

Fix hitches before steady-state cost. A player forgives a consistent 40 fps and does not forgive a 60 that stutters, and the hitch is usually one setting or one allocation rather than a system rewrite.

## Recording the verdict

Write one line before continuing, because this is the fact every later decision depends on and the one people forget they assumed:

```text
GPU-bound at 1280x800 on Steam Deck: stat unit shows GPU 24.1 ms, Game 9.2 ms, Draw 7.8 ms,
frame 24.3 ms. Screen percentage 50 drops the frame to 13.2 ms, confirming fill rate.
```

If the verdict changes after a fix — and it should, because fixing the bound side eventually exposes the other — re-run this page rather than continuing down the old list. Optimising past the crossover point is effort spent on a side that is no longer setting the frame time.
