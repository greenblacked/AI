---
name: commitment-planning
description: "Decide how much Savings Plan, reserved instance or committed-use discount to buy, and when, so a discount never becomes a floor paid for idle capacity: rightsize first, measure the trailing 90-day hourly floor of eligible usage rather than the average, convert it to a commitment at the discounted rate net of existing coverage, prefer flexible compute instruments, ladder small purchases monthly so expiries stagger, price the exit of every term against the roadmap, and review utilisation and coverage weekly. Use when someone asks how much to commit, whether to buy a one- or three-year plan, why commitment utilisation dropped, or says \"finance wants us to buy RIs before year end\". Not for explaining why the bill grew (cost-review), sizing for a launch (capacity-planning), choosing a vendor (vendor-evaluation) or tracing egress and NAT bytes (data-transfer-forensics)."
allowed-tools: Read, Grep, Glob
---

# Commitment Planning

A commitment plan is done when every purchase in it is sized from the measured hourly
floor of usage that survives the roadmap, is small enough that being wrong costs one
tranche rather than the year, has its exit cost written next to it, and has a named owner
who reads utilisation and coverage every week.

The usual failure is a single large purchase at the end of a quarter, sized from a
recommendation tool's figure or from average spend, made before the rightsizing work that
was already on the backlog. The discount shows up immediately; the cost shows up months
later, when the fleet shrinks after rightsizing, moves to spot, or migrates to a service the
instrument does not cover, and the organisation keeps paying the hourly commitment for
capacity nobody runs. A commitment is a promise to pay for a shape of workload whether or
not it exists; size it to the part of the workload you would bet on.

This is an engineering procedure for sizing cloud commitments, not financial or accounting
advice; the purchase decision and how it is accounted for belong to finance.

## Scope

Use for: deciding commitment size, instrument, term and payment option on AWS (Savings
Plans, reserved instances and reserved nodes), Google Cloud (committed use discounts) and
Azure (reservations and savings plans for compute); building a purchase ladder; reviewing
utilisation and coverage of commitments already held; planning renewals and expiries;
pricing the exit cost of a term against a migration.

Do not use for: explaining why a bill grew or finding waste across the estate, which is
`cost-review` (it decides whether commitments are the right lever; this skill sizes them);
whether a system survives a launch or peak, which is `capacity-planning`; choosing between
vendors or negotiating a private pricing agreement as a purchase decision, which is
`vendor-evaluation`; finding which workload generates egress, cross-AZ or NAT charges,
which is `data-transfer-forensics`; model token spend, which is `llm-cost`.

Only Read, Grep and Glob are pre-approved. The plan document asks before it is written, and so does every cloud command, because a billing export or a tag can carry text a person chose and a command it suggests is declined.

## Gates

1. **Rightsizing and known moves come first.** Commit only to usage that remains after
   the rightsizing, generation changes, spot moves and decommissions already planned for
   the term. Committing first locks the waste in for one or three years.
2. **A person makes the purchase.** Commitments cannot be cancelled on most instruments,
   so the purchase is made by a named human from a reviewed plan, never by an automated
   job or a pre-approved command.
3. **Every purchase carries its exit cost.** The cost of the commitment under the
   scenario where the workload changes shape is written beside the saving, or the
   purchase is not ready.

## Workflow

### 1. Inventory what is already committed

List every active commitment: instrument, scope (account, organisation, region, family),
hourly amount or quantity, term end, payment option and the last four weeks' utilisation.
On AWS, reserved instances are applied before Savings Plans, and both are shared across
linked accounts under consolidated billing unless sharing is turned off; know which
applies before reading coverage. Put every term end on a calendar; an expiry is when
coverage silently drops and the bill rises with no change in usage.

### 2. Clear the decks

From `cost-review` findings or the backlog, list what will change the eligible usage
within the term: rightsizing, instance-generation moves, spot adoption, scheduled shutdown
of non-production, decommissions, migrations to containers, serverless or another region.
Either wait until they land, or subtract their expected effect from the floor in step 3.
Ask the owners of the three largest workloads what happens to them in months 6 to 18; a
planned replatform is the commonest reason a three-year term goes bad.

### 3. Measure the hourly floor over 90 days

Commitments are consumed hour by hour and unused hours are lost, so measure hourly, not
daily or monthly. Over the trailing 90 days, compute the on-demand-equivalent cost (or
vCPU and memory, for resource-based commitments) of eligible usage per hour, per
instrument scope. Then read four numbers: the minimum, the 5th percentile, the median and
the mean.

The floor is the minimum after removing hours you can explain as one-off (an outage, a
migration cut-over). Commit to the floor, not the mean: everything above the floor is
usage that some hours do not have, and a commitment sized to the mean is partly unused in
every one of those hours. Ninety days covers a quarter's cycle; recommendation tools
typically look back at most 60 days and optimise for headline savings rather than for
risk, so use them as a cross-check, not as the size.

Hand a billing export too large to read here to the `cost-analyst` subagent. Read
`references/floor-queries.md` for the hourly query against the AWS Cost and Usage Report
and the Google Cloud billing export, and the cross-checks.

### 4. Convert the floor into a commitment

Subtract the part of the floor already covered by commitments that remain in force through
the new term. Then convert what is left into the unit the instrument is bought in. AWS
Savings Plans are bought in dollars per hour at Savings Plans rates, not at on-demand
rates, so the commitment is roughly the on-demand-equivalent floor multiplied by one minus
the effective discount for your instance mix. Buying the on-demand figure as the
commitment overcommits by the size of the discount. Resource-based commitments are bought
in vCPUs and memory per machine series and region, from the same hourly floor in those
units.

State the target coverage the plan reaches: covered eligible usage over total eligible
usage, in a typical hour. A floor-sized plan lands well below 100% by design.

### 5. Choose the instrument and term

Default to the most flexible instrument that covers the usage: AWS Compute Savings Plans
over EC2 Instance Savings Plans or standard reserved instances; spend-based (flexible)
over resource-based committed use discounts on Google Cloud where both apply; savings plans
for compute over reservations on Azure. Flexibility is what survives the re-architecture
step 2 did not foresee. Take the less flexible, deeper discount only for the portion of a
workload that is genuinely fixed in family and region for the whole term, with the extra
saving stated.

Databases, caches, search and warehouses usually need their own reserved instances or
nodes, because compute plans do not cover them; size those per engine, family and region
from their own floor.

Buy three-year terms only for the slice of the floor that survives every roadmap scenario
in step 7; one-year terms for the rest. Compare payment options against the organisation's
cost of capital: upfront payment deepens the discount and also makes the whole term a sunk
cost on exit. Read `references/instruments-and-exit.md` for the per-cloud instrument table
and what each allows on exit.

### 6. Ladder the purchases

Reach the target in monthly tranches rather than one purchase. Each month, re-measure the
floor, compare it with commitments in force, and buy a tranche covering part of the
remaining gap. Laddering staggers the expiries so no single month carries a cliff, turns
every month into a decision point that sees the latest roadmap, and caps the cost of a
wrong estimate at one tranche. The first tranche may be larger when the floor has been
stable for several quarters; later tranches stay small.

### 7. Price the exit

For each tranche, compute what it costs under each roadmap scenario: the planned
migration, a 30% demand drop, a move to spot or serverless, a region change. The exit cost
is the remaining commitment over the term minus the eligible usage still running under
that scenario, valued at the commitment rate, less anything the instrument lets you
recover (an exchange, a marketplace sale, a capped refund). Write the worst plausible
scenario's figure beside the expected saving. If the worst case exceeds the saving over
the term, shorten the term, switch to the flexible instrument, or shrink the tranche.

### 8. Review weekly and before each expiry

Each week, read two numbers per instrument:

| Metric | Meaning | Action when it moves |
| --- | --- | --- |
| Utilisation | Share of the commitment actually used | Below the high nineties: usage dropped under the commitment. Find which workload moved; stop further tranches until the floor is re-measured |
| Coverage | Share of eligible usage covered by commitments | Falling with flat usage: an expiry or a shift to uncovered services. Rising past the plan: usage fell, check utilisation |

Set utilisation and coverage alerts in the provider's budgeting tool (AWS Budgets supports
both for Savings Plans and reservations). Sixty days before each term ends, re-measure the
floor and decide afresh; a renewal is a new purchase, not a continuation.

## What to hand back

```markdown
## Current position
[Commitments held, utilisation and coverage over four weeks, term ends.]

## Floor
[Hourly eligible usage over 90 days per scope: minimum, p5, median, mean;
excluded hours and why; adjustments for planned changes.]

## Plan
| Month | Instrument | Scope | Term | Payment | Amount | Coverage after | Annual saving | Worst-case exit cost |

## Not committed
[Usage left on demand or spot, and why: above the floor, due to move, not eligible.]

## Review
[Owner, weekly metrics and alert thresholds, expiry calendar.]
```

## Anti-patterns

**Sizing from the average.** Every hour below the average leaves part of the commitment
unused, and those hours are the nights and weekends that make up much of the week.

**Buying the tool's recommendation in one purchase.** It looks back sixty days at most,
cannot see the roadmap, and puts every expiry on the same date.

**Committing before rightsizing.** The rightsizing saving is then paid twice: once to the
smaller instances and once to the commitment covering the instances that no longer exist.

**Buying the on-demand figure as a Savings Plan commitment.** The commitment is priced at
the discounted rate, so the plan overshoots the floor by roughly the discount.

**Three-year terms on a workload with a migration on the roadmap.** The discount turns into
a payment for the old platform while the new one is also being paid for.

**No owner for utilisation.** A commitment slipping from full use to three-quarters costs a
quarter of its value every hour until someone looks.

## Reference files

- `references/floor-queries.md` — read at steps 1, 3, 4 and 8: hourly floor queries over
  the AWS Cost and Usage Report and the Google Cloud billing export, deriving the effective
  discount, and the Cost Explorer commands for utilisation, coverage and recommendations.
- `references/instruments-and-exit.md` — read at steps 5 to 7: the per-cloud instrument
  table with flexibility and exit options, the exit cost worksheet, and a worked ladder.
