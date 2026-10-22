# Diagnosing bogus conflicts

Match what you see to a row, run its confirming check, then use the repair.

| Pattern | What you see | Confirm | Repair |
| --- | --- | --- | --- |
| Parent PR squash-merged | `origin/main` has one commit titled like the parent PR; your branch still has the parent's several commits under yours | `git log --oneline origin/main..<branch>` lists commits that are not yours; the parent's files in `git diff origin/main <branch> -- <parent paths>` differ only by whitespace or are empty | `git rebase --onto origin/main <old-parent-tip> <branch>` |
| Parent PR rebase-merged | The parent's commits exist upstream with new SHAs | `git cherry -v origin/main <branch>` marks them `-` | Plain `git rebase origin/main` usually drops them; if it does not, use `--onto` |
| Cherry-picked fix | One or two commits conflict with themselves | `git cherry` marks them `-` | Let the rebase drop them, or `git rebase --onto` past them |
| Base amended and force-pushed | The old commits the branch sits on no longer exist upstream | `git reflog show origin/<base>` shows the previous tip; `git merge-base origin/<base> <branch>` is far back | `git rebase --onto origin/<base> <old-base-tip> <branch>` |
| Stack retargeted | The middle branch was merged; the top branch still includes it | `git log --oneline origin/main..<top>` shows the middle branch's commits | `git rebase --update-refs --onto origin/main <middle-tip> <top>` |
| Genuine drift | A few conflicts in files you and others both edited | `git merge-tree --write-tree --name-only` names only files you touched | Resolve normally; `rerere` keeps the result |

## Conflict count sanity check

Compare the number of conflicted paths with the number of files your commits touch:

```bash
git diff --name-only <old-parent-tip> <branch> | wc -l
git merge-tree --write-tree --name-only --no-messages origin/main <branch> | sed -n '2,$p' | wc -l
```

The first command counts the files your own commits touch, measured from the old parent tip so the parent's files are excluded. The second prints a tree ID on the first line, then only the conflicted paths because `--no-messages` suppresses the Auto-merging and CONFLICT lines, so the count is conflicts alone. A conflict list far larger than your touched-file count means the branch carries other people's changes, since a path can only conflict if the branch changed it.

## Finding the old parent tip when the reflog is gone

1. The pull request page shows the last commit of the parent branch before it merged.
2. A teammate's checkout still has `origin/<parent>` at the old tip.
3. The CI run for the parent's last push records the SHA it built.
4. As a last resort, find the commit just before your first commit: `git log --oneline --reverse origin/main..<branch>` then pick the first commit you wrote; its parent in that listing is the boundary.

## Rerere

`git config rerere.enabled true` records each conflict resolution and replays it when the same conflict reappears. It matters most when a repair takes more than one attempt, or when you rebase the same branch repeatedly onto a moving base. `git rerere status` lists paths with recorded state, and `git rerere forget <path>` discards a bad recorded resolution.
