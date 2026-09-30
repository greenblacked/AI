---
name: compensation-benchmarking
description: "Build or repair the pay structure a team is managed against — benchmark sources matched to stage and market, the level matched before the price, bands with a midpoint and a spread, compa-ratio and range placement, compression between new hires and tenured staff, a pay-equity check by cohort, offer construction, and a merit budget against a written matrix. Use this skill whenever someone is setting, checking or defending pay: refreshing salary bands, benchmarking a role, pricing an offer, reviewing for pay equity or compression, allocating a raise budget, or asking whether someone is paid fairly or a hire is affordable — including phrasings like \"we keep losing people on comp\" or \"what should we offer her\". Do not use it for the review or rating (growth-review), the interview loop and hire decision (hiring-loop), or the conversation where the number disappoints (difficult-conversation)."
allowed-tools: Read, Write, Grep, Glob
---

# Compensation Benchmarking

A pay decision is defensible when the level was fixed before the number, the band came from data that fits this team's stage and market, the placement is explained by a rule rather than a mood, and the equity check happened before the offer went out rather than after the complaint. The output is a band, a placement, and the reasoning a stranger could audit.

The job is hard because pay is the most opaque decision a manager makes and the one people read most into. The data is dirty — self-reported, stale, mixing base with total comp, sampled from companies that are not yours. Memory supplies an anchor: the last offer, the last person you hired, the number someone mentioned in a meeting. And the failure modes accumulate in silence. A generous hire quietly compresses the tenured people above them; a band never refreshed loses its top half to the market; a cohort that looks fine in aggregate hides a gap that only appears once you control for level. None of it announces itself, and all of it surfaces at once, as attrition, or in a meeting where you cannot explain the number. The order of operations below exists to make each of those visible while the fix is still cheap.

## Scope

Use for: building or refreshing salary bands; benchmarking a role, a level or a market; placing a person in a band; pricing an offer or a counter-offer; checking for pay equity, compression or inversion; allocating a merit or promotion budget; deciding whether a hire is affordable within the structure.

Do not use for: the written review, the rating or the promotion case itself (that is `growth-review`); designing the interview loop or making the hire/no-hire decision (that is `hiring-loop`); or holding the conversation in which the number lands as a disappointment or a surprise (that is `difficult-conversation`).

## The order of operations

Each step depends on the one before it, and taking them out of order is unrecoverable.

1. **Level before price.** You cannot benchmark a role you have not levelled. Priced first, the band defines the level, and the level is quietly redefined downwards to fit the budget.
2. **Data before band.** The band is a conclusion drawn from sources you can name. A band from a feeling cannot be defended and cannot be updated.
3. **Band before offer.** An offer outside the band is a decision to change the band. Make that decision deliberately or not at all.
4. **Equity check before the offer, not after.** The check that runs after the offer is a cleanup; the one that runs before it is a control.
5. **Budget against a written matrix before the cycle.** Allocated in the room, the budget rewards whoever argued last, which reproduces every bias in the room.

## Workflow

### 1. Fix the level, using the ladder in use

Benchmark the level, not the person and not the title. Two companies call the same work "senior"; two teams call different work the same. Use the organisation's ladder if it has one, and map the role onto it before touching a number. Where the ladder is informal, fix the level on the four axes `growth-review` uses — scope, autonomy, ambiguity and blast radius — and write down which one this role is.

If the role sits between two levels, decide which it is rather than averaging them. A band built on a half-level benchmarks against nothing.

### 2. Choose sources that fit this team

Market data answers "what would someone like this be paid elsewhere", and the answer is only as good as the sample's fit. Match on four things and say so in the output.

| Dimension | The question |
| --- | --- |
| Stage | Seed, scale-up or public — equity-heavy seed comp is not comparable to public-company cash |
| Geography | Local market for the office, or a location-adjusted remote band, not the HQ number applied everywhere |
| Role and level | The actual work and the ladder level, not the title |
| Mix | Base, bonus and equity modelled separately, then as total comp |

Free and paid sources both have a place — `references/band-construction.md` lists them and what each is trustworthy for. Use more than one. A single source is a point, not a range.

### 3. Clean the data before you trust it

Most benchmark data is self-reported and skewed, and the skew is not random.

- **Self-report bias.** People who submit data are often those who negotiated hardest or are looking to move; the number skews high. Treat crowd-sourced data as an upper reference, not a midpoint.
- **Age.** Comp data decays fast. Anything older than about a year is a historical figure; age it forward against a stated market movement or discard it.
- **Sample size.** A percentile from eight self-selected entries is noise. Say how many and where they came from, or do not use the percentile.
- **Mix.** Base salary and total compensation are different numbers. Comparing your base to a market total comp makes you look 30% behind when you are not.
- **Definition of the level.** A "senior engineer" in a flat ten-person company is not one in a 400-person one. Read the source's level definitions.

### 4. Build the band

A band has a midpoint, a spread and a set of rules for what sits inside it. `references/band-construction.md` has the formulas and a worked example; the shape is:

- **Midpoint** — the market rate for the level at the target percentile. Most organisations target the median (P50) for a solid performer and price above it deliberately, not by accident.
- **Spread** — typically 20–30% either side of the midpoint for an individual-contributor band, wider for senior and staff levels where the range of the work is wider. State the spread; do not let it grow one exception at a time.
- **Steps or none** — some structures have steps inside the band, some are continuous. Continuous is more flexible and needs more discipline about placement.
- **Geo differentials** — one band per market, or a location factor applied to a single band. Either is defensible; applying HQ pay everywhere is not.

Write the band with its effective date and the sources behind it. The next person to touch it should be able to see how it was built.

### 5. Place people, and explain the placement

Placement is a rule, not a negotiation. Use two measures together.

- **Compa-ratio** — salary divided by the band midpoint. Below 0.8 is a retention risk; above 1.2 in a band with a 1.2 ceiling is an exception that has to be named.
- **Range penetration** — how far up the band the person sits. Someone at 95% of a band has nowhere to grow and will leave unless the next level is open to them.

Record the reason for each outlier: a long tenure with flat growth, a hot skill, a correction of a past under-payment. An unexplained outlier is the one that gets noticed in an equity review.

### 6. Find compression and inversion before someone else does

Compression is a new hire paid close to or above the tenured people at the same level. It is the most common silent failure and the one that drives the most attrition.

Pull every person at the same level, sorted by pay, and look at it next to tenure and performance. Then ask three questions:

- Are there new hires within 10% of people two levels of tenure above them?
- Are there inversions — a less senior or less effective person paid more than a more senior one at the same level?
- Is any band's top now below what you must pay to hire at the midpoint?

Compression is not fixed by a one-off bonus; it is fixed by repricing the affected people, which is why it belongs in the budget conversation, not the offer conversation.

### 7. Run the pay-equity check by cohort

Aggregate numbers hide gaps. Compare like with like: same level, same role family, same location, and look at the ratio of each under-represented group to the reference group. A simple group mean is a starting signal; a regression controlling for level, tenure and performance is the defensible version. `references/offers-and-equity.md` has the method and the traps.

Two rules. Do not explain a gap away with "performance" unless performance is in the model, and do not publish a number you have not checked for small-sample noise — a cohort of six cannot support a conclusion.

### 8. Construct the offer or the counter-offer

An offer is a placement plus a story. Set it inside the band at the level you fixed, at a position you can justify, with the equity component modelled separately from cash. Where the candidate asks above the band, the answer is either a deliberate exception you record, or a no with the band as the reason.

A counter-offer is a retention decision, not a pay decision. Ask what changed to make the person worth more than the band said last month; if the honest answer is "nothing, we are afraid to lose them", say so and decide it as a retention case with its own budget line, not as a quiet band breach. `references/offers-and-equity.md` covers counter-offer policy and the equity grant mechanics.

### 9. Allocate the merit and promotion budget

Write the matrix before the room convenes. A common shape allocates the budget by performance band against range penetration — more for someone low in their band who performed well, less for someone already near the top, nothing for someone at the ceiling except a promotion case.

The matrix is what stops the cycle rewarding visibility and negotiation. Run it before the calibration meeting, bring the output to it, and require a written reason for every deviation. If the budget cannot fund the equity fixes and the merit increases both, that is a decision for the budget owner, and naming the trade-off is the manager's job.

### 10. Communicate the bands and the decision

Tell people the band they are in and the rule for moving through it. Bands that are secret cannot be trusted and cannot retain anyone, and the secrecy is usually what turns a fair decision into a suspected unfair one.

When the number is a disappointment, the pay decision is done and the conversation is a different skill — hand it to `difficult-conversation` with the band and the reason as the fixed facts.

## Output format

```markdown
## Band — [level], [role family], [location]
[Midpoint, spread, effective date, and the sources behind it with their ages.]

## Placement — [name]
[Compa-ratio, range penetration, and the one-line reason. Flag any exception.]

## Compression and inversion
[Same-level people sorted by pay next to tenure and performance. Named risks.]

## Pay equity
[Cohorts compared, the method, the gap and its confidence. Small samples marked as
inconclusive rather than reported.]

## Offer or counter-offer
[The number, its position in the band, the equity component, and the exception record
if any.]

## Budget
[The matrix, the allocation, the equity fixes funded, and the trade-offs left open.]
```

## Anti-patterns

**Pricing before levelling.** The band becomes the definition of the level, and a strong person is paid a strong salary at the wrong level. Level first, always.

**One source, treated as truth.** A single crowd-sourced percentile is a data point with a sampling bias. Two or three sources that disagree tell you the range; one source tells you a number you will defend badly.

**Base compared to total comp.** Makes an adequately paid team look far behind and a behind team look fine. Model the mix explicitly.

**The quiet band breach.** One exception to close a hire becomes the new floor for the next one, and the band erodes without a decision. Every exception is recorded and repriced.

**Compression left for the exit interview.** The tenured person who discovers the new hire's number finds it in the wrong order and leaves. Find it in the budget cycle.

**Equity checked in aggregate.** A company-level gap of 2% can hide a 15% gap at one level. Compare cohorts, and say when a cohort is too small to conclude from.

**Counter-offers as a comp strategy.** Paying to match an external offer teaches the team that the path to a raise is an outside offer. If it was a retention decision, fund it as one and fix the underlying reason.

## Reference files

- `references/band-construction.md` — read when building or refreshing a band: the data sources and what each is good for, the cleaning rules, the midpoint-and-spread formulas, geo differentials, compa-ratio and range penetration, and a fully worked band with its arithmetic.
- `references/offers-and-equity.md` — read when pricing an offer, setting counter-offer policy, or running the equity check: offer construction, equity grant mechanics, the counter-offer decision, the cohort equity method and its traps, and the merit matrix with a worked allocation.
