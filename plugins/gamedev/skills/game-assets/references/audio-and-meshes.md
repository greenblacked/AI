# Audio and mesh import

Read this at the audio and mesh steps. The audio half is mostly three settings applied with one decision rule; the mesh half is mostly unit conventions, which are boring until they surface as a physics bug nobody connects to an import setting.

## Contents

- [Audio: the decision rule](#audio-the-decision-rule)
- [Audio: sample rate and channels](#audio-sample-rate-and-channels)
- [Audio: the settings per engine](#audio-the-settings-per-engine)
- [Audio: delivery format is not import format](#audio-delivery-format-is-not-import-format)
- [Meshes: units and import scale](#meshes-units-and-import-scale)
- [Meshes: polygon budgets that mean something](#meshes-polygon-budgets-that-mean-something)
- [Meshes: LODs](#meshes-lods)
- [Meshes: the settings that quietly double memory](#meshes-the-settings-that-quietly-double-memory)

## Audio: the decision rule

Three properties are chosen per sound, and every engine has all three under different names: the codec it is stored in, whether the decoded samples are held in memory, and whether it is read from storage while it plays.

| Length and use | Store as | Held as | Why |
| --- | --- | --- | --- |
| Under ~2 s, plays constantly (footsteps, hits, UI) | Uncompressed or ADPCM | Decompressed in memory | Decoding costs CPU at the exact moment the game is busiest, and the memory is trivial |
| 2–10 s, plays occasionally (voice lines, one-shots) | Compressed | Compressed in memory, decoded on play | Middle ground; the decode is affordable because it is rare |
| Over ~10 s (music, ambience, long dialogue) | Compressed | Streamed from storage | Holding it decompressed is enormous and holding it compressed still costs the whole file |

The arithmetic behind it: one minute of stereo 16-bit audio at 44.1 kHz is 10.6 MB decompressed. A twenty-minute soundtrack held in memory is over 200 MB, which on most targets is the entire audio budget several times over, for something that is read strictly in order and is the ideal candidate for streaming.

The rule inverts for the smallest sounds. A 0.2 s footstep is 35 KB decompressed, and there may be twelve of them. Compressing those saves nothing worth having and adds a decode to a sound that plays several times a second.

One caveat on streaming: each stream is a file handle, a decoder and a buffer. Two or three concurrent streams are normal, twenty are not — a game with many long looping ambiences needs a mixing strategy, not twenty streams.

## Audio: sample rate and channels

These are the levers that cost nothing and are almost never pulled.

- **Sample rate.** 44.1 or 48 kHz is worth it for music. Most sound effects are indistinguishable at 22.05 kHz, which halves them, and low-frequency content — impacts, rumbles, engine loops — survives lower still. Decide per folder rather than per file.
- **Channels.** Anything positioned in 3D should be mono. The spatialiser takes a single channel and computes the stereo image from the listener's position, so a stereo source is downmixed anyway and cost twice the bytes to get there. Stereo is for music, stereo ambience beds and UI.
- **Bit depth.** 24-bit is an authoring format. Ship 16-bit; the difference is inaudible after mixing and it is a third of the size.
- **Trailing silence.** Editors leave it and it is stored at full rate. Trimming a library of one-shots routinely removes a double-digit percentage.

## Audio: the settings per engine

- **Unity.** The AudioClip importer: `Load Type` is the memory decision (`Decompress On Load`, `Compressed In Memory`, `Streaming`), `Compression Format` is the codec (`PCM`, `ADPCM`, `Vorbis`, plus platform-specific formats), `Quality` tunes Vorbis, `Force To Mono` and `Sample Rate Setting` (`Preserve Sample Rate`, `Optimize Sample Rate`, `Override Sample Rate`) are the budget levers. `Preload Audio Data` decides whether the clip loads with the scene or on first play. The importer shows the resulting size for the current settings, so the effect of a change is visible immediately.
- **Unreal.** The Sound Wave asset: `Loading Behavior` covers the memory decision (`Force Inline` keeps it resident, `Retain On Load` keeps the first chunk, `Load On Demand` streams), the `Streaming` flag enables audio streaming for the asset, and `Compression Quality` tunes the codec. Which codec is used is a platform decision, set in the per-platform audio section of the project settings, where the sample rate for each quality tier and the maximum channel count also live. Bink Audio is available across platforms in UE5 and is usually the better default where it applies.
- **Godot 4.** WAV files are imported as `AudioStreamWAV` with `Compress > Mode` offering PCM, IMA-ADPCM and Quite OK Audio, plus `Force > Mono`, `Force > 8 Bit` and `Force > Max Rate` in the Import dock. Ogg Vorbis and MP3 files are held in memory in their compressed form and decoded during playback, so they are the right choice for anything long; there is no separate disk-streaming toggle to set.

## Audio: delivery format is not import format

A sound designer delivers 48 kHz 24-bit stereo WAV because that is the correct authoring format, and importing it unchanged is how a build ends up with a hundred megabytes of footsteps. The delivered files belong with the other lossless source, outside the engine's import path; what enters the project is the trimmed, mono-where-appropriate, rate-reduced version. This is the audio half of the source-versus-shipped distinction and it is skipped more often than the texture half, because audio is invisible in a size report until somebody sorts by category.

## Meshes: units and import scale

Every tool disagrees, and none of them warn:

| Tool | Unit | Up axis | Handedness |
| --- | --- | --- | --- |
| Unity | 1 unit = 1 metre | Y | Left, +Z forward |
| Unreal | 1 unit = 1 centimetre | Z | Left, +X forward |
| Godot | 1 unit = 1 metre | Y | Right, -Z forward |
| Blender | metres | Z | Right, -Y forward |
| Maya | centimetres by default | Y | Right |
| 3ds Max | generic or inches by default | Z | Right |

glTF is the least ambiguous interchange format because the specification fixes the answer: metres, Y up, right-handed. FBX carries a unit scale in the file, which is why the same FBX imports at different sizes into different engines and why importers expose both a scale factor and a convert-units option.

**Why a wrong scale is a physics bug.** A model imported a hundred times too large looks correct as soon as someone scales the scene to match, and everything renders fine. Physics does not scale with it. Gravity is expressed in units per second squared, so a character a hundred times too large falls a hundred times too slowly relative to its own size, which reads as floaty rather than as wrong. Collision margins, contact offsets, sleep thresholds and solver tolerances are absolute values tuned for human-scale geometry, so at the wrong scale thin walls are penetrated by fast objects, stacked bodies jitter, and character controllers fail to step over geometry they clearly should. The symptom arrives weeks after the import, in a different system, described by whoever found it as a physics problem.

The check takes a minute and is worth doing on the first mesh from every new source: put a primitive of known size next to the import and confirm a two-metre character is two units tall in Unity or Godot and two hundred in Unreal. Fix it in the exporter or the importer's scale factor, not with a scale on the object's transform — a non-unit transform scale propagates to colliders, makes non-uniform scaling possible by accident, and is a documented source of trouble for character controllers and physics queries in every engine.

## Meshes: polygon budgets that mean something

A triangle count without hardware attached is not a budget. Useful anchors:

- **Mobile.** Draw calls and fill rate bind long before triangles. A few hundred thousand triangles on screen is workable; a player character sits at 5,000 to 15,000, and the effort is better spent merging meshes and sharing materials than on decimating any single one.
- **Desktop and current consoles.** The same character is comfortable at 30,000 to 80,000, and geometry is rarely the constraint. Material complexity, shadow-casting draw calls and overdraw are.
- **Virtualised geometry.** Where a system like Nanite is in use for static geometry, the source triangle count stops being the budget and instance count, material count and the memory of the geometry data take its place. It does not cover everything — skinned meshes, transparency and some material types fall back to the traditional path — so the budget above still applies to whatever is outside it.

Collision is a separate budget from rendering and is the one that gets forgotten. A render mesh used directly as a concave collider costs memory, cooking time and query time far out of proportion to its value. Author collision as primitives or a low-polygon convex hull, and treat "collision uses the render mesh" as a finding.

## Meshes: LODs

Generate LODs at import rather than authoring them, and then check the transitions rather than accepting defaults. Unity creates an LOD Group automatically when the meshes in a file are named `<name>_LOD0`, `<name>_LOD1` and so on, so the convention is worth enforcing at the export step. Unreal generates and configures LODs in the Static Mesh editor, with LOD groups providing project-wide policy. Godot 4 generates mesh LODs automatically on import, with the switch threshold controlled globally by the mesh LOD project setting.

Two failure modes: a chain whose transitions are so far out that it never switches, which costs import time and buys nothing; and a first transition so close that the pop is visible, which players notice more than the lower detail itself. Both are found by flying the camera away from an object and watching, which takes less time than reasoning about it.

## Meshes: the settings that quietly double memory

- **Read/Write enabled.** Keeping a mesh readable from the CPU keeps a second full copy in system memory. It is needed for runtime mesh manipulation and for nothing else, and it is commonly left on across a whole project after being switched on for one asset.
- **Unused vertex attributes.** A mesh carrying a second UV channel, vertex colours or tangents it does not use pays for them per vertex. Importers can strip them; the default often does not.
- **Full-precision everything.** Where the engine offers compressed vertex positions, normals or UVs, the quality loss is invisible on most content and the saving is proportional.
- **Blend shapes and unused animation curves.** An animation that imports every bone in the rig, including the ones the mesh does not use, is several times larger than the one that does not. Animation compression settings and curve stripping are per-clip and are usually left at whatever the first import chose.
