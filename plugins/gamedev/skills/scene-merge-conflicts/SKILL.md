---
name: scene-merge-conflicts
description: "Stop teams losing work to conflicts in scenes, prefabs, blueprints and other binary or structured assets. Classifies each asset type as mergeable text, structured but fragile (Unity YAML, Godot tscn) or opaque binary (Unreal uasset and umap), locks opaque binary from day one with read-only checkout, shrinks the surface two people share with sub-scenes and data files, registers the engine merge tool for fragile text, checks merges by opening them, and adds an ownership map and a CI check for conflict markers and missing meta files. Use whenever someone says \"two people edited the same scene and one lost work\", \"unity merge conflict in prefab\", \"unreal blueprint can't be merged\", \"should we use file locking\" or \"Godot tscn conflicts\". Not for LFS thresholds and source-versus-shipped files (game-assets), code review (code-review), or pipeline design (ci-pipeline-design)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Scene Merge Conflicts

The work is done when no two people can silently overwrite each other's edit to a scene, prefab or blueprint: binary assets cannot be edited without a lock, fragile text assets merge through the engine's own tool and are opened and checked afterwards, the team knows who owns which scene, and CI rejects a conflict marker or a missing meta file.

The usual failure is trusting the version control tool to merge what it cannot read. A binary blueprint has no merge: the second person to push either overwrites the first or is told there is a conflict they cannot resolve, and the cheapest resolution is to pick one side and discard the other's day. A Unity scene merges cleanly as text and loads as a scene with missing references, because the text was valid and the meaning was not. The cure is mostly prevention, since the cost of a merge is paid in someone's lost afternoon.

## Scope

Use for: lost work from two edits to one asset; a merge conflict in a scene, prefab or blueprint; choosing between file locking and merging; setting up version control for a new project; Unity, Unreal and Godot asset conflicts.

Do not use for: where large files live, LFS size thresholds, and deciding what is source and what is shipped, which is `game-assets`. Reviewing the code changes in a pull request is `code-review`. Designing the build and test pipeline around the repository is `ci-pipeline-design`; this skill only specifies the one check the pipeline should carry.

## Workflow

### 1. Classify every asset type

List the file extensions in the repository and put each in one of three classes. The class decides the policy.

| Class | Examples | Policy |
| --- | --- | --- |
| Mergeable text | Source code, JSON and CSV data, shader text, text-only config | Normal branching and merging |
| Structured but fragile | Unity YAML scenes, prefabs and assets; Godot `.tscn` and `.tres` | Text, so it can merge, but a clean merge can still be wrong; use the engine merge tool and verify |
| Opaque binary | Unreal `.uasset` and `.umap`; Photoshop, Blender, Maya and audio project files | Cannot merge; exclusive lock |

Write the table into the contributor guide. The question to answer for each extension is whether a human can read the diff and a tool can combine two diffs; if either is no, it is not mergeable.

### 2. Lock opaque binary from the first commit

Lock before the first conflict, not after. Pick the mechanism your version control supports:

- **Perforce**: set the exclusive-open modifier on the type in the typemap (a type such as `binary+l`), so a second user cannot open the file for edit while it is checked out.
- **Git with LFS**: track the pattern as lockable and use LFS locks, for example `git lfs track "*.uasset" --lockable`, then `git lfs lock <path>`, `git lfs locks` to list and `git lfs unlock <path>` to release. Lockable files are checked out read-only until you hold the lock, so an unlocked edit is physically blocked. Locking needs an LFS server that supports the locks API; confirm with your host before relying on it.
- **Plastic**: exclusive checkout rules for the patterns in question.

The read-only checkout is the part that works: a policy that asks people to remember to lock fails the first time somebody is in a hurry. Also mark these patterns as binary in `.gitattributes` so no tool tries a text merge.

Locks have a cost. A lock held over a weekend blocks a colleague, so require unlocking after a push and have a named person who can break a lock. See `references/locking-and-merge-setup.md` for the attribute lines, the lock etiquette and the stale-lock routine.

### 3. Shrink the surface two people touch together

Most conflicts come from several people needing the same file for unrelated reasons. Reduce that:

- Split one large scene or level into additive sub-scenes per area or discipline (layout, lighting, audio, gameplay), loaded together at runtime, so each discipline edits its own file.
- Use prefabs and nested scenes as the unit of ownership; edit the prefab, not a per-instance override in the scene.
- Move gameplay data out of scenes into data files (tables, scriptable objects, resources, JSON) that are text and merge line by line. A designer tuning numbers should not need to open the scene.
- Keep generated and cached data out of version control.

The test of success is that two people doing ordinary work on different things rarely need the same file.

### 4. Register the smart merge for fragile text

For Unity, serialise as text and make meta files visible: in the project's editor settings set asset serialisation to force text and version control to visible meta files. Commit every `.meta` file with its asset; a missing one regenerates a different identifier and breaks every reference to it.

Register the engine's tool, UnityYAMLMerge, with the version control client so conflicts in scenes and prefabs go through it rather than a line-based text merge. With Git it is configured as a merge tool; the form from Unity's documentation is:

```text
[merge]
    tool = unityyamlmerge

[mergetool "unityyamlmerge"]
    trustExitCode = false
    cmd = '<path to UnityYAMLMerge>' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```

The executable ships with the editor, in its install folder. Rehearse the setup on a scratch branch with a deliberately conflicting scene before relying on it, and put the config in a checked-in script teammates run, since the setting lives in each person's local Git configuration. Godot `.tscn` and `.tres` files are text; they merge, and their conflicts are usually reorderings and renumbered resource identifiers, so the same rule applies: check the result.

### 5. Check every merge result by opening it

A clean merge of a fragile file is not a correct one. After every merge of a scene or prefab, open it in the editor and look: references intact, no missing scripts, the objects both people added are present, nothing duplicated, transforms plausible. Make this part of the merge procedure, and name who does it. In Unity a missing reference shows as a "Missing" field in the inspector, and in Godot as an error on load; neither shows in the diff.

### 6. Write the ownership map

A short file in the repository: for each scene, prefab family and blueprint group, the person or discipline that owns it. The rule is that one person edits a given scene at a time, and anyone else asks the owner or takes the lock. Where there is no lock mechanism (fragile text), the team channel carries the status line: who is in which scene, since when. This replaces the afternoon of discovering two people were in the same level. The map also tells a reviewer who should approve a change.

### 7. Make CI catch the leftovers

Add one check that fails the build when a scene file contains a conflict marker or when an asset lacks its `.meta` file (or a `.meta` lacks its asset). Both survive review because nobody reads thousands of lines of serialised scene. `references/locking-and-merge-setup.md` has a script for it. Run it on pull requests and on the main branch.

### 8. Report

```markdown
## Asset classes
[Each extension and its class.]

## Locking
[Mechanism, patterns locked, read-only enforced, stale-lock owner.]

## Surface
[Scene splits made, data moved out of scenes.]

## Merge tooling
[Tool, where registered, rehearsal result.]

## Ownership
[Map location and the channel status convention.]

## CI
[The check, where it runs, and the first run's result.]
```

## Anti-patterns

**Merging binary by choosing a side.** Somebody's work is discarded and nobody is told.

**Trusting a clean merge of a scene.** Valid text is not a valid scene; open it.

**Asking people to remember to lock.** Read-only checkout makes the mistake impossible, a reminder does not.

**Overrides in the scene instead of the prefab.** Every override is another reason for two people to need the same file.

**One giant level file.** It guarantees the conflict; split it by discipline and area.

**Ignoring meta files.** Leaving them out of version control or committing them late breaks references for everyone who pulls.

## References

- `references/locking-and-merge-setup.md` — read at steps 2, 4 and 7: the `.gitattributes` and Perforce typemap lines, lock etiquette and the stale-lock routine, the per-engine serialisation settings, and the CI check script.
