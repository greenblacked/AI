# Success plan template

Read this when writing a POC plan: the template the customer sponsor signs, examples of
vague criteria rewritten as measurable ones, the mid-point checkpoint questions and the
exit review agenda.

## Contents

- The success plan
- Rewriting vague criteria
- Mid-point checkpoint questions
- Exit review agenda

## The success plan

```markdown
# Proof of concept: [customer] and [vendor]

## The problem
[In the buyer's words. Who has it, what it costs today.]

## Decision this POC supports
[What will be decided, by whom, by when.]

## Success criteria
| # | Criterion | Baseline today | Target | Data and method | Measured by |
| --- | --- | --- | --- | --- | --- |
| 1 | | | | | |

## In scope / out of scope
[What will be tested. What will not, even if asked for during the POC.]

## Environment and data
[Who provides the environment. Which data, its classification, the approvals needed,
and how it is deleted or returned at the end and by when.]

## Roles
| Role | Customer | Vendor |
| --- | --- | --- |
| Sponsor (decides) | | |
| Technical lead | | |
| Day-to-day contact | | |

## Timeline
| Milestone | Date |
| --- | --- |
| Kickoff | |
| Mid-point checkpoint | |
| Exit review and decision | |

## Change control
New criteria or scope only in writing, agreed by the customer sponsor, with a revised decision
date where the change adds work.

## If the criteria are met
[The agreed next step: for example, proceed to an order form for the stated scope by a
stated date, or a paid pilot of a stated size.]

## Sign-off
Customer sponsor: [name, date]   Vendor sponsor: [name, date]
```

## Rewriting vague criteria

| Vague | Measurable |
| --- | --- |
| Evaluate performance | 95th percentile query time under 2 seconds on the customer's largest dataset, measured by their data lead with the agreed test queries |
| Easy to use | Three of their analysts each build the weekly report unaided within one hour, observed by their team lead |
| Integrates with our systems | Orders created in their system appear in ours within five minutes, for one week of real orders, checked by their operations lead |
| Secure | Their security team completes their review and records no open high-severity findings by the checkpoint |
| Saves time | Monthly reconciliation takes under two hours, against a current two days, on last month's data |

Each rewritten criterion names a number, the data, and the customer-side person who
measures it. If the buyer cannot name a baseline, measure it before the plan is signed, or put a
dated baseline-measurement task, with its owner, in the signed plan ahead of setup.

## Mid-point checkpoint questions

Ask with the customer sponsor present:

1. For each criterion: on track, at risk, or failing? What is the evidence?
2. Is the decision in the plan still the decision the business needs to make?
3. Is the sponsor still the person who decides, and are they still engaged?
4. Have new requirements appeared? Are they in the change log, or arriving informally?
5. Is there anything that would make the result irrelevant even if every criterion passes?

End or reset in writing when a criterion cannot be met in the window, the sponsor has
disengaged, or the decision has changed.

## Exit review agenda

1. The problem and the decision, restated from the plan.
2. Each criterion: target, result, evidence, met or not.
3. Anything learned outside the criteria, labelled as such.
4. The sponsor's decision.
5. The next step and its date, as agreed in the plan.
6. Close-down: access removed, data deleted or returned, confirmation recorded.
