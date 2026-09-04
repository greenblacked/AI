# One set of facts, three audiences

## Contents

- The rule
- The shared fact base
- Version 1: the team
- Version 2: peer leaders
- Version 3: executives
- Translation rules
- What changes and what may not

## The rule

Re-cut the same facts for what each reader can act on. Do not produce a different set of
facts per audience. Versions diverge quietly — a date softened for executives, a risk
sharpened for the team — and then two of them are in the same meeting and the divergence
is what people remember. Recovery from that is slow.

Write the fact base once, then cut three views from it.

## The shared fact base

An example week, all figures with sources the author holds:

- 6 of 14 teams migrated to the new CI pool ([migration board])
- Median queue time 27 min, was 3 min in March ([CI dashboard])
- Two teams merging without green builds ([INFRA-4471])
- Vendor contract for extra runners is monthly, 30-day exit
- Platform team owes an answer on shared-runner quota; asked 1 Aug, no reply
- Target: all 14 teams migrated by 30 Sep; current forecast 21 Oct
- Ask: budget approval for [TK: n] runners at [TK: monthly cost]

## Version 1: the team

Detail and mechanism. They need to know what is blocked, who owns what, and what changed
in the plan.

> AMBER · FYI · CI migration · 2026-08-04
>
> **Bottom line:** 6 of 14 teams migrated; queue time is the bottleneck and the 30 Sep
> date is at risk — forecast is 21 Oct unless we add runners.
>
> **Ask:** None from you. I am asking for runner budget this week.
>
> **Since last:** Teams 5 and 6 cut over ([board]). Queue time still 27 min median
> ([dashboard]). INFRA-4471 confirms two teams are merging without green builds — if that
> is you, come and talk to me, it is a system problem not a discipline problem.
>
> **Next:** Team 7 cutover — [owner] — 8 Aug. Runner budget decision — me — 8 Aug.
> Chase platform team on quota — [owner] — 5 Aug.
>
> **Risks:** Platform quota answer outstanding since 1 Aug — chasing — [owner]. Queue
> time blocks the remaining eight cutovers — runner budget — me.

## Version 2: peer leaders

Interfaces and dependencies. What you need from them, what you owe them, what moved on a
shared timeline.

> AMBER · DECISION NEEDED (platform) · CI migration · 2026-08-04
>
> **Bottom line:** CI migration is at 6 of 14 teams; the 30 Sep date slips to 21 Oct
> unless queue capacity increases, and one input is yours.
>
> **Ask:** Platform — a yes/no on the shared-runner quota request from 1 Aug. Needed by
> 8 Aug or the forecast moves again.
>
> **What this changes for you:** Teams 7-14 cut over between Aug and Oct; each cutover
> needs a two-hour window from your on-call. Dates on the [board].
>
> **Since last:** 2 teams migrated. Queue time 27 min median, was 3 min in March
> ([dashboard]).
>
> **Risks:** Two teams merging without green builds ([INFRA-4471]) — this affects your
> deploy confidence as much as ours.

## Version 3: executives

Outcome, risk, ask. Three lines, then optional detail. They are reading for: are we on
track, what are the major risks, and what do I need to decide.

> AMBER · DECISION NEEDED · CI migration · 2026-08-04
>
> **Bottom line:** Migration is 6 of 14 teams done and will land 21 Oct rather than
> 30 Sep unless we add CI capacity; I need [TK: monthly cost] approved by 8 Aug.
>
> **Ask:** Approve [TK: n] additional runners at [TK: monthly cost], monthly contract.
> Reversible — 30-day exit, so if the queue problem resolves another way we drop it.
>
> **Why it matters:** Build queue time is 27 min, up from 3 min in March ([dashboard]);
> two teams have started merging without green builds ([INFRA-4471]), which is how
> production incidents start.
>
> **Risks:** Platform quota decision outstanding since 1 Aug — if it lands positively the
> runner spend may be unnecessary; I will know by 8 Aug.

## Translation rules

| Element | Team | Peers | Executives |
| --- | --- | --- | --- |
| Mechanism and detail | Full | What touches them | Omit |
| Named owners | Yes | For shared work | Rarely |
| Ticket links | Yes | Yes | One or two, load-bearing only |
| The ask | Often none | What you need from them | First two lines |
| Cost and reversibility | If relevant | If relevant | Always, when asking |
| Length | One page | Half a page | Three lines plus detail |

## What changes and what may not

Changes: level of detail, which links are included, what the ask is and who it points at,
and the ordering.

Does not change: dates, numbers, RAG status, and the existence of a risk. If the project
is amber for the team it is amber for the executive. Softening the status for the senior
audience is the specific failure that makes a reporting line worthless, and it is usually
discovered at the worst possible moment.

Also does not change across audiences: nothing about a named individual's performance
appears in any of the three. If a person is the reason a date moved, the update carries
the date and the system-level reason; the rest belongs in a one-to-one.
