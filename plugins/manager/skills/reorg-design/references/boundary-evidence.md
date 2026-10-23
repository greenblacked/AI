# Boundary evidence

Use the data you already have. A rough number found in an afternoon is enough to justify, or to rule out, a reorganisation. Record how each number was counted so the 90-day review repeats it the same way.

## Three measures

| Measure | Source | How to count |
| --- | --- | --- |
| Cross-team handoffs per project | Project plans, epics, launch documents | For each project of the last six to twelve months, list the teams that owned at least one deliverable. A handoff is a deliverable that cannot start until another team finishes one. Report the average handoffs per project and the count of projects with two or more teams |
| Ownership overlap | Repository history | For each team's main repositories, count commits or merged changes in the last two quarters by authors from outside the team. Report outside-author share per repository. A high share in one place says the boundary cuts through a single codebase |
| Queue wait | Ticket tracker | For requests that move from one team's queue to another's, take the time from creation to first action by the receiving team. Report the median and the 90th percentile, not the mean |

## Repository history

This works in a clone of the repository. Replace the paths and dates.

```bash
git log --since="6 months ago" --no-merges --format='%ae' -- services/billing | sort | uniq -c | sort -rn
```

Map each author address to a team with a small lookup table, then compute the outside share. A squash merge reduces several contributors to one author, and co-authors appear only in trailers, so the share understates shared work; check a sample of ten changes by hand before trusting the share.

## The project test

Take the three or four most recent significant projects, the ones people remember as painful or slow as well as one that went well.

| Project | Teams touched today | Candidate A | Candidate B | Baseline plus interface fix |
| --- | --- | --- | --- | --- |
| Example: checkout redesign | 3 | 1 | 2 | 3 |

Count the teams that would have had to own a deliverable under each structure. Add a column for any new handoff the structure creates, such as a shared library now owned by neither team.

Read the result as a comparison, not a statistic. Four projects cannot prove anything; they show whether the structure addresses the pain people describe, and they expose a candidate that only moves the boundary.

## Warnings about the data

- Handoff counts depend on what counts as a deliverable; fix the definition first and apply it to every project.
- A single large project can dominate a small sample. Say so when it does.
- Wait time that comes from a shortage of people is not a boundary problem. If the receiving team is understaffed, moving the boundary does not help; that is a headcount question for `headcount-case`.
- Do not use individual-level commit counts in any communication. Use team-level shares only.
