# Findings memo

One page. Written for the team to read, so keep individual names out and attribute themes, not people. Personnel concerns never go in it; they go in the private note below.

## Template

```markdown
# What I found in the first 30 days: [team], [date]

How I got here: 1:1s with [n] people, [n] quarters of postmortems and plans, conversations
with [upstream and downstream teams].

## Inherited commitments (to honour or renegotiate explicitly)
| Promise | Made to | Due or ongoing | My intention |
| --- | --- | --- | --- |
| Support for the reporting export through Q4 | Finance | Ongoing | Honour; revisit scope with Finance in November |

## Inherited risks (each gets an owner and a decision date)
| Risk | Evidence | Owner | Decide by |
| --- | --- | --- | --- |
| Only one person can deploy the legacy scheduler | Three of four deploys last quarter were by the same person | [name] | [date] |

## Inherited preferences (mine to keep or change; none changed yet)
- Planning happens in a single Monday session.
- Reviews need two approvals.
- [others]

## What I do not yet know
- [Open questions, who might answer them]

## What I will change, and what I will leave alone
Changes (at most two): see below.
Leaving alone for now: [items, and why]
```

## What goes where

- **Commitment**: someone outside the team is relying on it. Test: would they be surprised or harmed if it stopped? If yes, it is a commitment. Dropping one without telling them damages the team's reputation in a way you will inherit.
- **Risk**: a bad outcome is plausible and the team has no protection. Single points of failure, unowned systems, expiring certificates, licences or contracts, and unreviewed access. Performance problems are not shared risks; they go in the private note.
- **Preference**: a way of working that could reasonably be different. If the team could do it another way with no one outside noticing, it is a preference.

When an item fits two kinds, record it under the heavier one and say why.

## Choosing the two changes

Choose by these tests, in order:

1. Does the evidence come from more than one source (the 1:1s and the record, for example)?
2. Is it within your authority, or do you know who decides?
3. Can the team see a result in about thirty days?
4. Does it reduce a named risk or fulfil a request that several people made?

For each change record:

```markdown
Change:
Owner:
Date it starts, date it should be visible:
What will be different (observable by the team):
First visible win by day 60:
How we will know it worked:
What it costs, and what we will stop to make room:
```

Keep the changes small enough that the day-60 win is real. Report progress to the team at day 60 and day 90, including a change that is not working.

## Private note (you and your manager only)

Never shared with the team. Holds performance concerns, with the evidence and the next step, handled through `performance-improvement-plan` or `difficult-conversation` as the case requires. Keep it out of the shared memo, its drafts and any file the team can read.
