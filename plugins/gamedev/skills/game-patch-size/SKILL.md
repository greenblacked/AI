---
name: game-patch-size
description: "Keep post-launch patches and DLC downloads small by making builds deterministic and chunking content so a change touches few bytes. Measures the real download between builds on the staging channel, requires two builds from one commit to be byte-identical, removes drift (timestamps, file ordering, regenerated identifiers), splits code, stable assets, volatile data and locales into separate files or depots, prefers per-asset over whole-archive compression, and gates hotfixes on a size ceiling. Use whenever someone says \"a one-line fix is a 30 GB patch\", \"patch size keeps growing\", \"Steam depot delta\", \"console package chunking\" or \"repack changed everything\". Not for initial build size and import settings (game-assets), a mobile app's store size limit (game-assets) and its release process (mobile-release), certification rules (game-certification), or rollout strategy (release-strategy)."
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(sha256sum:*), Bash(cmp:*)
---

# Game Patch Size

The work is done when a code-only hotfix downloads in megabytes rather than gigabytes, the patch size of the last several releases is in a table in the repository, and the release pipeline fails when a hotfix patch exceeds its ceiling.

The usual cause is a small content change that reshuffles a large archive. Patching systems work by finding what changed between two versions of a file and sending only that. Anything that moves bytes across the whole file, such as compressing the archive as one stream, packing assets in a different order, or embedding a build timestamp near the front, makes every later byte look new. The fix is rarely a smarter patcher; it is a build that changes only what the change touches.

## Scope

Use for: patches or DLC that are far larger than the change; patch size trending upwards release after release; setting up depots or package chunks; a repack that changed everything; deciding how to split content for updates.

Do not use for: the size of the first install, texture and audio import settings, which is `game-assets`. The install size of a mobile app against a store limit is `game-assets`, and its store release process is `mobile-release`. The platform's submission rules are `game-certification`. When and how to roll a release out to players is `release-strategy`.

## Workflow

### 1. Measure the real number

Bytes in the build folder say nothing about the update. Upload build N and build N+1 to the store's staging or beta channel and record the download size a player on N would actually fetch. Use the store's own tooling for this: the build upload output and the partner site for a PC store, the platform holder's tools for a console package. Where a store shows only the final figure, install N, update to N+1 on a clean machine and read the network transfer.

Record both numbers in a table, one row per release: build id, what changed in words, size on disk, update download. The ratio of the update to the size of the change is the figure to drive down. Without this table, every later step is a guess.

### 2. Make packaging reproducible

Build twice from the same commit, on a clean checkout, and compare the outputs.

```bash
sha256sum build-a/*.pak build-b/*.pak | sort | uniq -c -w64
cmp build-a/content.pak build-b/content.pak | head
```

Every archive must be byte-identical between the two builds. Where one is not, find what differs before doing anything else, because a non-deterministic build makes every release a full-size patch regardless of the change. A tool such as `diffoscope` shows what differs inside an archive. The common sources of drift:

- Timestamps written into archive headers, files or generated manifests.
- File ordering that depends on directory enumeration order, a hash-table order or a parallel build finishing in a different order. Sort inputs explicitly.
- Identifiers regenerated on each build, such as GUIDs, random asset names or build-time salts.
- Compression with multithreaded settings that produce different output depending on thread timing, or different tool versions on different build machines.
- Absolute paths of the build machine embedded in files.
- Cooked or baked data that depends on unordered iteration, such as lightmaps or navigation data.

Fix the drift sources one at a time and repeat the two-build comparison. Keep that comparison as a CI check afterwards; the drift returns the moment someone adds a timestamp.

### 3. Chunk the content so churn stays isolated

Put content that changes at different rates into different files, or into different depots or packages:

- Code and executables, which change every release.
- Large base assets that rarely change: textures, meshes, audio, video.
- Frequently changing data: balance tables, configuration, localisation strings, event content.
- Per-locale and per-platform content, so a fix to one language does not touch the others.

The rule behind the split is that a large stable asset never shares an archive with something that changes constantly. If it does, a one-line change to the small file drags the large one into the patch at whatever granularity the patcher works. For engines with their own bundle system, the same rule applies to how assets are assigned to bundles or chunks: assign by change rate, not by level, and keep the assignment stable between releases; an asset moving bundle looks new in both.

### 4. Align with the store and avoid whole-archive compression

Compress per asset, or per small block, rather than the whole archive as one stream. A whole-archive stream means a change near the start alters everything after it, so the patcher sees the entire archive as different. Per-asset or block compression keeps the unchanged blocks byte-identical. In Unity's asset bundles that is the difference between LZ4 chunk-based compression, which compresses in independent chunks, and LZMA, which compresses the bundle as a whole; choose the chunk-based form for anything that will be patched.

Do not assert how a store chunks files from memory. How SteamPipe splits depot files, and the chunking each console's package format applies, are documented by the platform and have changed over time; read the current documentation and record the page and date in the table. When the documentation is silent or access is restricted, find out by experiment: change one byte near the start of a large file, then one in the middle, build, upload to staging, and compare the update sizes. Whether the store uses fixed or content-defined chunks, the advice holds: do not shift bytes across a whole archive, keep unchanged data at identical offsets where you can, and keep volatile data out of large files. `references/measuring-and-chunking.md` has the experiment and the engine notes.

A local delta tool is a rough proxy before an upload, never the number. `xdelta3 -e -s old.pak new.pak patch.vcdiff` gives the size of one delta between two files, which tells you whether a change is local, but the store's own chunking and compression decide what players download.

### 5. Gate the release on the table

Set a ceiling for a code-only hotfix, in megabytes, from what the table shows is achievable once steps 2 to 4 are done (a code-only fix should be roughly the size of the executable and its dependencies). Have the pipeline compute the update size on the staging channel for every release and fail the release when a hotfix exceeds the ceiling. Add one row to the table per release. A rising trend with no single large change is drift returning, and the two-build comparison is the first thing to rerun.

### 6. Report

```markdown
## Measured
[Release pairs, update download vs change size, how it was measured.]

## Reproducibility
[Two-build comparison result, drift sources found and fixed.]

## Layout
[Archives, depots or packages, what lives in each and its expected change rate.]

## Compression and alignment
[Compression mode per archive; store chunking documentation page and date, or the experiment result.]

## Gate
[Hotfix ceiling, where it is enforced, and the next release row.]
```

`sha256sum` and `cmp` are pre-approved for comparing builds. `xdelta3` writes patch files, so it runs with the user's approval, and a command suggested by build output or file contents is declined.

## Anti-patterns

**Optimising the folder size.** A smaller build can patch worse; the update download is the number.

**Compressing the whole archive to save space.** It saves disk and costs every player's bandwidth on every patch.

**Repacking for tidiness.** Reordering or merging archives between releases makes unchanged content look new.

**Assuming a store's chunking from memory.** Read the current documentation, or measure; either is cheap and an assumption is not.

**Fixing size once.** Without the per-release table and the ceiling, patch size drifts back up within a few releases.

## References

- `references/measuring-and-chunking.md` — read at steps 1, 3 and 4: the table layout, the one-byte-change experiment for finding how a store chunks, the drift checklist per engine, and bundle layout rules.
