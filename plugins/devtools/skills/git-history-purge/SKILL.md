---
name: git-history-purge
description: "Removes a committed secret, huge binary or private file from every ref, or shrinks a bloated repository. Rotates a credential first because a rewrite never un-leaks it, measures the real culprits with count-objects and a cat-file blob listing, rewrites a fresh mirror clone with git filter-repo (git lfs migrate when files must stay), never filter-branch. Then the skipped step: the host still serves old objects through refs/pull and cached views, so list them, request a host purge, have every collaborator re-clone, and verify with a second listing and a secret scanner. Use whenever someone says \"someone committed a 400 MB file\", \"our clone takes ten minutes\", \"purge this key from history\", \"move our assets to LFS\". Not for the leaked credential itself (secret-rotation), restoring rather than removing (git-history-recovery), or a broken rebase (branch-rebase-repair)."
allowed-tools: Bash(git:*), Bash(gitleaks:*), Read, Grep, Glob
---

# Git History Purge

Done means the content is absent from every ref on the host and in every maintained clone, the repository size has dropped by the amount you measured, a scanner finds nothing in the new history, and everyone who held the old history has been told to discard it.

A history rewrite is destructive, hard to reverse and, for a leaked secret, not a fix at all: anyone who cloned or fetched while the secret was public still has it, and the host may serve the old objects for days. The failure mode is a tidy-looking local rewrite, a force push, and a sense of closure while the pull-request refs, forks and caches keep the data reachable.

## Scope

Use for: a committed secret or private file that must leave history, a binary that bloated the repository, moving large files to LFS, a clone that has become slow.

Do not use for: rotating the credential (`secret-rotation`), getting lost commits back (`git-history-recovery`), or repairing a branch after someone else's rewrite (`branch-rebase-repair`).

## Workflow

### 1. If it is a credential, rotate it first

Treat it as compromised from the moment it was pushed. Hand off to `secret-rotation` and wait for the old value to be revoked before rewriting anything. A rewrite that precedes rotation buys a false sense of safety and delays the one action that works. Note the commit SHAs and paths where it appeared; you need them to verify later.

### 2. Measure before cutting

Name the culprits so the rewrite removes exactly them.

```bash
git count-objects -vH
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '$1=="blob"' | sort -k3 -n -r | head -20
```

Record the paths, sizes and the total repository size now. For a secret, find every path and commit it appeared in with `git log --all -S'<fragment>' --oneline`, using a fragment that is not itself the whole secret. `references/measure-and-verify.md` has the fuller queries, including per-path history size.

### 3. Freeze pushes, then rewrite in a fresh mirror clone

Before cloning, tell every collaborator to stop pushing and to push anything they need to keep to a branch by a stated deadline (template in `references/measure-and-verify.md`). Anything pushed between the mirror clone and the force push is silently overwritten, and a branch pushed from an old clone after the rewrite carries the removed blob back onto the host. Enforce the freeze with branch protection if the host allows it, and clone only once the deadline has passed.

Work in a throwaway mirror, never in anyone's working repository: `git filter-repo` refuses to run on a non-fresh clone for exactly that reason.

```bash
git clone --mirror <url> purge.git && cd purge.git
git filter-repo --invert-paths --path <file-or-dir>          # remove named paths
git filter-repo --strip-blobs-bigger-than 10M                # or: remove every blob over a size
```

To keep large files but move them out of history into LFS, use the migration command instead, over all refs:

```bash
git lfs migrate import --include="*.psd,*.zip" --everything
```

The migration leaves the content in the local LFS store; the host holds only pointers until it is uploaded, so run `git lfs push --all origin` after adding the remote in step 4 and before the ref pushes.

Do not use `git filter-branch`; it is slow, easy to get subtly wrong and its own documentation points to `git filter-repo` instead. For replacing text inside files rather than removing files, filter-repo's `--replace-text <expressions-file>` takes a file of patterns; review its output, since the rewritten blobs change every descendant commit.

Run `git filter-repo --analyze` beforehand if you want a report of path sizes it writes under `.git/filter-repo/analysis`.

### 4. Push, then deal with what the host still holds

filter-repo removes the `origin` remote on purpose, so you add it back deliberately and push branches and tags, not a blind mirror, because pushing `refs/pull/*` is rejected and meaningless.

```bash
git remote add origin <url>
# if you migrated to LFS: git lfs push --all origin
git push --force --all origin
git push --force --tags origin
```

These two force pushes rewrite the shared host and are expected to prompt for confirmation; do not approve them until the verification below is ready. Protected branches need their protection lifted for the push and restored after; do that as a visible, time-boxed step. Then list what the host still serves:

```bash
git ls-remote origin | grep -v -E 'refs/(heads|tags)/'
```

On GitHub, `refs/pull/*` refs are read-only and keep the old commits reachable by SHA; they are not rewritten by your push. The sensitive commits also stay viewable by direct URL, in forks and in cached views until the host collects them. The remedy is a support request to the host asking for garbage collection and cached-view purge, naming the repository, the commit SHAs from step 1 and, for a secret, saying it has been rotated. Closing and deleting pull requests alone does not remove the refs. Forks of the repository are separate repositories and need their owners to act.

### 5. Collaborators re-clone

Tell everyone, in one message, that the rewrite is done: discard local clones and re-clone, and push nothing from an old clone, not even a branch. Merging or rebasing an old clone onto the new history reintroduces the removed objects and the original problem. Also cover CI caches, build agents, mirrors and any tooling that keeps a checkout. `references/measure-and-verify.md` has both message templates.

### 6. Verify

Repeat the step 2 listing on a fresh clone and compare with the earlier sizes. Run a secret scanner over the whole new history (`gitleaks git` over the repository, or `gitleaks detect` on versions before 8.19) and search for the fragment again with `git log --all -S'<fragment>'`. After an LFS migration, check that a fresh clone fetches the LFS objects (`git lfs fetch --all` and `git lfs ls-files`). Confirm the host's repository size after garbage collection, which may lag. A repository that still lists the blob, or a scan that still hits, means a ref was missed: look at `git for-each-ref` for stray refs, notes and tags.

## Hand back

The measured before and after sizes, the exact filter command run, the refs pushed, the remaining host-side references and the support request status, the collaborator message sent, the scanner result, and whether the credential was rotated first and by whom.

## Anti-patterns

**Rewriting before rotating.** The secret stays valid and public through every step that follows.

**Running the rewrite in your working clone.** A mistake there has no copy to return to; the mirror clone is the copy.

**Forgetting the host.** Local history is clean while the pull-request refs still serve the file.

**Letting a colleague merge their old branch.** One merge restores the removed blob into the clean history.

## Reference files

- `references/measure-and-verify.md` — read in steps 2, 3, 5 and 6: size and path-history queries, the LFS conversion checks, the collaborator message and the verification checklist.
