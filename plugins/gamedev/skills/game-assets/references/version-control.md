# Version control for binary game assets

Read this when deciding what goes in the repository, whether Git LFS is needed, or how to fix a repository that already has gigabytes of binary history.

## Contents

- [What to commit and what to ignore](#what-to-commit-and-what-to-ignore)
- [Settings that make an engine project mergeable](#settings-that-make-an-engine-project-mergeable)
- [Git LFS: what it does and what it does not](#git-lfs-what-it-does-and-what-it-does-not)
- [.gitattributes patterns](#gitattributes-patterns)
- [Migrating existing history](#migrating-existing-history)
- [LFS in CI](#lfs-in-ci)
- [When to leave Git](#when-to-leave-git)
- [Secrets that hide in project files](#secrets-that-hide-in-project-files)

## What to commit and what to ignore

The principle: commit the inputs and the metadata that describes how to process them; ignore anything the engine can regenerate. The mistake in both directions is common, and the two failures look nothing alike — an over-broad ignore is silent and destructive, an over-narrow one is merely enormous.

**Unity.** Ignore `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/`, `MemoryCaptures/`, the build output directory, and the generated IDE project files. Commit `Assets/`, `Packages/` and `ProjectSettings/`. The critical one: every `.meta` file is committed. A `.meta` holds the import settings and the GUID that every reference in every scene and prefab resolves through, so an ignore rule that catches them detaches references across the project and regenerates GUIDs differently on each machine. This is the single most damaging `.gitignore` mistake available in Unity, and it presents as prefabs losing their materials rather than as a version control problem.

**Unreal.** Ignore `Binaries/`, `Build/`, `DerivedDataCache/`, `Intermediate/` and `Saved/`. Commit `Content/`, `Config/`, `Source/`, the `.uproject`, and the source of any in-tree plugin. `Content/` is binary `.uasset` and `.umap` throughout, which is why an Unreal project needs LFS or Perforce from the start rather than as a later decision.

**Godot 4.** Ignore `.godot/`, which is the import cache and the editor's per-project state, and `android/build/` if one-click Android deploy has been set up. Commit `project.godot`, every scene and resource (they are text and they diff), and every `.import` file — those carry the import settings and the resource's identity exactly as Unity's `.meta` files do. From Godot 4.4 the `.uid` files beside scripts and resources are committed for the same reason.

## Settings that make an engine project mergeable

Worth setting once, at the start, because each removes a class of conflict rather than helping resolve one:

- **Unity: serialise as text.** Set the editor's asset serialisation mode to force text, so scenes and prefabs are YAML and can be diffed and merged. Set version control mode to visible meta files. Then configure Unity's YAML merge tool as the merge driver for scene and prefab extensions in `.gitattributes`, because a three-way merge of a scene is otherwise impossible.
- **Unreal: one file per actor.** In a World Partition project, enabling one file per actor moves each actor out of the single monolithic map file, which is what lets two people edit the same level without one of them losing work.
- **Both: lock what cannot merge.** A binary asset edited by two people has no merge, only a choice. LFS file locking or a team convention exists to prevent the situation rather than to resolve it.

## Git LFS: what it does and what it does not

LFS replaces a tracked file in the Git object database with a small text pointer and stores the real bytes on a separate server, fetched on checkout. The effect that matters is that cloning no longer downloads every historical version of every binary, only the versions actually checked out.

What it does not do:

- **It does not make binaries mergeable.** A conflict on an LFS-tracked file is still a choice between two versions.
- **It does not shrink history that already exists.** Tracking a pattern applies to future commits only. Everything already committed stays in the Git objects until history is rewritten.
- **It is not free.** Most hosts meter LFS storage and, more painfully, bandwidth. The free tiers are on the order of a gigabyte of each, and every clone spends bandwidth.
- **It is not for small text files.** Putting `.meta`, `.import`, `.tscn` or source files into LFS costs a pointer indirection, breaks diffs, and saves nothing. Track the large binaries and only those.

Route the decision by expected history rather than current checkout size: plain Git under about a gigabyte of binary, LFS above it or for any Unreal project, and something other than Git past a few tens of gigabytes or a team of several full-time artists.

## .gitattributes patterns

Commit `.gitattributes` before adding the files it covers, or the files land in ordinary Git and have to be migrated later. Start with line-ending normalisation, then track the binary types the project actually has, marking each `-text` so no host tries to translate line endings inside it.

```gitattributes
* text=auto

# Source art and audio, if any of it lives in this repository
*.psd  filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text
*.wav  filter=lfs diff=lfs merge=lfs -text

# Shipped intermediates
*.png  filter=lfs diff=lfs merge=lfs -text
*.tga  filter=lfs diff=lfs merge=lfs -text
*.ogg  filter=lfs diff=lfs merge=lfs -text
*.fbx  filter=lfs diff=lfs merge=lfs -text
*.glb  filter=lfs diff=lfs merge=lfs -text

# Unreal content, which cannot merge and should be locked
*.uasset filter=lfs diff=lfs merge=lfs -text lockable
*.umap   filter=lfs diff=lfs merge=lfs -text lockable
```

Verify what is actually tracked rather than what was intended:

```bash
git lfs ls-files --size | sort -k2 -h | tail -20
git count-objects -vH
```

## Migrating existing history

This is a scheduled event with a coordination cost, not a settings change. Every commit SHA changes, every open branch and pull request is invalidated, and every collaborator re-clones rather than pulls.

1. Measure first: `git lfs migrate info --everything --top=20` reports the largest file types across the whole history, whether or not LFS is in use. It tells you whether the migration is worth the disruption and which patterns to include.
2. Pick a window. Everyone pushes their work, open pull requests are merged or closed, and the repository is frozen.
3. Take a backup clone with `--mirror`. This is the step that makes the rest reversible.
4. `git lfs install`, commit the `.gitattributes`, then `git lfs migrate import --include="*.psd,*.png,*.fbx" --everything`. The `--everything` matters: without it only the current branch is rewritten and the objects survive on the others.
5. Verify: `git count-objects -vH` for the new size, `git lfs ls-files | wc -l` for the count, and check out an old tag to confirm the files still resolve.
6. Force-push with lease, then tell everyone to delete their clone and clone again. A pull onto rewritten history produces a mess that takes longer to untangle than the re-clone.
7. The remote reclaims space on its own schedule and sometimes only after a support request, so the size drop may not be immediate.

## LFS in CI

CI is where LFS bandwidth quotas are consumed, because every job clones. Two mitigations, both worth setting by default:

- Jobs that do not need binaries — linting, unit tests, static analysis — skip the download entirely with `GIT_LFS_SKIP_SMUDGE=1` set in the environment, or by disabling LFS in the checkout step and not fetching.
- Jobs that do need them cache the LFS object store between runs, keyed on the commit's LFS file list, so an unchanged asset set is downloaded once rather than per build.

A build job that fails with an LFS quota error mid-month is the usual way a team discovers both of these.

## When to leave Git

Git plus LFS handles a small team and a repository in the low tens of gigabytes. Past that, the things it lacks start costing real time: exclusive checkout on binaries, partial workspaces so an artist syncs only the folders they need rather than the whole project, and a server that streams a single file without a full object store.

Perforce Helix Core is the industry default for this and is what Unreal integrates with directly; Unity Version Control fills the same role with an interface artists tolerate better. Both are worth proposing honestly rather than pushing LFS past what it does well. A reasonable threshold: more than a few full-time artists, more than a few tens of gigabytes of live assets, or a team where the people editing binaries are not the people comfortable with Git.

## Secrets that hide in project files

Two project files routinely accumulate credentials and get committed without anyone reading them: Godot's export presets file, which stores Android keystore paths and can hold the keystore password, and the per-platform publishing settings in Unity and Unreal, which hold signing configuration. Keystores, provisioning profiles and signing certificates belong in a secret store and are injected by the build job, never committed. Check for them before the first push, not after, because a secret removed in a later commit is still in the history.
