# Search cookbook

Run these in the frozen repository (see step 1 of the skill). Each scenario lists the key to search on and how to confirm the candidate.

## Hard reset or checkout that moved the branch

The commit you want is where the branch pointed a moment ago.

```bash
git reflog show <branch> --date=iso | head -20
git rev-parse ORIG_HEAD
git log --oneline -5 <branch>@{1}
```

Confirm: `git diff --stat <candidate> <branch>` shows exactly the work you lost.

## Dropped or cleared stash

`git stash drop` prints the SHA when it runs; check the terminal scrollback first. Otherwise a stash is a merge-shaped commit that no ref points to.

```bash
git fsck --unreachable --no-reflogs | awk '/commit/ {print $3}' |
  while read -r c; do
    git log -1 --format="$c %ad %s" --date=iso "$c"
  done | grep -E 'WIP on|On [^ ]+:'
```

Stash commits are titled `WIP on <branch>: ...` or `On <branch>: <message>`. Confirm with `git log -1 --stat <sha>`, then `git stash apply <sha>` or `git branch rescue/stash <sha>`. The third parent, when present, holds untracked files saved with `-u`.

## Deleted branch

Git prints the tip when you delete: `Deleted branch x (was abc1234)`. Otherwise find the last time HEAD was on it.

```bash
git reflog show --date=iso | grep -n 'checkout: moving from <branch> '
```

Each match is a `HEAD@{n}` entry where HEAD left the branch (grep -n counts from 1, so n is the printed line number minus one when the reflog is unfiltered). The reflog lists newest first, so the entry that records the last thing done on the branch is the next, older one: `git rev-parse 'HEAD@{n+1}'` is the branch tip, assuming nothing moved the branch without HEAD on it. Check with `git log --oneline -5 <sha>`. If the reflog has expired, fall back to `git fsck --lost-found` and search candidate commits by message.

## Amended or rebased away commit

The original commit is still in the HEAD reflog under the pre-rewrite position.

```bash
git reflog show --date=iso | head -40
git range-diff <base>..<pre-rewrite-sha> <base>..<branch>
```

`range-diff` pairs commits across the rewrite; a line marked `<` with no partner is a commit the rewrite dropped.

## Detached HEAD that moved on

Commits made while detached are reachable only from the reflog.

```bash
git reflog show --date=iso | head -30
git branch rescue/detached <sha-of-latest-detached-commit>
```

## Lost merge or conflicting resolution

A merge commit has two parents. Find it, then check both sides survived.

```bash
git log --merges --all --oneline --since='2 weeks ago'
git diff <merge>^1 <merge> --stat
git diff <merge>^2 <merge> --stat
```

## Force-pushed tip

In order of cost: a colleague's `git rev-parse origin/<branch>` from before they fetched; the CI run for the last good push (`gh run list --branch <branch> --json headSha,createdAt`); the pull request's own timeline, whose force-push events show the commit before and after (visible on the pull request page and through the GraphQL `HeadRefForcePushedEvent` fields `beforeCommit` and `afterCommit`).

A commit the host still serves can be fetched by SHA: `git fetch origin <sha>` works when the host allows fetching unadvertised objects.

## Dangling blobs from never-committed work

Only content that was staged survives.

```bash
git fsck --lost-found --no-reflogs        # writes dangling blobs to .git/lost-found/other
for b in $(git fsck --no-reflogs --lost-found | awk '/dangling blob/ {print $3}'); do
  printf '%s  ' "$b"; git cat-file -s "$b"
done | sort -k2 -n -r | head -20
git cat-file -p <blob-sha>
```

Blobs carry no filename; match on content by printing each candidate with `git cat-file -p <sha>` and searching for a string you remember.

## Choosing between candidates

Prefer the candidate whose diff against the expected state is smallest, whose author and date match, and whose descendants include the last commit you remember. If two fit, restore both onto separate branches and compare with `git range-diff`.
