# Profilers, per engine and per platform

Read this at step 2, before capturing anything. Each section gives the way to open the profiler, the build settings that make a device capture possible, and what to export so the numbers in `cpu-or-gpu.md` and `frame-costs.md` can be read off it.

The rule that outranks every tool here: profile a build, on the target device, during real play. The editor sections exist to shortlist suspects, not to judge them.

## Contents

- [Unity](#unity)
- [Unreal](#unreal)
- [Godot 4](#godot-4)
- [Browser games](#browser-games)
- [Device and vendor tools](#device-and-vendor-tools)
- [Steam Deck and handhelds](#steam-deck-and-handhelds)
- [Exporting frame times](#exporting-frame-times)

## Unity

**Open it.** Window > Analysis > Profiler (Ctrl+7, Cmd+7 on macOS). The CPU Usage module's Timeline view is the one to read; the Hierarchy view hides which thread was waiting, and the wait markers are the diagnosis.

**Build for profiling.** In File > Build Settings — File > Build Profiles in Unity 6 — enable **Development Build** and **Autoconnect Profiler**. Enable **Deep Profiling Support** only when you need per-call detail, because it adds enough overhead to change which function looks expensive. Leave the build otherwise identical to release: the same scripting backend, the same stripping level, the same compression.

**Connect to the device.** The Profiler window's target dropdown lists development players on the local network; pick the player rather than Editor, and confirm the label changes. Over USB on Android, forward the port first:

```bash
adb forward tcp:34999 localabstract:Unity-com.yourcompany.yourgame
```

**Capture without the editor.** A development player accepts profiler arguments, which is how you get a capture from a machine the editor cannot reach:

```bash
./YourGame.x86_64 -profiler-enable -profiler-log-file capture.raw -profiler-capture-frame-count 1800
```

Open the resulting file with the Profiler window's Load button.

**The supporting views.**

- Game view toolbar > Stats: batches, SetPass calls, triangles and vertices, live.
- Window > Analysis > Frame Debugger: steps through every draw call in one frame, which is how you find the material that broke batching.
- The **Profile Analyzer** package compares two captures frame by frame and gives a median and percentile per marker, which is the right tool for before-and-after.
- The **Memory Profiler** package for a snapshot when the question is allocation rather than time.

## Unreal

**The first command.** In the console (backtick), `stat unit`. Four numbers plus the total, and the largest of Game, Draw and GPU is the bound. `stat unitgraph` plots them over time so a spike can be attributed. Before reading either, `t.MaxFPS 0` and `r.VSync 0`, or every number is clamped to the refresh interval.

**The next commands, by side.**

| Command | Answers |
| --- | --- |
| `stat gpu` | Which render pass owns the GPU time: base pass, shadow depths, lighting, post |
| `ProfileGPU` | One frame in the GPU Visualizer, drilled down to individual draws |
| `stat scenerendering` | Draw call counts, visible sections, culling work |
| `stat game` | Tick cost by group on the game thread |
| `stat rhi` | Render hardware interface counts and memory |
| `viewmode shadercomplexity` | Where pixel shader cost is concentrated, as a heat map |
| `viewmode quadoverdraw` | Overdraw, including the hidden cost of dense small triangles |

The view modes are also in the viewport under View Mode > Optimization Viewmodes.

**Unreal Insights.** The real profiler, and the one that works against a packaged build on a device. Launch the game with tracing on:

```bash
YourGame.exe -trace=cpu,gpu,frame,bookmark,log -statnamedevents
```

That writes a trace file next to the build, which the Unreal Insights application (in the engine's `Binaries` directory) opens. To watch a device live instead, add `-tracehost=<workstation-ip>` to the game and start Insights first. `-statnamedevents` is what gives the CPU timeline readable scope names; without it the trace is technically complete and practically unreadable.

## Godot 4

**Open it.** Run the project from the editor and use the Debugger bottom panel. Three tabs matter:

- **Profiler** — CPU frame time attributed to functions and to engine steps, with `Process` and `Physics Process` separated. Sort by Self time, not Total.
- **Visual Profiler** — CPU and GPU time per frame side by side, broken down by rendering pass. This is the direct CPU-versus-GPU comparison.
- **Monitors** — frames per second, process and physics process time, draw calls per frame, objects and primitives drawn, video memory, static memory.

**Profiling an exported build.** The editor's debugger listens on port 6007 by default, so a build can connect back to it:

```bash
./your-game --remote-debug tcp://127.0.0.1:6007
```

For a phone or a console-like device, use Debug > Deploy with Remote Debug in the editor, which exports, deploys and points the build's debugger at the workstation. Keep Debug > Keep Debug Server Open on when you want to relaunch without re-exporting.

**In code, for a build with no debugger attached.** The counters are available at runtime, so a build can log its own frame times:

```gdscript
var cpu_ms := Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
var physics_ms := Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
var draws := Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
```

**Overdraw and shading.** In the 3D viewport, the view menu in the top-left corner (labelled Perspective) has Display Overdraw, Display Wireframe, Display Unshaded and Display Lighting. Overdraw is the one that finds layered transparency.

Uncap the frame rate for a diagnostic run with `Engine.max_fps = 0` and V-Sync set to Disabled under Project Settings > Display > Window > V-Sync.

## Browser games

**Record.** Open DevTools (F12), go to the Performance panel, and record with Ctrl+E (Cmd+E) or the record button. Five to ten seconds of real play is plenty; the panel gets hard to read past that. Read the Frames track for actual frame durations, the Main track for the JavaScript flame chart, and the GPU track underneath for the other half.

**The frame timing that matters is `requestAnimationFrame`.** The callback's argument is the frame's timestamp, so the delta between consecutive callbacks is the frame interval as the compositor produced it, and it is the only number that corresponds to what the player sees. `setInterval` and a frame counter both lie: one is not tied to the display, the other averages.

```javascript
let last = 0;
const frames = [];
function tick(now) {
  if (last) frames.push(now - last);   // frame interval, the number the player feels
  last = now;
  const start = performance.now();
  update();
  render();
  frames.work = performance.now() - start;  // your share of it
  requestAnimationFrame(tick);
}
```

The gap between the interval and your own work is everything the browser did: style, layout, paint, composite, and garbage collection.

**The rest of the toolkit.**

- Command menu (Ctrl+Shift+P) > Show Rendering > Frame Rendering Stats, for a live overlay, plus Paint flashing for unexpected repaints in DOM-based games.
- The Performance panel's long-task and layout-shift markers, and `PerformanceObserver` on the `long-animation-frame` entry type for logging the same thing from a shipped build.
- Memory panel > Allocation sampling to find per-frame garbage; a sawtooth in the Performance panel's memory track with hitches on each drop is the giveaway.
- `chrome://gpu` to confirm hardware acceleration is actually on, before concluding the GPU is slow.

## Device and vendor tools

Reach for these when the engine profiler says GPU and you need to know which draw.

| Platform | Tool | Use it for |
| --- | --- | --- |
| Windows, Vulkan, D3D12 | RenderDoc | Single-frame capture, per-draw timing, overdraw and state inspection |
| Windows, D3D12 | PIX | Frame and timing capture with GPU counters |
| NVIDIA | Nsight Graphics | Frame capture and hardware counters |
| AMD | Radeon GPU Profiler | Wavefront occupancy, where a shader stalls |
| iOS, macOS | Xcode Instruments, Metal debugger | GPU counters, shader cost, thermal state |
| Android | Android GPU Inspector | Frame capture and GPU counters on supported devices |
| Qualcomm | Snapdragon Profiler | Per-stage GPU counters on Adreno |
| Arm | Arm Performance Studio | Bandwidth and cache counters on Mali |

A single-frame capture answers "which draw", not "which frame". Pick the frame to capture from the engine profiler first.

## Steam Deck and handhelds

The built-in overlay is enough for the first pass and needs no development build. Open the Quick Access menu, go to Performance, and raise the Performance Overlay Level to 4: frame time graph, CPU and GPU utilisation, clocks, power draw and temperature, live.

Read it for three things the desktop cannot show you:

- **The frame time graph**, not the frame rate number, for the same reason percentiles beat averages.
- **GPU utilisation near 100% with CPU low**, or the reverse, as a first cut at the bound before a real profiler is attached.
- **Sustained versus opening minutes.** A handheld shares a power budget between CPU and GPU and throttles as it warms. Play for ten minutes before writing any number down, and note the frame rate cap the device is set to, because a game locked to 40 Hz has a 25 ms budget and looks fine at 24 ms right up until a wave spawns.

## Exporting frame times

Every path above can produce per-frame timings; the statistics in step 3 need them as a plain list.

- Unity: the Profiler window's Frame Charts export, or `ProfilerRecorder` writing a CSV from the build itself.
- Unreal: Insights exports timing data, and `csvprofiler` commands write a CSV per frame for offline analysis.
- Godot: log `Performance.get_monitor` values per frame to a file from the build.
- Browser: the array from the snippet above, dumped to the console or posted to a local endpoint.

Whatever produces them, keep the raw file. The before capture is the only evidence that a change helped.
