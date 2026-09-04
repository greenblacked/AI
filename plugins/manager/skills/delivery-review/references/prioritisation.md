# Prioritisation and sequencing frameworks

## Contents

- [Classify the decision first](#classify-the-decision-first)
- [RICE](#rice)
- [ICE](#ice)
- [Cost of Delay and CD3](#cost-of-delay-and-cd3)
- [WSJF](#wsjf)
- [Choosing between them](#choosing-between-them)
- [Kill criteria](#kill-criteria)
- [How each framework is gamed](#how-each-framework-is-gamed)

## Classify the decision first

Before any scoring, sort the decision into one of three boxes. Most prioritisation
theatre comes from applying box three's machinery to box one's decisions.

**Reversible and cheap.** Do it. The cost of the meeting exceeds the cost of being
wrong, and being wrong is recoverable within a day. Framework use here is negative
value: it burns the team's tolerance for prioritisation processes on decisions that
did not need one.

**Irreversible or expensive.** No score helps. Write a decision record: the options
considered, the call, the reasoning, the assumptions it rests on, and what evidence
would reverse it. A number produced by multiplying three guesses does not make an
irreversible commitment safer; it makes it harder to argue with.

**Many similar items competing for one queue.** This is the only case the scoring
frameworks were built for. The items must be genuinely comparable and genuinely in
competition — the same team, the same period, the same kind of value.

## RICE

`RICE = (Reach × Impact × Confidence) / Effort`

**Reach** — how many entities are affected in a defined period. "1,400 active
accounts per month." This must be a real number over a real period taken from a
real dashboard, and it is where RICE dies in practice: teams substitute a
plausible-feeling figure, and every subsequent multiplication inherits that
fiction while looking like arithmetic. If Reach cannot be sourced, either go and
measure it or record it as `[TK: reach, from the admin-portal usage dashboard]`
and mark the score provisional.

**Impact** — per-entity effect, on a fixed scale so it cannot be inflated:

| Score | Meaning |
| --- | --- |
| 3 | Massive |
| 2 | High |
| 1 | Medium |
| 0.5 | Low |
| 0.25 | Minimal |

**Confidence** — 100% (strong evidence: data plus a validated mechanism), 80%
(some evidence, one significant assumption), 50% (informed opinion). Below 50%,
do not score. A sub-50% item is a question, and the correct next action is an
experiment, a spike or a customer conversation — not a position in a ranking.

**Effort** — person-months, whole team included: design, engineering, QA, rollout.
Rounding to 0.5 is fine; pretending to two decimal places is not.

Worked example:

```text
Item: self-serve API key rotation
Reach       = 320 accounts/quarter   (source: admin-portal usage dashboard)
Impact      = 1     (medium — removes a support ticket, not a purchase decision)
Confidence  = 80%   (ticket volume is measured; conversion effect is assumed)
Effort      = 2 person-months
RICE = (320 × 1 × 0.8) / 2 = 128
```

RICE fits a product backlog where reach is measurable and items are of similar
kind. It fits badly where value is concentrated in a few large customers, since
Reach flattens a strategic account into a small integer.

## ICE

`ICE = Impact × Confidence × Ease`, each scored 1-10.

Fast, coarse, and useful when the alternative is no prioritisation at all —
triaging fifty ideas down to eight worth thinking about properly. It is highly
gameable: one person shifting a single column by two points reorders the list, and
because the scales are unanchored, "8" means different things to different scorers.

Two mitigations, both required for the output to be worth anything: score blind
(everyone submits before anyone sees another's numbers), then discuss only the
items where scores diverge widely. Convergent scores need no meeting; the outliers
are the entire conversation, and usually reveal that two people were scoring
different interpretations of the item.

Do not use ICE for a final funding decision. It is a filter, not a verdict.

## Cost of Delay and CD3

**Cost of Delay** is the economic loss per unit time of not having the thing,
expressed in currency per week. It is the only framework here that answers "why
not just do them all" — because it prices the queue itself and makes the cost of
waiting visible next to the cost of building.

Build it from whichever components apply:

- Revenue not earned or lost while absent, per week.
- Cost incurred while absent: manual toil, support load, infrastructure overspend,
  contractual penalties.
- Time-limited value: a market window, a regulatory date, a contract renewal after
  which the value drops sharply or to zero.
- Risk reduction: expected loss avoided, if it can be honestly estimated.

Estimating in currency feels harder than scoring 1-10, and that difficulty is the
point — it forces the value conversation the scoring frameworks let people skip.
An order-of-magnitude estimate with stated assumptions beats a precise-looking
composite score built from nothing.

**CD3** = `Cost of Delay ÷ Duration`. Sequencing by CD3 is optimal for independent
items sharing a single queue: it does the shortest, most costly-to-delay work
first, which minimises total economic loss across the whole set. Two conditions
matter — the items must be independent (no ordering constraints between them) and
in the same queue (competing for the same capacity). Where dependencies exist,
sequence the dependency chain first, then apply CD3 within what remains.

```text
Item A: CoD £12k/week, duration 2 weeks → CD3 = 6.0   → do first
Item B: CoD £30k/week, duration 8 weeks → CD3 = 3.75
Item C: CoD £4k/week,  duration 1 week  → CD3 = 4.0   → do second
```

Note that B has the highest raw Cost of Delay and is sequenced last of the three.
That result is the reason CD3 exists, and the reason it is unpopular in rooms where
the largest item has the loudest sponsor.

## WSJF

`WSJF = Cost of Delay ÷ Job Size`, where

`Cost of Delay = user-business value + time criticality + risk reduction / opportunity enablement`

All four terms are scored relatively on modified Fibonacci (1, 2, 3, 5, 8, 13, 20)
rather than in absolute units. Anchor each column independently by finding the
smallest item in that column and setting it to 1, then scoring everything else
relative to that anchor. Without anchoring, scores drift upward across sessions
until every item is a 13 and the ranking is noise.

The three CoD components:

- **User-business value** — what the user or the business gains. Revenue, retention,
  cost avoided.
- **Time criticality** — how sharply the value decays with delay. A fixed regulatory
  date scores high; a nice-to-have with flat value over a year scores 1.
- **Risk reduction / opportunity enablement** — value that is not in the item itself
  but in what it de-risks or makes possible later. This column is where platform and
  enabling work earns its place against feature work, and dropping it is why
  platform work loses every prioritisation round in organisations that only score
  user value.

WSJF suits portfolio-level sequencing across teams where currency estimates are not
available. It is a relative-scoring approximation of CD3, and inherits CD3's
assumption of independent items in one queue.

## Choosing between them

| Situation | Use |
| --- | --- |
| Reversible, cheap, one team | Nothing. Do it |
| Irreversible or expensive | Decision record, not a score |
| Fifty raw ideas needing a first cut | ICE, scored blind |
| Product backlog, reach is measurable | RICE |
| The question is "why not all of them" | Cost of Delay |
| Independent items, one queue, durations known | CD3 |
| Cross-team portfolio, no currency estimates | WSJF |

Do not run two frameworks on the same set to "check" the result. They encode
different value models; agreement means little and disagreement resolves nothing.
Pick the one matching the decision and defend that choice.

## Kill criteria

Every prioritised item ships with two things agreed before work starts:

1. **The metric that says it worked** — named, measurable, with a baseline recorded
   now rather than reconstructed later.
2. **The threshold or date at which you stop and revert** — "if weekly active use
   of the new flow is under 15% eight weeks after GA, we remove it."

Most teams skip this, and the consequence is structural rather than occasional: an
item with no agreed failure condition can only be cancelled by someone
volunteering to be wrong in public, so nothing is ever cancelled. Capacity is then
permanently consumed by items whose case collapsed months ago, and the next
prioritisation round happens against a queue nobody is allowed to shorten.

Write the kill criterion into the item at the point of prioritisation, not at
kickoff. By kickoff the sponsor is committed.

## How each framework is gamed

| Framework | The gaming move | Counter |
| --- | --- | --- |
| RICE | Reach inflated with a plausible unsourced number | Require a named dashboard and period for every Reach |
| RICE | Effort deflated to raise the score | Effort estimated by the delivering team, not the requester |
| ICE | Scores tuned after seeing others' | Blind scoring, discuss outliers only |
| ICE | Ease scored by someone who will not build it | The team scores Ease |
| Cost of Delay | Speculative revenue attached to a pet item | State assumptions inline; sanity-check against actual revenue per user |
| WSJF | All columns drift to 13 over successive sessions | Re-anchor each column to 1 every session |
| WSJF | Job Size shrunk to lift the ratio | Size from historical throughput, not optimism |
| Any | The framework is run, then overridden without record | Log every override and its reason; a pattern of overrides means the wrong framework or the wrong decision box |
