# The frame cost catalogue

Read this at step 5, after `cpu-or-gpu.md` has named the bound. Work only the side that is bound, in order of measured cost, one change at a time with a re-capture after each.

Every entry has the same three parts: how it shows up, how to confirm it is yours rather than plausible, and the fix with a number to start from. The confirmation step is not optional — half the entries here are the obvious explanation for a symptom they did not cause.

## Contents

- [CPU: draw calls and batching](#cpu-draw-calls-and-batching)
- [CPU: per-frame allocation and garbage collection](#cpu-per-frame-allocation-and-garbage-collection)
- [CPU: physics tick rate](#cpu-physics-tick-rate)
- [CPU: per-frame work that belongs in a cache](#cpu-per-frame-work-that-belongs-in-a-cache)
- [GPU: overdraw and transparency](#gpu-overdraw-and-transparency)
- [GPU: fill rate and resolution](#gpu-fill-rate-and-resolution)
- [GPU: shader complexity](#gpu-shader-complexity)
- [GPU: shadows and lights](#gpu-shadows-and-lights)
- [GPU: texture bandwidth](#gpu-texture-bandwidth)
- [Fixes that cost quality](#fixes-that-cost-quality)

## CPU: draw calls and batching

**Shows up as** frame time that rises with the number of visible objects but not with the amount of logic, a render thread longer than the game thread, and a draw call count in the thousands on hardware that wants hundreds.

**Confirm** with the renderer's own counter: SetPass calls in Unity's Game view stats, `stat scenerendering` in Unreal, the draw calls monitor in Godot. Then find what breaks the batch — Unity's Frame Debugger names the reason per draw, and it is nearly always a unique material instance, a different texture, or a per-object shader parameter.

**Fix.** Atlas textures so objects share one material. Use instancing for repeated meshes rather than copies. Mark static geometry static so it can be combined. Merge small props into one mesh per room or chunk. Cut per-object material property changes, which silently make every object its own batch.

**Starting numbers.** Low-end mobile and handheld: aim under about 200 draw calls per frame, and treat 500 as a problem to solve. Desktop absorbs several thousand, and it is still the cheapest millisecond you will ever recover.

## CPU: per-frame allocation and garbage collection

**Shows up as** a good average with a periodic hitch: 8 ms frames and a 60 to 300 ms spike every few seconds, worse the longer play continues.

**Confirm** by aligning the memory graph with the spikes. A sawtooth that climbs steadily and drops at each hitch is garbage collection, and an allocation profile of the update path names the line. A hitch with a flat memory graph is something else — go back to the hitch table in `cpu-or-gpu.md`.

**Fix.** The allocation sources are boringly consistent:

- **C#**: LINQ in `Update`, string concatenation or interpolation for UI labels every frame, boxing when iterating a collection as an interface, a `new` array or list per frame, closures captured in a per-frame lambda, `GetComponent` and `Find` in the update path, and physics queries that return arrays instead of filling a buffer.
- **GDScript**: arrays and dictionaries built per frame, string formatting for debug output left in a release build, and per-frame `get_node` when the node could be cached in `_ready`.

The fixes are the mirror image: hoist buffers out of the loop and reuse them, cache component and node references once, use the non-allocating overload of physics queries, update UI text on change rather than per frame, and keep per-frame strings out of release builds entirely.

Pool only what a profile shows allocating in the loop — see the pooling anti-pattern in the skill body, because pooling by reflex trades a measured cost for an unmeasured class of stale-state bug.

## CPU: physics tick rate

**Shows up as** a spike immediately after a slow frame, then a run of slow frames, or a steady cost that scales with body count rather than with anything visible.

**Confirm** by reading the physics step count per frame and the physics share of the frame in the profiler. If the engine ran three or four steps in one frame, it is catching up: the render frame overran the physics interval, so the next frame owes extra steps, which makes it longer again.

**Fix.**

- **Lower the tick to what the game needs.** Unity defaults `Time.fixedDeltaTime` to 0.02, which is 50 Hz; Godot defaults `physics/common/physics_ticks_per_second` to 60. A turn-based or slow-moving game runs fine at 20 or 30 and halves the cost. A twitch platformer with fast projectiles wants it high — that is a design decision, not a performance one, so make it deliberately.
- **Cap the catch-up.** Godot's `physics/common/max_physics_steps_per_frame` and Unity's Maximum Allowed Timestep exist to convert a death spiral into a brief slowdown. Confirm they are set rather than assuming.
- **Reduce what is simulated.** Let resting bodies sleep, filter the collision layer matrix so pairs that can never touch are never tested, keep continuous collision detection for fast small objects only, and use simple convex shapes rather than mesh colliders for anything that moves.
- **Do not raytrace the world every frame** from every entity. Stagger checks across frames.

## CPU: per-frame work that belongs in a cache

**Shows up as** frame time proportional to entity count, with no single expensive function — the cost is spread across many cheap ones called too often.

**Confirm** in the profiler's self-time ranking, and by plotting frame time against entity count. A straight line is per-entity work; a curve that bends upward is an O(n²) pattern, usually every entity checking distance to every other.

**Fix.** Three moves cover most of it:

- **Spread it.** Pathfinding, line of sight, target selection and AI decisions rarely need to run every frame for every agent. Run a fixed slice per frame — say 20 agents of 200 — so the cost is bounded and constant rather than proportional.
- **Cache it.** Component and node lookups, transform hierarchies, sorted lists, formatted strings and computed bounds. Anything derived from data that changes rarely should be computed when it changes.
- **Partition it.** A spatial grid or quadtree turns "every entity against every entity" into "every entity against its neighbours". This is the fix for the upward-bending curve, and nothing else will do.

Polling is the pattern underneath most of this: a check that runs every frame to notice something that happens twice a minute. Make it an event or a timer.

## GPU: overdraw and transparency

**Shows up as** frame time that collapses when the camera looks at the sky and rises in dense scenes, particle-heavy moments, or anywhere with layered smoke, foliage or UI.

**Confirm** with the overdraw view: Display Overdraw in Godot's viewport menu, `viewmode quadoverdraw` in Unreal, an overdraw draw mode or a RenderDoc capture in Unity. Bright areas are pixels being shaded several times over.

**Fix.** Fewer and larger particles beat many small ones; a ten-particle effect with a good texture reads better than a hundred faint ones and costs a tenth. Shrink the on-screen size of alpha-blended quads, cap particle counts by distance, and cut full-screen transparent layers. Use alpha-tested or opaque materials where the art allows, since transparency cannot be depth-culled. On mobile, treat every full-screen transparent layer as an entire frame's worth of bandwidth, because that is roughly what it is.

## GPU: fill rate and resolution

**Shows up as** frame time that tracks resolution almost linearly and barely reacts to scene complexity — the first experiment in `cpu-or-gpu.md` moves it a lot.

**Confirm** by halving the render resolution and re-measuring. That is the whole test.

**Fix.** Render the 3D scene at a lower internal resolution and upscale, keeping the UI at native, which is the single highest-value setting on a handheld or phone. Cut the number of full-screen post-process passes; each one reads and writes the whole framebuffer. Check the render scale the game actually uses on the device rather than the one in the project settings, because a platform override is easy to lose track of.

Both a lower internal resolution and a lower frame target are legitimate answers. A locked 40 fps at native beats an unstable 60 at half resolution on most handhelds, and the choice belongs to whoever owns the game's look.

## GPU: shader complexity

**Shows up as** GPU cost concentrated in the base pass, out of proportion to the triangle count, and worse on mobile than on desktop by more than the hardware gap explains.

**Confirm** with the shader complexity view mode in Unreal, a GPU capture elsewhere, and by counting texture samples and branches in the material that covers the most screen area.

**Fix.** Simplify the materials that fill the most pixels, not the ones that are most complicated — a complex shader on a small prop costs nothing. Bake what is static into a texture. Cut dynamic branches in pixel shaders on mobile. Give distant objects a cheaper material variant the way they get a cheaper mesh.

## GPU: shadows and lights

**Shows up as** a large `shadow depths` or equivalent pass in the GPU breakdown, cost that scales with the number of lights rather than with what is on screen, and a sharp drop when shadows are switched off.

**Confirm** with `stat gpu` in Unreal or the Visual Profiler's pass breakdown in Godot, and by toggling shadow casting per light.

**Fix.** One shadow-casting directional light is the budget on mobile and handhelds; every additional shadow caster re-renders the scene from that light. Reduce cascade count and cascade distance before reducing shadow map resolution, since distant cascades cover the pixels nobody looks at. Bake static lighting where the scene allows it. Turn off shadow casting on small or flat objects individually — the shadow nobody sees costs the same as the one they do.

## GPU: texture bandwidth

**Shows up as** cost that appears on the device and not on the workstation, stalls that do not correlate with triangle or draw counts, and memory pressure or thermal throttling arriving early.

**Confirm** with a memory or bandwidth counter from the vendor tool, and by auditing the largest textures in the build against their on-screen size.

**Fix.** Use the platform's compressed format — ASTC on mobile, BC7 or BC5 on desktop — rather than shipping uncompressed. Keep mip maps on for anything seen at distance; a missing mip chain costs both bandwidth and shimmering. Size textures to their on-screen footprint rather than to their source resolution, and audit for the 4096-pixel texture on a crate nobody stands next to. Atlas small textures, which cuts both bandwidth and draw calls.

## Fixes that cost quality

Some of the entries above trade visual quality for milliseconds. Those are not engineering decisions taken quietly:

- Lower internal resolution, fewer particles, shorter shadow distance, fewer shadow casters, cheaper materials and a lower frame target all change how the game looks or feels.
- Present them as a choice with the numbers attached — "shadow distance 120 to 60 gives 4.1 ms at p99, and distant trees lose contact shadows" — and let whoever owns the look decide.
- Record what was traded in the report, because the next person to see the setting will otherwise raise it back.
