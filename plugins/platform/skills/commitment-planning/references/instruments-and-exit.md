# Instruments and exit

Read this when choosing the instrument and term, pricing the exit, and laying out the
ladder. Provider terms change; confirm exchange, resale and refund rules on the provider's
current pages at purchase time rather than from this table.

## Contents

- Instruments by cloud
- Exit cost worksheet
- A worked ladder
- Questions before each tranche

## Instruments by cloud

| Cloud | Instrument | Bought in | Flexibility | Exit route |
| --- | --- | --- | --- | --- |
| AWS | Compute Savings Plan | Dollars per hour at plan rates, 1 or 3 years | Any EC2 family, size, region, OS, tenancy; Fargate; Lambda duration | None once past the short return window AWS documents for recent small purchases; confirm it, and do not plan around it |
| AWS | EC2 Instance Savings Plan | Dollars per hour, 1 or 3 years | One instance family in one region; any size, OS and tenancy within it | None |
| AWS | Standard reserved instance (EC2) | Instances, 1 or 3 years | Size-flexible within a family for some platforms when regional | Can be listed on the Reserved Instance Marketplace, subject to its conditions |
| AWS | Convertible reserved instance (EC2) | Instances, 1 or 3 years | Exchangeable for another of equal or greater value | Exchange only |
| AWS | Reserved instances or nodes for RDS, ElastiCache, OpenSearch, Redshift | Per engine, family, region | Size-flexible within a family for some engines | None in general |
| Google Cloud | Resource-based committed use discount | vCPUs and memory per machine series and region, 1 or 3 years | Fixed to the series and region | None: cannot be cancelled |
| Google Cloud | Spend-based (flexible) committed use discount | Hourly spend, 1 or 3 years | Across eligible machine series and regions for the covered services | None: cannot be cancelled |
| Azure | Savings plan for compute | Hourly spend, 1 or 3 years | Across eligible compute services and regions | None: cannot be cancelled or exchanged |
| Azure | Reservation | Per resource type, size group and region, 1 or 3 years | Instance size flexibility within a group for VMs | Exchange and capped refund, under rules that have changed more than once; check the current policy |

Spot and preemptible capacity is not covered by any of these. Workloads moving to spot
leave the floor; subtract them in step 2 of the skill.

## Exit cost worksheet

For each tranche, one row per roadmap scenario:

```text
tranche:            Compute SP, 1 year, no upfront, $40/h, starts 2026-11-01
remaining hours:    hours from the scenario date to the term end
committed:          40 * remaining_hours
still used:         eligible usage under the scenario, at plan rates, per hour * remaining_hours
recoverable:        exchange, resale or refund value, if the instrument allows any
exit cost:          committed - still used - recoverable
```

Scenarios to cover, at minimum:

- the largest planned migration on the roadmap lands on its stated date;
- eligible demand falls by 30% from month 6;
- a major workload moves to spot, serverless or a managed service the instrument does not
  cover;
- the organisation moves the main region.

Write the worst plausible row's exit cost beside the tranche's expected saving over its
term. A tranche whose worst-case exit cost exceeds its expected saving is shortened,
moved to a more flexible instrument, or shrunk until it does not.

Break-even, for the case where usage falls below the commitment for the whole term: a
commitment at discount `d` against on-demand loses money once utilisation over the term
falls below `1 - d`. At a 30% discount that is 70% utilisation.

## A worked ladder

Floor after adjustments: $300/h on-demand equivalent. Effective plan rate ratio: 0.70.
Existing Compute Savings Plans: $105/h, ending in month 4.

```text
Target commitment at plan rates     = 300 * 0.70 = $210/h
Gap today                           = 210 - 105  = $105/h

Month 1   buy $45/h, 1 year      (larger first tranche: floor stable for three quarters)
Month 2   re-measure; buy $20/h, 1 year
Month 3   re-measure; buy $20/h, 1 year
Month 4   existing $105/h expires; re-measure; buy back what the floor still supports,
          split: $50/h now, the rest across months 5 and 6
Month 5+  re-measure monthly; buy to close the gap in small tranches, or buy nothing
```

After a year the commitments expire one tranche a month instead of all at once, and the
three-year slice, if any, is added only once the roadmap scenarios show which part of the
floor survives all of them.

## Questions before each tranche

1. Has the floor been re-measured this month, with excluded hours listed?
2. Are rightsizing, spot and decommission changes due this term subtracted?
3. Which roadmap scenario gives the worst exit cost, and is it below the expected saving?
4. Does the scope (organisation-wide or one account) match how the saving will be shown
   back to teams?
5. Is the weekly utilisation and coverage review owned by a named person?
