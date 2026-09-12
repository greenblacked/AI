# Reading a repository's history as evidence

Read this at step 6 of the workflow, and again before proposing any change that feels
obvious. History answers questions the current tree cannot: which code is alive, which is
feared, who owns what, and what has already been tried and reverted.

## Contents

- [What each query answers](#what-each-query-answers)
- [Churn: where the requirements are still moving](#churn-where-the-requirements-are-still-moving)
- [Ageing: what has not moved and why that varies](#ageing-what-has-not-moved-and-why-that-varies)
- [Ownership and bus factor](#ownership-and-bus-factor)
- [Reverts and abandoned attempts](#reverts-and-abandoned-attempts)
- [Coupling: files that always change together](#coupling-files-that-always-change-together)
- [When the history is not there](#when-the-history-is-not-there)

## What each query answers

| Question | Query | How to read the answer |
| --- | --- | --- |
| How old is this really? | `git log --format=%ad --date=short \| tail -1` | A first commit far younger than the product means an import, and everything before it is invisible. |
| What is still being worked on? | churn over 12 months, below | The top ten files are the system's active surface. |
| What is frozen? | files with no commit in 24 months | Either stable infrastructure or abandoned; the tests decide which. |
| Who knows this? | authors per path | One author, last seen a year ago, is an ownership hole. |
| Has this been tried? | `--grep='revert' -i` | A revert is the strongest negative evidence available. |
| What moves together? | co-change, below | Hidden coupling the directory layout denies. |

## Churn: where the requirements are still moving

```bash
git log --since='12 months ago' --name-only --format= \
  | grep -v '^$' | sort | uniq -c | sort -rn | head -30
```

High churn is not a defect. It marks the part of the system where the business is still
deciding what it wants, which is where a newcomer's change is most likely to be welcome
and least likely to be permanent. Two refinements are worth the extra command:

- Restrict to bug-fix commits (`--grep='fix' -i`) and the ranking changes meaning
  entirely: high fix-churn plus high complexity is the code that costs the team most.
- Exclude generated and vendored paths, or lockfiles and compiled schemas will dominate
  the list and tell you nothing.

## Ageing: what has not moved and why that varies

```bash
git ls-files | while read -r f; do
  printf '%s %s\n' "$(git log -1 --format=%ad --date=short -- "$f")" "$f"
done | sort | head -40
```

Old files split cleanly into three kinds, and confusing them is expensive:

- **Stable infrastructure.** Well tested, central to the trace, untouched because it is
  correct. Change it with care and a test.
- **Abandoned.** No tests, no inbound callers from any entry point, last touched in a
  bulk rename. Candidate for the dead list in step 8.
- **Feared.** Touched rarely, always in small commits, often with apologetic messages.
  This is the code everyone routes around. Read the commit messages; they usually say why.

## Ownership and bus factor

```bash
git log --since='24 months ago' --format='%an' -- path/to/module | sort | uniq -c | sort -rn
```

Run it per module rather than repository-wide. A module whose commits come from one
person who no longer appears in the last six months of repository-wide history is
knowledge that has already left, and it is the highest-value thing to ask about while
someone who remembers is still available.

A module with many authors and no consistent one is the opposite problem: nobody will
review your change with any authority, so lean harder on tests and on the trace.

## Reverts and abandoned attempts

```bash
git log --oneline --grep='revert' -i --since='24 months ago'
git log --oneline -i -E --grep='roll ?back|back out|disable' --since='24 months ago'
```

Read the revert and then the commit it reverted. Between them they usually name a failure
mode the test suite does not cover — a performance cliff, a customer-specific behaviour, a
migration that could not be run in the deployment window. This is the cheapest way to
avoid spending a week rediscovering something the team already learnt the expensive way.

Branches that were never merged carry the same signal more weakly:

```bash
git branch -r --no-merged origin/main --sort=-committerdate | head -20
```

## Coupling: files that always change together

Files that appear in the same commit repeatedly are coupled whether or not the
architecture says so.

```bash
git log --since='12 months ago' --name-only --pretty=format:'---' \
  | awk '/^---$/{if(n>1&&n<8)for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)print f[i]"|"f[j];n=0;next}
         NF{f[++n]=$0}
         END{if(n>1&&n<8)for(i=1;i<=n;i++)for(j=i+1;j<=n;j++)print f[i]"|"f[j]}' \
  | sort | uniq -c | sort -rn | head -20
```

Two details are load-bearing. `--pretty=format:'---'` rather than `--format='---'`: a
`--format` whose value carries no `%` is read as the name of a pretty format and git exits
with `fatal: invalid --pretty format: ---`, so the whole pipeline yields nothing. And the
`END` block flushes the last commit in the stream, whose file list no separator follows;
without it that commit's pairs are silently dropped.

Bounding the commit size (here between two and seven files) keeps bulk renames and
formatting sweeps from swamping the result. A pair at the top of this list that lives in
two different modules is the coupling your change will trip over: modify one, and the
history says the other needed modifying too.

## When the history is not there

A squashed import, a migration from another version-control system, or a repository whose
commits are all "update" from a single bot account leaves nothing above to read. Say so
explicitly in the orientation note rather than reporting the empty result as a finding,
and substitute what evidence remains:

- The issue tracker and pull-request history, if they survived the migration when the
  commits did not.
- Deployment and release history, which often outlives the repository's own record.
- The previous system's archive, if it still exists read-only somewhere.
- Production telemetry: an endpoint with no traffic in 90 days is dead in a way no commit
  log can tell you, and this evidence is stronger than history even when history is intact.
