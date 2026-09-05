---
description: Draft a weekly status update from what actually shipped — merged pull requests, commits and closed issues — bottom line first, with every number sourced or marked missing.
argument-hint: [since date, default 7 days ago]
allowed-tools: Bash(gh:*), Bash(git:*), Read, Glob
---

Draft this week's update from evidence rather than memory. Use `$0` as the start of the
window, defaulting to seven days ago.

Gather first:

```bash
gh pr list --state merged --search "merged:>=$0" --json number,title,mergedAt,author,additions,deletions
gh issue list --state closed --search "closed:>=$0" --json number,title,closedAt,labels
git log --since="$0" --no-merges --format='%h %s'
```

Then write it bottom line up front. The first sentence says where things stand and what,
if anything, is needed from the reader. Everything after it is support. An update that
builds to its conclusion wastes the attention of the only people who can unblock you.

Structure:

- **Bottom line.** One or two sentences. State the position, not the activity.
- **Shipped.** What changed for a user or an operator, in their terms. A merged pull
  request is evidence, not an outcome — say what it enables.
- **In flight.** What is moving, with the expected landing and the confidence in it.
- **Risks and asks.** Named, with an owner and a date. A risk with no ask is a
  weather report.

Rules that keep it trustworthy:

- Every number is sourced from the commands above or marked as not measured. Do not
  estimate a figure and present it as counted.
- Say slipped when something slipped. An update that has never contained bad news is one
  nobody reads for signal.
- Cut anything the reader cannot act on and would not miss.

For the reasoning behind the format, including when to use Minto instead for a
persuasive case, use the `status-update` skill.
