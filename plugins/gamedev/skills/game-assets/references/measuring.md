# Measuring build size, memory and load time

Read this before changing an import setting. The purpose is to replace "the build feels big" with a table that says which category, which asset and how many bytes, produced the same way each time so two builds can be compared.

## Contents

- [What to produce](#what-to-produce)
- [Unity](#unity)
- [Unreal Engine](#unreal-engine)
- [Godot 4](#godot-4)
- [Measuring from outside the engine](#measuring-from-outside-the-engine)
- [Measuring load time](#measuring-load-time)
- [Recording a result so it can be compared](#recording-a-result-so-it-can-be-compared)

## What to produce

Two artefacts, every time:

1. **A size report.** Bytes on disk in the shipped form, grouped by category — textures, audio, meshes, animation, scripts and code, everything else — with the twenty largest individual assets listed. Compressed and uncompressed figures are different questions; say which one the table holds.
2. **A memory breakdown.** Peak resident memory during actual play on the target device, split at least into graphics, audio and managed or engine allocations. Editor figures include editor overhead and are not the number; capture from a player build on real hardware wherever the platform allows it.

Both are worthless without the context that makes them reproducible: engine version, platform, build configuration, the scene or level measured, and the commit.

## Unity

**Build size, the free way.** Every player build writes a build report into the Editor log. Open it after the build and search for `Build Report`; it contains an uncompressed usage summary by category followed by every asset sorted by size, with each asset's share of the total.

```text
Windows  %LOCALAPPDATA%\Unity\Editor\Editor.log
macOS    ~/Library/Logs/Unity/Editor.log
Linux    ~/.config/unity3d/Editor.log
```

The categories are what to read first. If textures are 60% of the build, nothing else on the list matters yet.

**Build size, the readable way.** The same data is serialised to `Library/LastBuild.buildreport` after each build. Installing the Build Report Inspector package (`com.unity.build-report-inspector`) through the Package Manager adds a menu entry that opens that file in an inspector with sortable categories, the list of source assets per output file, and the build's step timings. It is the fastest way to answer "what got bigger since last week" when both reports have been kept.

**Memory.** Install the Memory Profiler package (`com.unity.memoryprofiler`) and open it from `Window > Analysis > Memory Profiler`. Attach to a development player build running on the target device, take a snapshot during representative play, and read the breakdown by object type — graphics memory and the texture list are the two views that matter here. Two snapshots can be compared directly, which is how a leak and a budget regression are told apart.

The built-in profiler at `Window > Analysis > Profiler` gives the same totals more cheaply. Build with `Development Build` and `Autoconnect Profiler` enabled, because profiling in the editor measures the editor.

**Addressables and asset bundles.** When content is delivered through Addressables, the per-bundle detail is in the build layout report. Enable the debug build layout in the Addressables preferences, build the content, and read `Library/com.unity.addressables/buildlayout.txt`, which lists every bundle, every asset inside it, and the duplication across bundles — that last one is where a shared texture ends up in four bundles and the download is four times what it should be.

## Unreal Engine

**Per-asset size and dependencies.** Right-click any asset or folder in the Content Browser and choose `Size Map`. It draws a treemap of the asset and everything it pulls in, with disk and memory sizes, which is the tool for answering why one level costs what it does. `Reference Viewer` on the same menu answers the complementary question of who is keeping an asset in the build at all.

**Project-wide.** `Tools > Audit > Asset Audit` lists assets with their disk size, memory estimate and type, filterable and sortable across the whole project. `Window > Statistics` gives the per-level texture and primitive statistics.

**Runtime memory.** From the console in a packaged development build:

```text
stat memory          Live totals by allocation category
stat streaming       Texture streaming pool usage and whether it is over budget
ListTextures         Every loaded texture with its current and maximum size
MemReport -Full      Writes a detailed report to Saved/Profiling/MemReports/
```

`stat streaming` reporting the pool over budget is the specific signal that the texture set does not fit and the streamer is thrashing, which shows up to players as textures that resolve late or never.

**Cooked size.** The cooked output lands in `Saved/Cooked/<Platform>/`. For a packaged build the content is inside pak files, and `UnrealPak <file.pak> -List` prints every entry with its size, which is the ground truth for what shipped.

## Godot 4

**Texture and video memory.** Run the project from the editor and open the `Debugger` panel. The `Video RAM` tab lists every resource currently on the GPU with its path, type, format and size, sorted by usage — it is the single most useful view in this list, because it names the format alongside the size, so a texture that fell back to uncompressed is visible rather than inferred. The `Monitors` tab graphs video, texture and buffer memory over time.

The same numbers are readable from code through `Performance.get_monitor()` with `Performance.RENDER_VIDEO_MEM_USED` and `Performance.RENDER_TEXTURE_MEM_USED`, which is how to log them from a real device rather than the editor.

**Build size.** Godot has no built-in size report. The useful substitute is to export the resource pack as a ZIP rather than a PCK from the export dialog and list it:

```bash
unzip -l game.zip | sort -k1 -n | tail -30
```

That gives every imported resource at its shipped size, in shipped form, which is exactly the table needed. For an automated version, export from the command line and size the output:

```bash
godot --headless --export-release "Linux/X11" build/game
du -sh build/
```

Remember that what ships is the contents of the import cache, not the source files: a 40 MB PNG that imports to a 2 MB compressed texture appears in this list at 2 MB, which is the point of measuring here rather than on the source tree.

## Measuring from outside the engine

Sometimes the engine will not tell you, or the question is about the artefact a store actually serves.

**Android.** An APK and an AAB are both ZIP archives:

```bash
unzip -l app.apk | sort -k1 -n | tail -40
```

For the figure Google Play enforces, which is the download size after its own compression and per-device splitting, use `bundletool build-apks` followed by `bundletool get-size total` against the resulting archive. The number in the Play Console is that one, not the size of the file uploaded.

**iOS.** An IPA is also a ZIP, but the figure that matters — per-device download and install size after thinning — comes from the App Store Connect app size report for an uploaded build.

**Desktop and web.** Size the tree and sort it:

```bash
du -h --max-depth=2 build/ | sort -h | tail -20
```

For a web build, size the compressed transfer as well as the files, since the server serves them compressed, and check what is needed before first interaction separately from the total: a 300 MB game that is playable after 20 MB is a different product from one that is not.

## Measuring load time

Log a timestamp at process start, at the first frame rendered, and at the point the player can act, and record all three per platform. The gap between the second and third is where asset loading lives.

Two things are worth separating, because the fixes are different. Time spent reading bytes from storage is fixed by making the assets smaller or by streaming them; time spent after the bytes are read — decompressing audio, uploading textures, building physics shapes, compiling shaders — is fixed by changing the format or by moving the work off the critical path. Shader compilation in particular is commonly mistaken for asset loading, and no amount of texture compression touches it.

## Recording a result so it can be compared

Write one line per build into a file in the repository, and generate it from the build job rather than by hand:

```json
{"date": "2026-09-11", "commit": "a1b2c3d", "platform": "android", "config": "release",
 "download_bytes": 148000000, "install_bytes": 310000000,
 "peak_memory_bytes": 620000000, "time_to_first_input_ms": 4100,
 "by_category": {"textures": 210000000, "audio": 58000000, "meshes": 22000000, "other": 20000000}}
```

Two builds and a diff turn an argument into a fact. A threshold on the same numbers in CI turns the fact into a gate, and a gate is the only thing that has ever kept a build size flat: it fails the pull request that added the 4K texture, while the person who added it is still looking at it.
