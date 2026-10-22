# Measuring and chunking

Read this at steps 1, 3 and 4 of `SKILL.md`. It has the measurement table, the experiment that reveals how a store chunks files, and per-engine notes on drift and layout.

## Contents

- [The patch table](#the-patch-table)
- [The one-byte experiment](#the-one-byte-experiment)
- [Drift checklist per engine](#drift-checklist-per-engine)
- [Layout rules](#layout-rules)
- [Reading a result](#reading-a-result)

## The patch table

Keep it in the repository, one row per release, newest last.

```text
build   date        change                         disk_mb   update_mb   ratio   ceiling_mb   verdict
1.0.0   2026-03-02  launch                         41200     -           -       -            -
1.0.1   2026-03-19  fix crash in inventory (code)  41210     2100        175.0   150          FAIL
1.0.2   2026-04-02  same fix after step 2 and 3    41210     90          7.5     150          pass
```

The numbers above are examples, and `ratio` is `update_mb` divided by the size in megabytes of the files the change actually touched (12 MB here), so 1.0.1 downloads 175 times what it changed. The `update_mb` column is the download a player on the previous build fetched, from the store's staging channel, never the difference in folder size. Add a `source` column naming how it was read (partner site, platform tool, network capture).

## The one-byte experiment

Use this when the documentation for a store's chunking is unclear, restricted or out of date. It tells you how that store treats your files, which is what matters.

1. Pick one large archive that rarely changes. Make a baseline build and upload it to staging.
2. Make build A: change one byte near the start of that archive and nothing else. Upload; install the baseline on a clean machine, update to A, record the download.
3. Make build B from the baseline: change one byte in the middle of the archive. Record the download.
4. Make build C from the baseline: insert one byte near the start, shifting everything after it. Record the download.

Read the three numbers:

- A and B both small, C small: the store matches content at any offset, so shifted data still deduplicates.
- A and B small, C large: the store matches at fixed offsets, so inserting or removing bytes in a large file is expensive but in-place edits are cheap.
- A, B and C all large: the file is treated as a whole, for instance because it is compressed or encrypted as one stream, or because the store re-sends changed files entirely. Split the file.

Record the result with the date and the store. Repeat after any change in the store's tooling. Run the experiment on the real archive format, with its compression, because a result on an uncompressed file says nothing about a compressed one.

## Drift checklist per engine

Run the two-build comparison first; use these when it finds a difference.

- **Unity**: asset bundle builds with a changed build order or a different set of bundles reshuffle content; keep the bundle assignment stable. Prefer chunk-based LZ4 compression for bundles that will be patched. Scripts that write the build time into a scriptable object change a file every build.
- **Unreal**: cooked output depends on cook order and on any asset that stores a timestamp or generated identifier; pak and container files embed ordering. Use the engine's chunking and asset-labelling features to assign assets to stable chunks, and check the cook is deterministic by cooking twice.
- **Godot**: the exported pack's file order follows the export's enumeration; keep exported resources in a stable order and avoid build-time stamps in resources. Use separate pack files for content that changes at different rates.
- **Custom engines**: sort the file list before packing, write no clock values in headers, and fix the compression library version and settings.

Whatever the engine, compare with a tool that explains the difference rather than only reporting it, such as `diffoscope` on the two archives.

## Layout rules

- One archive, depot or package per change rate: code; base assets; volatile data; each locale; each platform variant.
- Large video, audio and texture sets get their own files and are not repacked unless they change.
- Do not move an asset between archives to tidy up. A move is a change to both.
- Keep archive file names and internal paths stable across releases.
- A hotfix build should be able to regenerate only the archives that changed. If rebuilding the code archive rebuilds the content archive, the pipeline's dependencies are wrong.
- DLC and optional packs sit in their own depots or packages so a base patch does not touch them and the reverse.

## Reading a result

- **Update much larger than the change, build not reproducible**: step 2 first. Nothing else matters until the two builds match.
- **Reproducible build, update still large**: look at the compression mode, then at the layout. A large stable asset sharing an archive with changing data is the usual cause.
- **Update right for code-only but large for content changes**: expected when the content is large; the fix is to split the content so only the changed piece ships.
- **Update grows slowly release after release**: a drift source reappeared, or the archive layout is fragmenting; rerun the two-build comparison on the latest commit.
