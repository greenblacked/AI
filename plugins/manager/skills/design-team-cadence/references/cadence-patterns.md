# Cadence Patterns

Use these patterns as starting points, then remove anything that does not own a recurring
decision or relationship.

## Contents

- [Selection rules](#selection-rules)
- [Single engineering team](#single-engineering-team)
- [Platform team with internal customers](#platform-team-with-internal-customers)
- [Group of teams](#group-of-teams)
- [Manager of managers](#manager-of-managers)
- [Remote and multi-time-zone teams](#remote-and-multi-time-zone-teams)
- [Review and deletion rules](#review-and-deletion-rules)

## Selection rules

Choose frequency from decision latency, not convention:

| Need | Default path |
| --- | --- |
| Information with no discussion | asynchronous update |
| Reversible local decision | owner decides and records |
| Cross-team dependency | short decision forum with pre-read |
| Operational trend | weekly or fortnightly operational review |
| Individual context and growth | one-to-one |
| Strategy or investment | monthly or quarterly review |
| Urgent user impact | incident process, not recurring cadence |

No agenda by the pre-read deadline means cancellation unless the forum protects a
relationship, as a one-to-one does.

## Single engineering team

Minimum viable rhythm:

| Forum | Frequency | Primary output |
| --- | --- | --- |
| One-to-one | weekly or fortnightly | mutual commitments and surfaced context |
| Planning/review | aligned to delivery unit | accepted scope and trade-offs |
| Retrospective | fortnightly or monthly | one owned system change |
| Operational review | weekly when service-owning | risk decision and follow-up owner |

Keep a daily coordination event only when the work genuinely benefits from same-day
replanning. Otherwise use an asynchronous check-in plus an exception huddle.

## Platform team with internal customers

Add interfaces rather than inviting customers to internal meetings:

- office hours for low-cost questions and adoption friction;
- monthly customer council for roadmap trade-offs, with representative teams;
- service review for SLOs, adoption, support load and deprecation;
- published decision and deprecation logs;
- named escalation route with response expectation.

Do not turn the customer council into a vote. The platform owner remains accountable for
strategy and must explain trade-offs against evidence.

## Group of teams

Use a weekly staff forum for cross-team decisions, staffing constraints, dependency risk,
and escalations. Team status is a pre-read. Rotate deep dives only when they ask for a
decision or expose a reusable lesson.

Add a monthly portfolio review for investment and cancellation. Keep architecture review
separate when it needs different expertise and evidence; do not make every manager an
architecture approver.

## Manager of managers

The operating system needs two loops:

1. business and system outcomes across teams;
2. management quality, organizational health and leadership development.

Use skip-levels as sampling, not a shadow reporting line. Ask about system patterns,
decision clarity, workload and what leadership is not seeing. Return themes to the manager
without attributing private remarks unless safety requires escalation.

Review spans, succession risk, management load, hiring, regretted attrition, and team
interfaces monthly or quarterly. Do not wait for annual planning to discover that one
manager owns three incompatible jobs.

## Remote and multi-time-zone teams

Default to written context and rotate inconvenience. Define:

- which decisions may complete asynchronously;
- response windows by urgency;
- one canonical decision record;
- overlap hours reserved for discussion, not broadcast;
- recording and summary expectations;
- who represents an absent region and how objections reopen a decision.

A recording is not asynchronous inclusion if nobody can influence the decision afterwards.

## Review and deletion rules

Review the cadence after four weeks, then quarterly. For each forum ask:

- What decision or relationship would fail if this disappeared?
- How many people-hours did it cost?
- What percentage ended with its promised output?
- Which agenda items belonged elsewhere?
- Which attendees never contributed to the decision?
- Can frequency, duration, or attendance shrink?

Delete first, merge second, redesign third, and add only when a required decision remains
homeless.
