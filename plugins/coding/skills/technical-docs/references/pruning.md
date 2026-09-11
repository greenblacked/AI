# Pruning a documentation set

Read this when auditing documentation that already exists rather than writing a new page.
The premise is that documentation sets fail by accumulation: adding is easy and socially
safe, deleting feels destructive, so stale pages survive next to their replacements and
the reader is left to arbitrate between them.

## Contents

- [Gathering the evidence first](#gathering-the-evidence-first)
- [The audit pass](#the-audit-pass)
- [Deciding: fix, merge, archive, delete](#deciding-fix-merge-archive-delete)
- [Archive and redirect mechanics](#archive-and-redirect-mechanics)
- [Making deletion routine](#making-deletion-routine)
- [What not to delete](#what-not-to-delete)

## Gathering the evidence first

Audit on data, not on impressions. Four cheap sources, in ascending order of effort:

```bash
# Age: when each page was last touched at all.
git ls-files '*.md' | while read -r f; do
  printf '%s %s\n' "$(git log -1 --format=%ad --date=short -- "$f")" "$f"
done | sort

# Reachability: pages nothing links to.
git ls-files '*.md' | while read -r f; do
  b=$(basename "$f")
  c=$(grep -rl --include='*.md' -F "$b" . | grep -v "^\./$f$" | wc -l)
  [ "$c" -eq 0 ] && printf 'unreferenced: %s\n' "$f"
done

# Declared staleness: pages carrying a last-verified stamp, oldest first.
grep -rEio --include='*.md' 'last[ -]verified[^0-9]{0,12}[0-9]{4}-[0-9]{2}-[0-9]{2}' . \
  | sed -E 's/^([^:]*):.*([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\2 \1/' | sort
```

The reachability check matches on the basename, so read it as a shortlist rather than a
verdict: two `setup.md` files in different directories mask each other, and a page reached
only from a mkdocs nav, a sidebar or an HTML index reads as unreferenced when it is not.
Confirm each hit by searching for its full path before deleting anything.

The fourth source is page views, from whatever hosts the documentation. It is the
strongest single signal and it is usually available and never looked at: a page with no
views in twelve months has no defender, whatever anyone says in the audit meeting.

## The audit pass

Work page by page, in one sitting, spending no more than a few minutes on each. Long
audits do not finish, and an unfinished audit changes nothing.

For each page, answer three questions in order and stop at the first that decides it:

1. **Does it execute?** Run the first three commands. A failure decides the page
   immediately — it is actively harmful, because it sends a reader confidently wrong, and
   the cost is higher than the page's entire lifetime benefit.
2. **Is it reached?** No inbound links and no views means nobody depends on it, whatever
   its quality.
3. **Is it contradicted?** Another page describing the same thing differently makes both
   untrustworthy, because the reader has no way to choose.

A page that executes, is reached and is uncontradicted is fine even if it is old. Age
alone is not a defect; unverified age is.

## Deciding: fix, merge, archive, delete

| Finding | Do this | Not this |
| --- | --- | --- |
| Commands fail, the page is still needed | Fix and re-stamp today, in this change | File a ticket; the evidence is in hand now and will not be later. |
| Commands fail, the page is not needed | Delete it | Add a "possibly out of date" banner, which nobody acts on and which readers ignore. |
| Two pages, one correct | Merge into the one with the better URL, delete the other, redirect | Leave both and link them to each other. |
| Describes a replaced system | Archive with a banner naming the replacement | Delete outright, if anyone still runs the old system or needs its history. |
| Accurate but unreachable | Link it from the index, or delete it | Leave it discoverable only by search, which is how duplicates get written. |
| Stamp over twelve months old, content plausible | Re-verify by execution, or restamp as unverified with today's date | Update the date without running anything, which is the single most damaging edit in this whole area. |

Restamping without verifying deserves its own warning: it converts an honestly stale
document into a dishonestly fresh one, and it removes the only signal a reader had.

## Archive and redirect mechanics

- **Keep the URL alive.** Deleting a page that other documents, tickets and chat history
  link to produces a dead end at exactly the moment someone needed it. Redirect it to the
  replacement; where the tooling cannot redirect, leave a one-line stub pointing on.
- **Archive under a visibly separate path** — `docs/archive/` — with a banner at the top
  of each page naming the replacement and the date it was archived. A banner below the
  fold is not read.
- **Exclude the archive from search and from the index** where the tooling allows it.
  Archived documentation that still competes in search results has not been archived.
- **Trust the version history.** Deleted documentation is recoverable by anyone with the
  repository, which makes deletion a cheap and reversible act. Say so when people
  hesitate; the hesitation is usually about loss that cannot actually occur.

## Making deletion routine

The audit is a one-off correction. What stops the set re-accumulating is a habit attached
to changes people already make:

- **Delete in the same change that made the page wrong.** The person changing the
  behaviour is the only one who knows which page it invalidated, and they know it now.
- **Treat a documentation change as part of the diff under review.** A reviewer asking
  "which page does this invalidate" costs nothing and catches most of it.
- **Re-stamp on execution.** Whenever anyone follows a document successfully, they update
  the date. This makes verification a by-product of use rather than a scheduled task, and
  scheduled documentation reviews are the first thing dropped in a busy quarter.
- **Cap the set.** A team that agrees an upper bound on the number of pages it maintains
  makes adding a page a trade rather than a free action, which is the only mechanism that
  reliably keeps a set small enough to keep true.

## What not to delete

- **Anything an outside party depends on**: published API guides, integration documents,
  anything linked from a contract or a support macro. Deprecate these on a stated timeline
  instead.
- **Records of decisions**, which are historical by nature and are not stale merely because
  the decision is old. Those belong to `decision-record` and are governed differently.
- **Incident write-ups**, whose value is precisely that they describe a system that no
  longer behaves that way.
- **The only description of a system still running**, however bad. Fix it, or write its
  replacement first. Deleting the last description of a live system converts a documented
  liability into an undocumented one.
