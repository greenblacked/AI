---
name: win-loss-review
description: "Find out why deals are won, lost or stall, from the buyers rather than the CRM: separate no decision, often the biggest bucket, from lost to a competitor; sample every closed deal in the period rather than the ones reps pick; have someone outside the sales team interview buyers within 30 days of close; code answers against the buyer's own decision criteria; report a competitor-specific pattern only once five or more deals show it. Use when someone asks why we lose deals, why so many end in no decision, what tipped a won deal, or says \"the CRM says price every time\" or \"we keep losing to the same rival\". Not for reading a competitor's public moves (competitor-signal-watch), customers who cancel after buying (churn-analysis), an angry customer threatening to leave (escalated-account-recovery), or validating a problem before building (problem-validation)."
allowed-tools: Read, Glob, Grep
---

# Win-Loss Review

A win-loss review is done when it can say, with counts behind each statement, why buyers
chose us, chose someone else, or chose nothing, and when each finding has gone to the team
that can change it: product, pricing, marketing or sales enablement.

The job is hard because the data that is easiest to get is the least true. The CRM's loss
reason is picked by the rep, after the loss, from a dropdown, and "price" is the answer that
protects everyone. Buyers soften their reasons when the person asking is the one who lost
the deal. Reviews look only at losses, so nobody learns what actually wins. And the largest
bucket, deals that ended with the buyer doing nothing, is usually filed as a loss to
whichever competitor was mentioned, which sends the fix to the wrong team. The steps below
put the buyer's own account at the centre and keep each kind of outcome apart.

## Scope

Use for: a periodic review of closed deals; a sudden rise in losses to one competitor or in
stalled deals; checking whether the CRM's loss reasons are believable; designing the
interview programme and its guide; turning interview notes into findings with owners.

Do not use for: what a competitor is doing in public (`competitor-signal-watch`); customers
who bought and then cancel or shrink (`churn-analysis`); rescuing a furious key account
(`escalated-account-recovery`); interviewing prospects about a problem before there is a
product to sell them (`problem-validation`); lead quality before an opportunity exists
(`lead-quality-loop`); the buyer side of a deal, choosing what to buy (`vendor-evaluation`). It is not a review of an individual rep's
performance: a buyer interview used to judge a rep stops being candid with the next buyer.

## Workflow

### 1. Define the outcomes before pulling a single deal

Write the outcome buckets and their rules first, so deals are classified the same way by
everyone:

| Outcome | Rule |
| --- | --- |
| Won | Signed |
| Lost to a competitor | Buyer chose a named alternative product |
| Lost to build | Buyer chose to build it themselves |
| No decision | Buyer kept the status quo, deferred indefinitely, or the project lost its budget or sponsor |
| Disqualified by us | We walked away; reviewed separately, since the lesson is about qualification |

No decision is the bucket that matters most and is most often hidden. A deal where the
buyer evaluated a competitor and then bought nothing is no decision, not a loss to that
competitor; the fix for it is about urgency, consensus and value, not features.

### 2. Sample the period, not the stories

Take every deal that closed in the period above a stated size threshold, won, lost and
stalled alike. A stalled deal counts once it has passed an agreed age in its stage with no
buyer activity. Letting reps nominate deals for interview selects the losses they are
comfortable discussing. Including wins matters for the same reason: without them, every
loss reason looks like a cause, when some of those reasons were equally present in the
deals we won.

Record the CRM's stated reason for each deal before any interview. Comparing it with what
the buyer says later is one of the most useful findings the review produces.

### 3. Interview buyers, from outside the sales team, within 30 days

The interviewer is someone the buyer has no reason to be polite to: a product manager, a
researcher, or an outside firm, never the account executive or their manager. Interview
within 30 days of the close, while the buyer still remembers the sequence of events rather
than a tidy summary of it.

Ask for the timeline, not the verdict: what triggered the search, who was involved, which
options they looked at, what they had to believe to choose, what nearly changed their mind,
and what happened in the last two weeks before the decision. Ask for permission before
recording and say how notes will be used. `references/interview-guide.md` has the request
email, the guide and the questions that get past "it came down to price".

Aim for interviews on a meaningful share of each bucket. Buyers who chose nothing are the
hardest to reach and the most worth reaching.

### 4. Code against the buyer's decision criteria

Map what each buyer said onto the criteria they actually used to decide, such as time to
value, a capability, integration with a named system, total cost, risk and vendor
viability, trust in the team, or internal consensus. Use the buyer's criteria rather than
our feature list: a buyer who says "they understood our workflow" is reporting a criterion,
and it will not appear on any feature matrix.

For each deal, record the deciding criterion, the criteria where we were stronger or
weaker, and whether the CRM reason matched. Code with two people on the first ten
interviews and compare; where they disagree, the criterion definitions need tightening.

### 5. Report patterns at the threshold they can bear

Report each finding with the count of deals behind it. Overall patterns can be reported at
any size if the count is shown. A competitor-specific pattern ("we lose to X on
onboarding") is reported only when five or more deals against that competitor show it;
below that, list the deals as cases and say the sample is too small. A pattern drawn from
two deals sends a product team to build the wrong thing with confidence.

Separate what we can change from what we cannot. Losing deals that should have been
disqualified earlier is a qualification finding for sales, not a product gap.

### 6. Send each finding to an owner, and repeat

Each finding goes to one owner with a date: product for a capability gap, pricing for a
packaging or price-metric problem, marketing for a positioning gap, sales enablement for a
process or qualification issue. Track the CRM-versus-buyer mismatch rate as its own number;
if it is high, fix the loss-reason field before trusting it in any dashboard.

Run the review on a fixed cadence, usually quarterly, so a change in pattern can be seen
rather than remembered.

## Output format

```markdown
## Win-loss review: [period]

### Outcomes
[Counts and value by bucket: won, lost to competitor (by competitor), lost to build,
no decision, disqualified. Interview coverage per bucket.]

### Why we win
[Deciding criteria in won deals, with counts and one quote each.]

### Why we lose, and why deals stall
[Findings per bucket with counts. No decision reported separately.]

### Competitor patterns
[Only where five or more deals support it; otherwise listed as cases.]

### What the CRM said versus what buyers said
[Mismatch rate and the commonest substitution.]

### Actions
| Finding | Owner | Change | Date |
```

## Anti-patterns

**Trusting the dropdown.** The CRM loss reason is a rep's best guess, written after the
loss. Use it as a hypothesis to test against the buyer's account.

**The account executive runs the interview.** The buyer is polite to the person they turned
down and the answer becomes "you were close on price".

**Losses only.** Without wins, every reason a buyer gives looks causal. Some of those same
weaknesses were present in the deals we won.

**No decision filed as a competitive loss.** The fix goes to product as a feature gap when
the real problem was that the buyer had no urgent reason to change.

**A battlecard rewritten from two deals.** A pattern below five deals per competitor is an
anecdote, however vivid the quote.

## Reference files

- `references/interview-guide.md` — read before contacting buyers: the request email, how
  to explain recording and use of notes, the timeline-based question set for won, lost and
  no-decision deals, the follow-up questions that get past price, and the coding sheet.
