---
name: shader-compile-stutter
description: "Eliminate hitches caused by shaders, pipeline state objects and materials compiling the first time they appear. Confirms the pattern first (one-off spike per effect, render or driver thread, gone on a second pass with a warm cache), then clears caches and logs every frame over twice the budget with the pipeline created in it, builds a manifest from a real play session, cuts permutation explosion, precompiles during loading with the engine's own mechanism, judges by hitch count over a fixed route, and gates it on a clean-cache CI machine. Use for \"stutter the first time an effect plays\", \"hitches on DX12 but not DX11\", \"first run is bad, second run is smooth\", \"Steam Deck shader cache\", \"PSO precaching\", \"Vulkan pipeline cache\". Not for steady-state CPU or GPU bound frames (game-performance), or texture and mesh import cost (game-assets)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Shader Compile Stutter

The work is done when a player on a clean install runs a fixed route through the game and sees no frame over twice the budget that is attributable to a pipeline being created, and a CI machine with an empty cache fails the build if that stops being true.

The usual failure is treating it as a frame-rate problem. Average frame rate is identical with and without the hitches, so a team optimises draw calls for a week, sees no change, and concludes the stutter is "just DX12". The hitches are a first-use cost: the driver or engine builds a pipeline state object (PSO) or compiles a shader permutation on the frame it is first needed, on the render or driver thread, and the cost is paid once per effect per cold cache. Newer APIs made this worse, not better, because DX12, Vulkan and Metal bake much more state into the pipeline object than DX11 or OpenGL did, so far more combinations have to be built and a driver cannot hide it behind lazy state changes.

## Scope

Use for: hitches that happen the first time something appears, hitches that vanish on a second run, per-API differences in stutter, shader or pipeline cache distribution (including Steam Deck and other fixed-hardware targets), and the build and CI side of keeping a pipeline manifest current.

Do not use for: stutter that recurs every time or at a steady interval, a CPU or GPU bound frame, allocation or garbage-collection spikes (`game-performance` owns "my game stutters" with no first-run pattern), or asset import and streaming cost (`game-assets`).

## Workflow

### 1. Confirm the diagnosis from the pattern

Do this before touching anything. All of these must hold:

- Each hitch happens once per effect, material, or mesh-and-pass combination, not on every appearance.
- The CPU spike is on the render thread or the driver or RHI thread, not gameplay or physics.
- A second pass of the same route, with nothing cleared, is smooth.
- Clearing the cache brings the hitches back in the same places.

If the hitch repeats on every appearance, or is smooth on a cold cache, stop and hand to `game-performance`. A mix is common: fix this class first because it is the one with a clean test.

### 2. Reproduce with a cold cache and a fixed route

Clear both caches, because either can mask the problem: the engine's own pipeline cache (in the project's saved or cache directory) and the driver's on-disk shader cache for the GPU vendor. Reboot is not required; deleting the directories is. Record where each lives on every target, since the driver location differs per vendor and OS.

Run one scripted route, the same each time: a camera path or recorded input that visits every biome, enemy type, weapon and effect the game ships. Log every frame over 2x the frame budget (33.3 ms against a 16.7 ms budget at 60 fps) with the pipeline or material created in that frame. Most engines can log pipeline creation; where the engine cannot, capture with the platform's frame profiler and read the spike's call stack. Keep the log: it is the baseline, and the ranked list of offenders.

Read `references/engine-mechanisms.md` for what to log and which switch to flip per engine.

### 3. Build the manifest from a real session

The manifest is the set of PSOs or shader variants actually used in play, not every one that exists. Record it by playing the route plus a normal session on a development build and capturing every pipeline created. A manifest of everything that could exist is usually far larger, often by orders of magnitude, takes minutes to precompile and pushes load times past what players tolerate.

Cut permutation explosion before precompiling anything. Each unused keyword, quality variant, or platform feature doubles the count of one shader. Strip keywords no material enables, remove variant sets for quality levels you do not ship, and collapse near-duplicate materials onto one shader. This is the cheapest hitch fix there is: a pipeline that does not exist cannot stutter.

### 4. Precompile during loading or a first-launch step

Use the engine's own mechanism, not a hand-rolled warm-up scene, because only the engine knows which state combinations it will request: the Unreal bundled PSO cache and PSO precaching, Unity shader variant collections and warm-up calls, a Vulkan pipeline cache saved and reloaded, Metal binary archives, and Steam's shader pre-caching distribution where the platform offers it. Details and the traps for each are in `references/engine-mechanisms.md`.

Decide the first-run compile-time policy explicitly, because players see it. The choices are:

- Compile everything before first play, behind a progress bar with an honest estimate. Best on a fixed-spec target; a long first launch on a PC with weak CPUs reads as a crash if there is no indicator.
- Compile the next level's subset during that level's loading screen, and ship a pre-built cache for known hardware.
- Compile on background threads during play, accepting that anything not ready is shown with a fallback or delayed one frame. Only acceptable when a missing effect is invisible.

Write the choice, the upper bound on first-launch time, and what happens if the player quits mid-compile into the design record. A cache that was half-written must be detected and rebuilt, not trusted.

### 5. Re-measure and judge on hitches

Repeat step 2 on a cold cache. Compare the count and the worst size of hitches over the route, plus the first-launch duration. Average frame rate will not move and is the wrong judge. A good result is zero hitches attributable to pipeline creation after the loading step; a small remainder is a list of missed manifest entries, so add them and run again.

### 6. Gate it in CI and keep the manifest fresh

Run the route on a dedicated machine whose caches are wiped at the start of every run, on the weakest GPU vendor you support, and fail the build when hitches over the route exceed a fixed number (start from the post-fix count and ratchet it down, never up). The gate matters because new content brings new materials and the hitches creep back one effect at a time.

Refresh the manifest whenever content or shader code changes, as a build step, never by hand. Stale manifests fail silently: the game still runs, the new effects simply hitch again.

## Hand back

The cold-cache baseline log and the after log with hitch count, worst hitch and first-launch time; the manifest size before and after the permutation cut; the chosen first-run policy; and the CI gate threshold and where it runs. Anything that survived as a recurring hitch goes to `game-performance` with the logged frames attached.

## Anti-patterns

**Judging by average frame rate.** It does not move, so the fix looks like it did nothing.

**Warming up with a hidden scene full of every object.** It builds pipelines the game never uses, misses the ones it does, and still happens on the render thread in a frame the player may see.

**Testing only on the developer's machine.** The developer's driver cache has been warm for months. Every hitch is invisible there.

**Shipping a cache without a version key.** A driver or GPU change invalidates it silently, and the player gets the cold-cache game with no warning. Key it by driver version and rebuild on mismatch.

## References

- `references/engine-mechanisms.md` - read at steps 2 and 4: what to log, the switch or call per engine and API, cache locations and invalidation.
