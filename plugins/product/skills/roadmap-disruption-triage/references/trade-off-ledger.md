# Trade-off ledger, options and decision log

Contents: the ledger, the options table, the decision log entry, re-plan triggers, and the messages that follow a decision.

## The ledger

Write it before any answer is given. One row for the item coming in, one row per item going out.

| Item | Direction | Estimate (range) | Current date | New date | Promised to | Who tells them | By when |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bulk export for Acme | In | 3 to 5 weeks, two engineers | n/a | 25 Nov | Acme (via CEO) | Account owner | 31 Oct |
| Usage-based billing | Out | n/a | 7 Nov | 5 Dec | Finance, board deck | Head of product | 28 Oct |
| Audit log v2 | Out | n/a | 21 Nov | 9 Jan | Two enterprise renewals | Their account owners | 30 Oct |
| On-call rota | Hidden cost | n/a | n/a | n/a | Platform team | Engineering manager | 28 Oct |

Rules for filling it:

- The estimate comes from the team that builds it, as a range. Use the top of the range when computing slips.
- Every "out" row names a person or group that was promised the item. If nobody was promised it, say so; it makes the slip cheap and the decision easier.
- A hidden-cost row records anything absorbed instead of slipping: deferred maintenance, extra on-call, a test plan cut short. These are decisions too.
- Dates are calendar dates, not sprint numbers. A customer cannot plan around "sprint 23".

## The options table

| | Do it | Smaller version | Do not |
| --- | --- | --- | --- |
| What ships | Full request | The least that meets the confirmed outcome | Nothing new; current roadmap holds |
| What slips | From the ledger | Usually one item or none | Nothing |
| Revenue tested | Signed contingency amount, or "none signed" | Same | Amount at risk if the requester acts on the threat |
| Risk | Slipped commitments, team load | Outcome only partly met | Relationship, deal, executive confidence |
| Reversible? | Hard once started | Usually | Can be revisited at the re-plan trigger |
| Recommendation | | | |

Smaller versions that recur:

- A dated, written commitment for a later quarter, which is often what procurement actually needs.
- A manual or professional-services workaround for the one customer, with a cost cap.
- The read-only or single-case slice of the feature.
- Configuration or an integration that already exists, shown properly.
- A paid early-access arrangement that funds the work.

## Decision log entry

```markdown
### 2026-10-21 — Bulk export for Acme

- Demand: CEO, on behalf of Acme renewal; export of all workspace data by 15 Nov.
- Class: proof. Renewal order form held pending, signed contingency dated 12 Oct.
- Options: full build (slips billing and audit log, and at the top of the estimate lands 25 Nov, after Acme's 15 Nov need); export via support script plus
  dated commitment for self-serve in Q1 (slips nothing); decline.
- Chosen: smaller version. Decided by: VP product. Requester told: 22 Oct.
- Slipped: none. Hidden cost: support engineer, two days.
- Re-plan trigger: Acme does not sign by 15 Nov, or a second customer asks for
  self-serve export before Q1 planning.
- Review date: 16 Nov.
```

Keep the log in one place for the whole product organisation, so the quarterly count of disruptions per team is a query rather than an archaeology project.

## Re-plan triggers

A trigger is a condition with a date, chosen so that someone will notice it without remembering to look:

- The contingency is not signed by its stated date: revert to the original plan.
- The build overruns the top of its estimate range by a stated amount: stop and re-decide.
- The same requester asks for more scope: treat it as a new disruption with a new ledger.
- A second disruption hits the same team in the same quarter: run a full re-plan of the quarter rather than another patch.

## Messages after the decision

To the owner of a slipped item, before anything is public:

> (Send this version only if "Do it" is chosen; the smaller version decided above slips nothing.) Audit log v2 moves from 21 Nov to 9 Jan. We pulled forward bulk export for a renewal that is signed pending delivery. Your two renewal customers need to hear from you by 30 Oct; here is the wording I suggest, and I can join the calls.

To the requester:

> We will deliver export for Acme through support by 15 Nov and commit in writing to self-serve export in Q1. The full build now would have moved billing by four weeks (promised to finance and in the board deck) and the audit log by seven (promised to two enterprise renewals). If Acme needs more than this, that reopens the decision and I will bring the trade-off back to you.
