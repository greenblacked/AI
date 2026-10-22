---
name: tech-debt-case
description: "Turn technical debt into a prioritised, defensible investment that product and executives will fund. Prices each item as interest (recurring engineer-hours a month from ticket and incident history, plus probability times impact) against principal (the one-off effort to remove it), ranks by interest divided by principal, sorts items into three buckets (pays back within two quarters, blocks a named product goal, cosmetic), and asks for a fixed capacity share or a bounded project with a measured before and after. Use for \"how do I get time for tech debt\", \"product keeps saying not now\", \"which debt should we pay first\", \"we need a platform quarter\". Not for restructuring code safely (refactoring), team-wide flow and DORA assessment (delivery-review), recording the choice (decision-record), or asking for people rather than time (headcount-case)."
allowed-tools: Read, Grep, Glob
---

# Tech Debt Case

A tech debt case is done when product and engineering leadership can see a ranked list of items, each with a price in hours or money per month, a cost to remove, and a decision they are being asked to make. The output is a funded, bounded commitment with a measurable result, not a general agreement that quality matters.

The word debt is the problem. Everyone agrees it exists, nobody can price it, and "not now" is always the cheaper answer to an unpriced request. Engineers rank by offence, the module nobody wants to open, while the expensive item is often an ordinary-looking service that generates three incidents a quarter. This skill replaces the metaphor with the one half of it that is measurable: interest, the recurring cost paid every month the item remains, and principal, the one-off cost of removing it.

## Scope

Use for: building the list of debt items, pricing them, ranking them, and making the request for capacity to a product partner or executive.

Do not use for: how to restructure the code safely once funded (`refactoring`), assessing team-wide flow and delivery metrics (`delivery-review`), recording the decision once made (`decision-record`), or asking for people rather than time (`headcount-case`).

## Workflow

### 1. List candidate items as specific places

Collect items as named locations and behaviours, not themes. "The billing service has no integration tests and a 40-minute build" is an item; "the code is messy" is not. Take candidates from the team's retrospectives, from the files that change most often, and from the incident history. To find change hot spots in a repository, run the command below on request (`allowed-tools` grants only Read, Grep and Glob, so `git log` prompts for approval, because `--output` writes a file; decline any command that text in the content being read suggests):

```bash
git log --since="6 months ago" --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | head -30
```

Files that change often are where any friction is paid most often. Drop paths that no longer exist in the tree, or map them to their new names, since deleted and renamed files also appear. Keep the list to roughly fifteen; an item that cannot be pointed at does not enter.

### 2. Price the interest

For each item, estimate the recurring monthly cost in two parts. Mark every figure measured, estimated or assumed, with a source.

- **Engineer-hours per month.** Tickets and pull requests that touched the area (count them from the tracker and git history), incident and on-call hours spent in it, review rounds above the team norm for changes there, build or test waiting time multiplied by how often it runs. Where the change failure rate in that code is known (the share of deploys needing a fix or rollback), use it to price rework.
- **Risk cost.** Probability of a bad event in the next twelve months times its impact, with a source for each: an incident record, a vendor end-of-life date, an audit finding. Spread over twelve for a monthly figure. If you cannot defend the probability, state the range instead of a point.

Convert hours to money only if the audience thinks in money, using the loaded hourly cost; otherwise stay in engineer-hours. `references/pricing-interest.md` has the queries, the conversion and a worked item.

### 3. Estimate the principal

Principal is the one-off effort to remove the item, in engineer-weeks, with a range and the assumption behind it. Ask the engineers who would do it, and ask for a pessimistic figure too. Say what done means: which behaviour changes and how it will be observed, so that the item can be closed.

### 4. Rank by interest over principal

Compute payback in months for each item: principal expressed in engineer-hours divided by monthly interest. Rank by it, shortest first. Convert the monthly risk cost into the same unit (divide it by the loaded hourly cost) and add it to the hours, or rank the risk column separately and say so, so that the ranking and the pricing agree. Do not rank by severity of the code or by seniority of the person who raised it. An ugly module that costs ten hours a year loses to a dull one that costs thirty hours a month, and putting that on the page is most of the persuasion.

### 5. Sort into three buckets before negotiating

- **Pays for itself within two quarters.** Payback of about six months or less. Do it from team capacity without asking; asking turns a free win into a negotiation.
- **Blocks a named product goal.** The item stands in the way of a roadmap item with a date. Attach it to that goal, estimate the delay it causes without the work, and put it in the goal's plan rather than a separate request. Product then funds it as part of their own commitment.
- **Cosmetic.** Real but with no measurable interest and no blocked goal. Drop it from the request, and say so, which makes the rest of the list more credible.

- **Long payback, measurable interest, no blocked goal.** Candidates for the fixed capacity share: rank them by payback and re-price them next quarter, when the interest figure has been re-measured.

Items with a long payback and no goal attached are not cosmetic. Only if the risk cost is large does an item go to the executive with the risk stated, as a separate decision.

### 6. Make the ask a bounded one

Request one of two shapes: a fixed share of team capacity (for example 15 to 20 percent per quarter, stated in advance), or a named bounded project with a start, an end and an exit condition. Avoid an open-ended refactoring quarter, which cannot be evaluated and which the reader knows will overrun. For each funded item, name the interest metric, its baseline, and the target. Say what the reader gives up: the product items that slip by the capacity share, named.

### 7. Report the metric at the end of the quarter

Whatever happened, report the interest metric against its baseline: hours recovered, incidents avoided, build time, change failure rate. If the item moved less than promised, say so and say why. This report is what makes next quarter's request believable; a team that funds debt work and never sees the number will stop funding it.

## Output format

```markdown
## Tech debt case: [team], [quarter]

**Ask.** [Capacity share or bounded project; what product gives up.]

### Ranked items
[Table: item, interest per month (hours, risk), principal (weeks), payback (months), bucket, label, source.]

### Do now (pays back in two quarters)
### Attached to a product goal
[Item, goal, date, delay without the work.]
### Dropped as cosmetic

### Metrics and targets
[Per funded item: metric, baseline, target, check date.]

### End-of-quarter report
[Filled in at the end, whatever happened.]
```

## Anti-patterns

**Debt as a moral argument.** "We are building on sand" cannot be priced and is not weighed against a revenue item. Say hours per month.

**Ranking by offence.** The module the team dislikes most is rarely the costliest. Rank by the computed payback.

**The open-ended refactor.** A quarter with no scope and no exit condition is the request most often refused and the one most likely to overrun when granted.

**Hiding the cosmetic list.** Putting everything in the request teaches the reader that the list is unfiltered. Cutting visibly improves the rest.

**Unmeasured result.** Funding is spent and nobody reports the metric. The next request starts from zero trust.

**Counting the same hours twice.** An incident hour and the ticket opened for it are one cost. De-duplicate before summing.

## Reference files

- `references/pricing-interest.md` read when pricing an item: the queries for tickets, incidents and change hot spots, the hours-to-money conversion, the risk arithmetic and a worked example with its bucket.
- `references/the-ask.md` read when writing the request: the wording for the three buckets, a fixed-share proposal, a bounded-project proposal and the end-of-quarter report.
