# Locking and merge setup

Read this at steps 2, 4 and 7 of `SKILL.md`. It has the configuration lines, the etiquette that keeps locks from becoming a bottleneck, and the CI check.

## Contents

- [Git attributes for locking](#git-attributes-for-locking)
- [Perforce typemap](#perforce-typemap)
- [Lock etiquette and stale locks](#lock-etiquette-and-stale-locks)
- [Engine serialisation settings](#engine-serialisation-settings)
- [The CI check](#the-ci-check)
- [Rehearsal](#rehearsal)

## Git attributes for locking

With Git LFS, mark the opaque patterns lockable and stored in LFS:

```bash
git lfs track "*.uasset" --lockable
git lfs track "*.umap" --lockable
git lfs track "*.psd" --lockable
```

That writes lines like `*.uasset filter=lfs diff=lfs merge=lfs -text lockable` into `.gitattributes`. Commit the file. Lockable files are read-only in the working tree until locked, which is the enforcement. Day-to-day commands:

```bash
git lfs lock Content/Maps/Level01.umap
git lfs locks
git lfs unlock Content/Maps/Level01.umap
```

`git lfs locks` lists who holds what. Unlocking a file someone else holds requires the force option and the right permission on the server; keep that for the stale-lock routine below. Locks are a feature of the LFS server, so confirm that your host supports them before rolling this out.

For binary files that are not in LFS, still stop any text merge attempt:

```text
*.fbx binary
*.wav binary
```

## Perforce typemap

Exclusive open is a file type modifier, set once in the typemap so every new file of that kind inherits it:

```text
TypeMap:
    binary+l //....uasset
    binary+l //....umap
```

With `+l`, only one user can have the file open for edit at a time. Files are read-only in the workspace until opened, as is normal in Perforce. Apply the typemap change to files already in the depot with a retype, which the server administrator should run.

## Lock etiquette and stale locks

- Lock when you start editing; unlock when you push. Never leave a lock overnight or over a weekend without a note in the team channel.
- Put the lock's reason in the channel, one line: the file, what you are doing, how long.
- Keep a list of people who can break a lock, and the rule for doing so: ask the holder, wait a set time, then break and tell them. Work in an unpushed local change that is lost on a broken lock is the holder's to recover, so ask before breaking.
- Review the lock list weekly. A lock older than a few days is either forgotten or a sign the asset is too large to edit safely and should be split.
- Locks are not a substitute for ownership; they stop simultaneous edits, not two people making incompatible changes in turn.

## Engine serialisation settings

- **Unity**: in project settings under the editor section, set Asset Serialization to Force Text and Version Control to Visible Meta Files. Commit meta files with their assets, and never delete a meta file by hand. Check the settings in as part of the project settings files.
- **Unreal**: assets are binary and the engine's own source control integration supports checkout and, with the right provider, locking. Use it, so the editor itself refuses to edit a file locked by someone else.
- **Godot**: scenes and resources are text by default. Prefer the text format for resources (`.tres`, `.tscn`) over binary variants (`.res`, `.scn`) in version control.

## The CI check

A script that fails on a conflict marker in any scene-like file and on a missing meta file. Adjust the paths and extensions to the project.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

fail=0

# 1. Conflict markers in serialised scene data.
if git grep -nE '^(<<<<<<< |>>>>>>> )' -- '*.unity' '*.prefab' '*.asset' '*.tscn' '*.tres' '*.mat'; then
  echo "conflict markers found in scene data" >&2
  fail=1
fi

# 2. Every tracked Unity asset has its meta file, and every meta file has its asset.
while IFS= read -r -d '' path; do
  # Unity does not import, and so writes no meta file for, hidden names
  # (leading dot), names ending in a tilde, or .tmp files.
  case "/$path" in
    */.*|*'~'|*'~/'*|*.tmp) continue ;;
  esac
  case "$path" in
    *.meta)
      base="${path%.meta}"
      if ! git ls-files --error-unmatch -- "$base" >/dev/null 2>&1 && [ ! -d "$base" ]; then
        echo "meta file without asset: $path" >&2
        fail=1
      fi
      ;;
    *)
      if [ ! -e "$path.meta" ]; then
        echo "asset without meta file: $path" >&2
        fail=1
      fi
      ;;
  esac
done < <(git ls-files -z -- 'Assets')

exit "$fail"
```

Paths Unity ignores are skipped before the meta test: any segment starting with a dot or ending in a tilde, and `.tmp` files. A tracked `Assets/.gitkeep` or a `Docs~/` folder has no meta file on a valid project, and a gate that fails on valid data gets switched off. Conflict marker lines begin with seven characters followed by a space; the pattern anchors at the line start so a string inside an asset does not match. Directories also need a meta file in Unity; the script only walks tracked files, so add a check over directories with `find Assets -type d` if the project has empty-folder problems. Run it on every pull request. The marker check is for the content of the commit, so it also catches a conflict committed with the markers left in.

## Rehearsal

Before relying on any of this, rehearse on a scratch branch:

1. Make two branches that edit the same scene in different objects, then merge them with the registered merge tool. Open the result.
2. Make two that edit the same object. Confirm the tool reports the conflict instead of choosing silently.
3. With locking on, try to edit a locked binary as a second user. The file should be read-only and the editor or client should refuse.
4. Commit a scene with a conflict marker and a file without its meta file, and confirm the CI check fails on both.
