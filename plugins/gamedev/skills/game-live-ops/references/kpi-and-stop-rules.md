# Choosing KPIs and writing a stop rule

Read this at step 5, before the season starts and before any number from a previous season is treated as a target. Nothing here supplies a figure to aim for — a retention or monetisation number borrowed from another game measures that game's audience, platform, genre and marketing, not this one's, and treating it as a target is the single most common way a season's KPIs are set dishonestly without anyone intending to.

## Contents

- [Building a baseline instead of borrowing one](#building-a-baseline-instead-of-borrowing-one)
- [Candidate KPIs by category](#candidate-kpis-by-category)
- [Choosing which ones this season](#choosing-which-ones-this-season)
- [Writing a stop rule that actually binds](#writing-a-stop-rule-that-actually-binds)
- [Reading the result honestly](#reading-the-result-honestly)

## Building a baseline instead of borrowing one

Before choosing a target, measure what this game already does, on its own players, over at least one full prior cycle where one exists. A season's KPI target is "better than our own last measured baseline by a stated amount", never a published industry figure, a competitor's stated number, or a round figure that sounded reasonable in a meeting. If there is no prior season to measure, the first season's honest KPI work is establishing the baseline itself, not hitting a target nobody has evidence for yet.

Where the game has no telemetry to build a baseline from at all, say that plainly, the same way `game-balance` says it plainly when telemetry does not exist yet for a balance target — the deliverable is the event schema and the first season's measurement, not a number invented to fill the KPI's place.

## Candidate KPIs by category

| Category | What it is measuring | Where to source it from this game specifically |
| --- | --- | --- |
| Retention | Whether players who played once come back | Day-N return rate against your own game's cohorts, not an external benchmark — sourced from your own analytics pipeline |
| Engagement | Depth of play among players who stay | Session length or session count per active player, read as a distribution rather than an average, the same way `game-balance` reads time-to-kill as a distribution rather than a mean |
| Monetisation | Whether the game sustains itself, where it has a monetisation model at all | Revenue or conversion per active player over the season, compared to this game's own prior cycle |
| Content completion | Whether a season's content is actually being consumed | Completion or participation rate for the season's specific drops and events, which tells you whether the calendar in `references/season-calendar.md` is producing content anyone finishes |

Not every category applies to every game — a game with no purchases has no honest monetisation KPI, and forcing one in produces a number that measures nothing.

## Choosing which ones this season

Pick a small number, few enough that each one can actually be read and acted on rather than reported and ignored. A season with a dozen KPIs usually has zero that anyone is actually watching, because attention spreads across all of them and settles on none. Name, for each chosen KPI, what a change in it would actually cause the team to do — a KPI with no attached action is a vanity number, however well-produced the dashboard showing it is.

## Writing a stop rule that actually binds

A stop rule is the specific, observable threshold that ends or reverses the season, written before the season starts and before anyone knows what the KPIs will show. The same standard `game-greenlight`'s kill criteria apply here: observable, set in advance, and attached to a real consequence someone has actually agreed to.

A stop rule that only exists on paper and would never actually be enforced is decoration. Before writing one, confirm honestly that reversing or ending the season is genuinely on the table if the threshold is crossed — if it is not, the honest thing is to say the season runs regardless and put the KPI to a purely diagnostic use instead, rather than dressing an unenforceable number up as a stop rule.

Examples of a stop rule that binds:

- "If day-7 retention for players who joined during the season falls more than a stated amount below the pre-season baseline for two consecutive weekly readings, the season's next planned content drop is delayed and the cause investigated before it ships."
- "If a season event's participation rate is below a stated floor at its halfway point, the event ends on schedule and is not repeated next season without a stated change to why it underperformed."

## Reading the result honestly

Read the season's KPIs against the baseline and the stop rule that were written in advance, not against whatever story explains the number most comfortably after the fact. A season that missed its KPI is information the next season's calendar should use, the same way a balance patch's written prediction in `game-balance` step 5 is only useful once the result line is filled in, including when the honest result is "no measurable effect" or "target missed".
