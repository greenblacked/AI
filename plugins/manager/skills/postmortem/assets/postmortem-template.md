# INC-[number]: [plain description of the failure]

**Date:** [incident date, with time zone]
**Authors:** [names]
**Status:** Draft | In review | Complete | Action items closed

## Summary

[Two or three sentences. What failed, for how long, what a user experienced.
No causes here — this is the paragraph someone reads in a hallway.]

## Impact

| Measure | Value | Source |
| --- | --- | --- |
| Time to detect | [TK: minutes] | [alert history / first report] |
| Time to mitigate | [TK: minutes] | |
| Time to full resolution | [TK: minutes] | |
| Users affected | [TK: count or %] | [how derived] |
| Requests failed or degraded | [TK: count] | [metric name] |
| Error-budget burn | [TK: % of period budget] | [SLO dashboard] |
| Revenue / contractual impact | [TK:] | [SLA terms] |
| Internal cost | [TK: engineer-hours] | |

[Narrative paragraph: what the degradation looked like from outside. Which
customer segments, which regions, which endpoints. Partial or total.]

## Root Causes

[The conditions that allowed the trigger to cause harm. Expect several, and
expect most to pre-date the incident by months. System-shaped statements only —
if a sentence has a person as its subject, rewrite it as a property of the
system. "Human error" is not a root cause; it is a signal that the analysis
stopped early.]

1.
2.
3.

## Trigger

[The single proximate event that started this occurrence. Deploy, config change,
traffic shift, upstream provider event, scheduled job, data volume threshold.]

## Resolution

[What actually restored service. Keep this separate from what was attempted —
the failed attempts belong in the Timeline and are where the diagnostic
learning lives.]

## Detection

[How the failure became known. Which alert fired, at what time, to which
rotation — or state plainly that no alert fired and a human found it.]

**Would automated monitoring have caught this?** [Yes, at [stage] / No, because
[gap]. This answer must produce at least one detection action item below.]

## Action Items

Every item needs all five columns. An item missing one is a wish, not an action
item. At least one must improve detection.

| # | Action | Class | Owner | Due | Priority | Tracker |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | detect | | | | |
| 2 | | prevent | | | | |
| 3 | | mitigate | | | | |
| 4 | | process | | | | |

## Lessons Learned

### What went well

[Controls that worked, tooling that helped, decisions that shortened the
outage. Name the reporting behaviour explicitly if someone raised their own
mistake — that is what keeps the next postmortem honest.]

### What went wrong

[Gaps in the system, in detection, in the runbook, in the escalation path.
Roles, not names.]

### Where we got lucky

[The section people skip. Every entry is a control that does not exist yet:
"the failure landed outside peak hours", "an engineer happened to be looking at
that dashboard", "the corrupted rows were within the retention window". Convert
each one into an action item or state why it is accepted risk.]

## Timeline

All times [time zone]. Sourced from [alert history, deploy log, chat transcript].

| Time | Event | Source |
| --- | --- | --- |
| | Change deployed | |
| | First user-visible impact | |
| | Detected — by [alert / human] | |
| | Responder paged | |
| | [Hypothesis pursued, and discarded because …] | |
| | Mitigation applied | |
| | Impact ends | |
| | Full resolution confirmed | |

## Supporting information

- Dashboards: [links]
- Queries used during diagnosis: [links]
- Alert definitions involved: [links]
- Chat transcript: [link]
- Related postmortems: [INC-… , if this failure mode has recurred]

---

**Before publishing:** an uninvolved reviewer has read this; no individual is
named outside Authors; every number is sourced or marked `[TK:]`; every action
item has an owner, a date and a live tracker link.
