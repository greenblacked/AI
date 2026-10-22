# Engine and API mechanisms

## Contents

the generic recipe, Unreal, Unity, Vulkan, Metal, Steam, cache invalidation, a hitch log template

Names below are the ones the engines document at the time of writing. Check the engine version's own documentation for the exact console variable or API before relying on one; a renamed switch fails silently.

## The generic recipe

1. Record: run a development build with pipeline-creation logging on, play the route, save the list of pipelines created.
2. Merge: combine recordings from several people and several sessions. One recording misses rare enemies and edge-case weapons.
3. Ship: package the merged list with the build so it is read at load time.
4. Compile: on the player's machine, build every listed pipeline before it is needed, off the render thread where the API allows.
5. Verify: a cold-cache run shows no creation inside gameplay frames.

## Unreal Engine

- Recording: the PSO recording mode is enabled with the `-logPSO` command-line switch on a development or test build. The recorded files are then merged into the project's shipping bundled PSO cache by the cook step.
- Runtime: the shader pipeline cache is controlled by the `r.ShaderPipelineCache.Enabled` console variable; a bundled cache is precompiled in the background during load, and the engine API lets a game pause and resume that batch.
- Newer versions add PSO precaching, which requests pipelines when a component is registered rather than when first drawn (`r.PSOPrecaching`). Check the version notes: it reduces the recording burden but does not remove it for every material path, and it can be combined with the bundled cache.
- The cost to watch is draws that wait on a pipeline still being built. Decide whether the engine skips the draw for a frame or stalls; the setting differs by version.

## Unity

- Collect used variants into a `ShaderVariantCollection` asset (the editor can record the variants used in a play session) and call its `WarmUp` method during loading. `Shader.WarmupAllShaders` exists but compiles every variant in the build, which is the exploded set this skill tries to avoid.
- Strip first: the build's shader stripping, plus removing unused keywords and `shader_feature` versus `multi_compile` choices. A `multi_compile` line multiplies the variant count by its number of options; a `shader_feature` only keeps what materials in the build use.
- Newer versions provide a graphics state collection that records and warms full pipeline state; where available it is the closer match for DX12, Vulkan and Metal because a shader warm-up alone does not build the PSO.

## Vulkan

- Create a `VkPipelineCache`, populate it by creating the pipelines you will use, read it out with `vkGetPipelineCacheData`, store it, and pass it as initial data at the next launch.
- The cache header carries a vendor id, device id and a driver-specific UUID; the driver ignores data that does not match. Validate the header yourself and discard a mismatch rather than trusting the driver to.
- Pipeline creation can run on worker threads against a shared cache; use that to compile the manifest in parallel behind the loading screen.
- Fossilize is the record-and-replay tool for pipeline state used by Steam; a recorded database can be replayed to fill driver caches.

## Metal

- A `MTLBinaryArchive` stores compiled pipeline functions. Build it from the manifest and load it at launch. Archives are specific to the GPU family and OS version, so ship per-family archives where you target several, with the runtime falling back to normal compilation when none matches.

## DirectX 12

- Pipeline library objects (`ID3D12PipelineLibrary`) store and reload pipeline state. The driver also keeps its own cache, which is why the per-vendor wipe in the repro step matters.

## Steam

- Steam distributes pre-built shader caches for Vulkan titles (and for Windows titles run through its compatibility layer) so a player downloads the cache with the game. This shortens first-run compile on Steam Deck and similar hardware but only covers what the recorded set covered, so the manifest discipline still applies. Check the current Steamworks documentation for how caches are collected and which titles are eligible.

## Cache invalidation

Key every shipped cache by: game build, shader source hash, GPU vendor and device, driver version. A mismatch means rebuild, not fail. A half-written cache (player quit mid-compile) must be detected by a length or checksum field written last.

## Hitch log template

| Frame | Time ms | Thread | Pipeline or material created | Effect on screen | Gone on warm second pass |
| --- | --- | --- | --- | --- | --- |

A "yes" in the last column for every row is the confirmation in step 1: the hitch is absent once the pipeline is cached. A "no" row recurs on a warm pass, so it is not a first-use compile and belongs to `game-performance`.
