---
name: game-assets
description: "Get art and audio into a game build without the build eating the disk, the memory or the download: keep lossless source out of the engine's import path, put large binaries behind Git LFS before the history is too big to migrate, choose per-platform texture compression (BC7, ASTC, ETC2) rather than shipping RGBA32, set resolution, mipmap, polygon and LOD budgets against the target hardware, pick compressed, decompressed or streamed per sound, fix import scale and unit conventions, and apply import presets per folder so a new asset is correct by default. Use whenever someone says the build is 4GB, the APK is over the store limit, textures look terrible on Android, the game is killed by the OS for memory on a phone, a mesh imports at the wrong scale, loading takes forever, or asks whether to use LFS for this. Not for frame time, draw calls or stutter, which is game-performance, and not for building the game itself."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git:*), Bash(godot:*), Bash(ffprobe:*), Bash(ffmpeg:*), Bash(du:*), Bash(unzip:*)
---

# Game Assets

An asset pipeline where the source file and the shipped file are different things on purpose, every import decision is made once at the folder level rather than remembered per asset, and the size of the build is a number somebody watches every week rather than a surprise the month before launch.

Most pipeline pain traces back to one confusion: treating the 200 MB layered source texture and the 2 MB block-compressed thing the GPU samples as the same asset. Once they are the same asset, the repository carries gigabytes it never needed, the engine re-imports a file only an artist can open, and nobody can answer what the build actually costs. The rest of the pain is per-platform: a texture format that is free on a desktop GPU is decompressed to four bytes a pixel on a phone, and nothing warns you — the build succeeds, the screenshots look fine, and the game is killed by the OS on a mid-range Android device three seconds after the level loads.

## Scope

Use for: what an asset costs in build size, memory footprint and load time, and the import settings that decide it. Texture compression and resolution, audio load type and sample rate, mesh LODs and polygon budgets, import scale and unit conventions, atlasing, repository layout, Git LFS, and getting a size or memory report out of an engine.

Do not use for: frame time. A game that renders at 22 ms per frame with a 40 MB build has a rendering problem, not an asset problem, and `game-performance` owns frame budget, draw calls, overdraw, physics cost and GC pauses. The boundary is what the number is measured in: bytes and seconds-to-load here, milliseconds-per-frame there. They meet at texture memory, because a texture that does not fit is both a memory problem and a bandwidth problem — start here when the symptom is a crash, a download size or a load time, and there when it is a stutter.

Do not use for: designing or writing the game, choosing an engine, or making it fun — that is `game-builder`. Do not use for container image size, which is a different kind of image entirely.

## Workflow

### Step 1: Get the budget before touching an asset

An asset decision cannot be made without a target, and "smaller" is not a target. Establish four numbers and write them into the repository, because a budget nobody can quote is a budget nobody enforces:

- **Download size.** The store or platform ceiling, not a preference. Google Play caps the base app at 200 MB for an Android App Bundle with the rest delivered as asset packs; iOS caps the uncompressed app at 4 GB and applies a cellular download limit above which users are prompted; a web build competes with the player's patience, so treat a few tens of megabytes before first interaction as the real cap.
- **Runtime memory.** The worst device the game claims to support, not the development machine. A mid-range Android phone gives an application a few hundred megabytes to a gigabyte before the low-memory killer takes it; a console has a fixed, published figure; a browser tab on a 32-bit context is capped far lower than the machine's RAM.
- **Load time.** Seconds from launch to first input, and seconds per level transition. This is the number asset streaming exists to serve.
- **The lowest target GPU.** It decides which texture formats exist at all, which is the single most consequential entry in this list.

If the user cannot answer these, ask. Every later decision is a trade against them, and guessing here makes the whole audit unfalsifiable.

### Step 2: Measure before changing anything

Do not open an import setting until there is a current build size report and a memory breakdown. The intuition about which assets are large is wrong often enough that acting on it wastes the effort on the third-largest thing.

`references/measuring.md` has the exact path for each engine: the Unity build report and Memory Profiler snapshot, Unreal's Size Map and texture listing, Godot's Video RAM debugger tab, and how to size a shipped archive from the outside when the engine will not tell you. Read it at this step.

What comes out of it is one table, sorted by size, with textures, audio, meshes and everything else separated. Nearly always the shape is the same: textures are the majority of memory, audio is the majority of the download, and one or two assets are ten times larger than anything near them. Name those first.

### Step 3: Separate source from shipped

The rule is one sentence: lossless authoring files live outside the engine's import path, and the engine's importer produces the shipped form from an exported intermediate.

```text
repo/
  art-source/        # .psd, .blend, .kra, .aup3 — lossless, versioned, never imported
  game/              # the engine project
    assets/          # .png, .gltf, .ogg, .wav — exported intermediates the importer reads
```

Both directories are version controlled. The difference is that nothing under `art-source/` is ever read by the engine, so no import cost, no format surprise, and no chance of shipping it.

Three things follow, and each is worth stating to the user because each is routinely violated:

- **A source file inside the project costs on every import.** Unity and Godot both import `.blend` by launching Blender, so a `.blend` in the project makes a working Blender install with a matching version a hard dependency for every teammate and every CI runner, and makes a cold import take minutes.
- **A broad export filter ships them.** Godot exports by resource filter, and a filter widened to catch a data file can sweep source art into the PCK. Check what the export actually contains rather than what you intended it to contain.
- **Generated import caches are not source.** Unity's `Library/`, Unreal's `Intermediate/`, `Saved/`, `Binaries/` and `DerivedDataCache/`, Godot's `.godot/` — all regenerate from the real inputs, all are enormous, and all produce merge conflicts nobody can resolve. Ignore them.

The counterpart matters more and is the one people get backwards: the small text files beside an asset are not cache and must be committed. Unity's `.meta` files carry both the import settings and the GUID every reference in the project resolves through, so a missing one silently re-randomises the GUID and detaches every prefab that used the asset. Godot's `.import` files and, from 4.4, its `.uid` files do the same job. `references/version-control.md` has the per-engine list of what to commit and what to ignore.

### Step 4: Decide on Git LFS before the history is large

Git stores every version of every binary forever, and a binary does not delta-compress, so a 40 MB texture revised twenty times is 800 MB in every clone for the rest of the project's life. The decision is not whether the current checkout is large; it is whether the history will be.

Route it:

- **Under a gigabyte of binary, and it will stay that way.** Plain Git is fine. A small 2D game does not need LFS.
- **Anything larger, or any Unreal project.** Use LFS from the first commit. Unreal's `Content/` is binary `.uasset` throughout, so the question never really arises.
- **Tens of gigabytes, a team of artists, or files two people will edit on the same day.** LFS is at its limit. Perforce Helix Core and Unity Version Control exist for this and are what the industry uses; say so rather than pushing LFS past what it does well.

The failure mode to name out loud: LFS is easy to adopt on an empty repository and expensive afterwards. Converting existing history means `git lfs migrate import --include="*.psd" --everything`, which rewrites every commit, changes every SHA, invalidates every open branch and pull request, and requires every collaborator to re-clone. It works, but it is a scheduled event with a coordination cost, not a settings change. Check the exposure before deciding, with `git lfs migrate info --everything --top=20`, which reports the largest file types across the whole history whether or not LFS is in use.

Two further points, because both are discovered late. LFS bandwidth is metered on most hosts, including GitHub, and every CI clone spends it, so a pipeline that clones the full asset set on each run can exhaust a monthly quota in an afternoon — fetch with `GIT_LFS_SKIP_SMUDGE=1` for jobs that do not need the binaries. And LFS does not merge: a binary asset two people edited has no resolution but picking one, which is what `git lfs lock` is for on files a team edits concurrently.

`references/version-control.md` has the `.gitattributes` patterns, the per-engine ignore lists and the migration checklist.

### Step 5: Textures, which is where the memory is

Textures are the largest lever available, they are per-platform, and the failure is silent. The four decisions, in order of impact:

**Format.** A PNG in the project is not what ships. The importer transcodes it to a block-compressed format the GPU samples directly, and which format depends entirely on the target: BC1 through BC7 on desktop and current consoles, ASTC or ETC2 on mobile, and a transcodable container such as Basis Universal in KTX2 on the web, where the device's format is not known until runtime. Getting this wrong does not produce an error. It produces a texture the runtime stores uncompressed at four bytes per pixel — eight times the size of the BC1 it should have been — or, more commonly, a correct-but-wrong choice such as an RGBA format for an opaque texture, which doubles it. A 2048 by 2048 texture is 16 MiB uncompressed, 4 MiB at BC7 or ASTC 4x4, and 2 MiB at BC1, and a project has hundreds of them. Read `references/texture-compression.md` before setting any platform override; it has the format table per platform, the per-channel-type choices, and the specific settings that cause a silent fallback to uncompressed.

**Resolution.** Decide texel density once — pixels per world unit — and let each asset's resolution fall out of its physical size, rather than choosing a resolution per asset by eye. A stylised game lives comfortably at 256 to 512 pixels per metre; realism wants 1024. Then cap by platform: 2048 as the standard maximum on desktop with 4096 reserved for the few things a player puts their face against, 1024 on mobile with 2048 for the player character. A 4096 texture in a mobile build is a bug. Uncompressed with mipmaps it is 85 MiB on its own, and it is being sampled onto an object that occupies two hundred pixels of a phone screen. The engine-side lever that makes this enforceable rather than aspirational is the per-platform maximum size override, which downscales on import without touching the asset.

**Mipmaps.** On for anything rendered in 3D or at a varying distance. They cost 33% more memory and they save far more than that in sampling bandwidth, which is the scarce resource on mobile GPUs, and they are what stops distant detail shimmering. Off for UI, sprites and anything drawn at a fixed one-to-one size, where the extra third buys nothing and the lower mips are never sampled.

**Atlasing.** Packing many small textures into one reduces draw calls and texture state changes, which is most of what makes 2D and UI rendering slow. It is not free: an atlas is resident as a unit, so one small icon keeps the whole page in memory, and atlased tiles bleed into each other at lower mip levels unless each is padded. Atlas UI and sprite sheets; do not atlas large 3D material textures, which are better served by streaming.

Two smaller rules that prevent surprises. Keep textures to powers of two, or at minimum to multiples of the compression block size, because a non-conforming size makes some importers pad the texture and others fall back to uncompressed. And do not carry an alpha channel that is fully opaque: it is invisible in the editor and it forces the more expensive format for the entire texture.

### Step 6: Audio, where the download is

Three settings decide everything, and they are the same three in every engine under different names: the codec, whether the decoded audio is held in memory, and whether it streams from storage.

The decision rule is short. A sound that is under a few seconds and plays often — footsteps, gunfire, UI clicks — is decompressed at load and held as raw samples, because decoding it on each play costs CPU at exactly the moment the game is busy, and the memory is small. Music, ambience, dialogue and anything over roughly ten seconds is streamed from storage and decoded as it plays, because holding it decompressed is enormous: a single minute of stereo 44.1 kHz 16-bit audio is 10.6 MB in memory, so a soundtrack held uncompressed is measured in hundreds of megabytes. The middle case — a medium-length sound played rarely — is held compressed in memory and decoded on demand.

Sample rate and channel count are the budget levers nobody pulls. Music earns 44.1 kHz; most sound effects are indistinguishable at 22.05 kHz, which halves them. Anything positioned in 3D should be mono, because the engine spatialises a single channel and a stereo source is both downmixed and twice the size. A sound imported stereo at 48 kHz because that is what the recording was is the most common avoidable waste in a build.

`references/audio-and-meshes.md` has the setting names per engine for each of these, and the reason a sound designer's delivery format is not the import format.

### Step 7: Meshes, scale and LODs

**Import scale is the one that bites three weeks later.** Every tool has a different idea of what one unit means: Unity and Godot work in metres, Unreal in centimetres, Blender exports metres, and several DCC tools default to centimetres or inches. An import scale that is off by a hundred does not look wrong, because everything is scaled to match by hand and the scene renders fine. It surfaces later as physics: gravity is defined in units per second squared, so a character authored a hundred times too large falls as if on the moon, collision margins and contact offsets are suddenly microscopic relative to the geometry, raycasts skip through thin walls, and the bug is diagnosed as "the physics feels floaty" rather than as an import setting. Check scale on the first mesh imported, by putting a one-unit reference cube next to it, and fix it in the exporter rather than with a scale on the transform — a non-unit transform scale also makes colliders non-uniform and character controllers unreliable.

**Polygon budgets only mean something against hardware.** Triangle counts in isolation are a number with no units. On mobile, a few hundred thousand triangles on screen is a workable ceiling and draw calls bind before triangles do, so a character in the 5,000 to 15,000 range and aggressive merging matters more than shaving the mesh. On desktop and current consoles the same character is comfortable at 30,000 to 80,000, and geometry stops being the constraint before it starts. Where a virtualised geometry system is in use, the budget moves off the mesh entirely and onto the material and instance count instead.

**LODs are how a budget survives contact with a real scene.** Generate them at import — every major engine can, using a mesh simplifier — rather than authoring them by hand, and then check the transition distances rather than accepting the defaults, because a visible pop is a tuning problem and an LOD chain that never transitions is a feature that is off. The reference has the per-engine naming convention that makes automatic LOD group creation work on import.

### Step 8: Make the next asset correct without anyone remembering

Every decision above is worthless if it has to be reapplied by hand. The pipeline is only real when a new file dropped into the right folder comes out correct.

- **Name and place by role, not by asset.** Normal maps, colour maps, masks, UI sprites and streamed music each want different import settings, so each gets a folder or a filename suffix that an importer can key on. This is why `_N`, `_BC`, `_M` suffix conventions exist; pick one and write it down.
- **Apply presets at the folder level.** Unity has the Preset Manager with name filters and, for anything conditional, an `AssetPostprocessor` that keys on the asset path; Godot's Import dock can set a preset as the default for a resource type; Unreal supports bulk editing a selection through the property matrix. The reference names the exact mechanism for each.
- **Gate size in CI.** A build size and a peak memory figure recorded per build, with a threshold that fails the job, is what turns size into a thing that gets noticed in the pull request that caused it rather than in the month before launch.

### Step 9: Report in numbers

```markdown
## Budget
[Download, memory, load time and lowest target GPU, as agreed in step 1.]

## Where it is now
[The measured table: size by category, the largest offenders, the method used.]

## Changes made
[Each change with its before and after in bytes or milliseconds, not adjectives.]

## Made permanent
[The presets, conventions and CI gate that keep the next asset correct.]

## Remaining and deferred
[What is still over budget, what it would cost to fix, and what was judged not worth it.]
```

## Anti-patterns

**Shipping the source.** A layered PSD or a `.blend` inside the project is imported on every cold start, makes the authoring tool a build dependency, bloats every clone, and can reach the shipped archive through a careless export filter. Export an intermediate; keep the source in a sibling directory.

**Committing the import cache.** Unity's `Library/`, Unreal's `Intermediate/` and `DerivedDataCache/`, Godot's `.godot/` are derived data. Committing them produces unresolvable conflicts and a repository an order of magnitude larger than the project.

**Ignoring the import metadata.** The mirror-image mistake, and worse, because it is silent: a `.gitignore` broad enough to catch Unity's `.meta` files or Godot's `.import` files detaches references and resets every import setting on the next checkout.

**One texture format for every platform.** The desktop build looks correct, the mobile build silently stores the same textures uncompressed, and the game is killed by the OS on devices nobody on the team owns.

**Choosing resolution by eye.** Per-asset judgement produces a project where a background prop and a hero character are both 2048, in either direction. Texel density is a decision made once.

**Full-rate stereo everything.** A 48 kHz stereo import of a mono footstep is four times the bytes for audio nobody can distinguish, repeated across every sound in the game.

**A non-unit scale on the transform.** The fix that appears to work and moves the bug into physics, where it costs a week to trace back.

**Adding LFS after the history is large.** The migration rewrites every commit and every collaborator re-clones. Decide it in the first week, when it costs one line in `.gitattributes`.

**Treating build size as an end-of-project task.** Size is accumulated one asset at a time by people who cannot see the total, and at the end the only levers left are blunt ones — global downscaling, cutting content, shipping a second download. Budget at the start and measure weekly.

**Optimising without measuring.** The largest asset is rarely the one anyone guesses, and an afternoon spent on the third-largest thing shows up as a rounding error in the report.

## References

- `references/texture-compression.md` — read at step 5, before setting any per-platform override: the format table for desktop, mobile, console families and the web, what each costs per pixel, which channel layouts want which format, and the settings that silently fall back to uncompressed.
- `references/measuring.md` — read at step 2: how to produce a build size report and a memory breakdown in Unity, Unreal and Godot, how to size a shipped archive from the outside, and what to record so two builds can be compared.
- `references/audio-and-meshes.md` — read at steps 6 and 7: the audio load-type and codec settings per engine, sample rate and channel guidance, unit conventions and import scale per tool, and LOD generation and naming.
- `references/version-control.md` — read at steps 3 and 4: what to commit and ignore per engine, the `.gitattributes` patterns for LFS, the migration checklist, and when to leave Git for Perforce or Unity Version Control.
