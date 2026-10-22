# Measuring and verifying a purge

## Size queries

Total and packed size, then the biggest objects:

```bash
git count-objects -vH
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '$1=="blob"' | sort -k3 -n -r | head -20
```

A blob's `%(rest)` is a path where it was reached; the same blob can live under several. `git filter-repo --analyze` writes a fuller report under `.git/filter-repo/analysis` in a fresh clone, including the paths ever deleted but still in history and the biggest by packed size.

Files deleted at some point still cost size:

```bash
git log --all --diff-filter=D --name-only --pretty=format: | sort -u | head -50
```

The listing shows deleted files: they cost size but nothing in the tree shows it.

Where did the file enter and where is it still referenced?

```bash
git log --all --oneline -- <path>
git branch -a --contains <commit>
git tag --contains <commit>
```

## Choosing the tool

| Situation | Tool |
| --- | --- |
| Remove named files or directories from all history | `git filter-repo --invert-paths --path <p>` |
| Remove every blob above a size | `git filter-repo --strip-blobs-bigger-than <size>` |
| Keep large files but store them as pointers | `git lfs migrate import --include=<patterns> --everything` |
| Rewrite a string inside files | `git filter-repo --replace-text <file>` |
| Only the latest commit is wrong | Amend and force-push that branch; rotate a secret anyway |

## After an LFS migration

LFS stores the content on the host's LFS storage, which counts against a quota and is not in the Git packfile. Run `git lfs push --all origin` before pushing refs so the host holds the content, not only pointers. Check that `.gitattributes` now lists the patterns, that `git lfs ls-files` shows the migrated files, and that CI checkouts fetch LFS objects (`lfs: true` on the checkout step, or `git lfs pull`). Ask whether the quota covers the total, since every historical version of a migrated file is uploaded.

## Collaborator messages

Before the mirror clone (freeze):

```text
The history of <repository> will be rewritten after <time> to remove <what>.
1. Push anything you need to keep to a branch before <time>, or save a patch with git format-patch.
2. After <time>, push nothing to <repository> until the all-clear message.
```

After the force push (all-clear):

```text
The history of <repository> was rewritten on <date> to remove <what>.
Do not pull, merge or rebase old work onto it, and push nothing from an old clone, not even a branch.
1. Delete your local clone and run: git clone <url>
2. Re-apply saved work to the new clone as patches (git am) or by cherry-picking onto the new history.
CI caches and build agents were cleared. Questions to <owner>.
```

Reapplying a branch with `git cherry-pick` from the old clone brings only the commits you pick; merging the old branch brings the removed history back.

## Verification checklist

- Fresh clone size is smaller by roughly the measured amount (`git count-objects -vH`).
- The blob listing no longer shows the named paths or any blob over the cap.
- `git log --all -S'<fragment>'` returns nothing.
- A secret scanner run over the full history is clean.
- `git ls-remote origin` shows no unexpected refs beyond heads, tags and the host's own pull refs, and the support request for those is filed.
- Branch protection restored; every tag of concern was rewritten and pushed.
- Forks, mirrors, CI caches and package registries that copied the data are listed with an owner for each.
