---
name: postmortem
description: "Write or review a blameless incident postmortem in the Google SRE shape — numbered title, quantified impact, root causes separated from the trigger, how it was detected, and action items that each carry an owner, due date, priority and tracker link. Use this skill whenever an incident needs writing up, reviewing before publication, or judging as postmortem-worthy: after user-visible downtime or degradation, any data loss, an on-call engineer intervening with a rollback or traffic reroute, a long resolution time, or an incident a human spotted before the alerting did. Casual phrasings count — \"we need a writeup for yesterday's outage\", \"can you draft the RCA\", \"is this worth a postmortem\", \"read this before I publish it\". Do not use it for triaging an incident that is still burning, for routine change records, or for a performance conversation about the engineer involved."
---

# Postmortem

A good postmortem lets someone who was asleep during the incident understand what broke, why the system allowed it, and what specifically changes as a result — with every number in it traceable to a source.

Postmortems fail in two directions. They become prosecutions, at which point engineers learn to under-report and the organisation loses the raw material that prevents recurrence. Or they become ceremony: smooth narrative prose, a root cause of "human error", a list of action items nobody funds, filed and never read. This skill exists to prevent both. Structure is enforced, evidence is demanded from the human, and where a number is not supplied it is written as a visible gap rather than an estimate that later gets quoted as fact.

## Scope

Use for: writing a postmortem after an incident, reviewing a draft before publication, deciding whether an incident meets the bar, and preparing the action-item set for a sprint planning conversation.

Do not use for: live triage during an ongoing incident — that is a different job, and for Kubernetes-shaped incidents the `k8s-triage` skill covers it. Also not for individual performance discussions; a postmortem that feeds one has already failed.

## Workflow

### 1. Confirm the incident meets the bar

Write a postmortem when any one of these holds. They are thresholds, not a scoring system — one is enough.

| Trigger | Why it qualifies |
| --- | --- |
| User-visible downtime or degradation past the agreed threshold | The SLO was spent on a failure, not on change |
| Data loss of any kind, any volume | Irreversible; the only class where recovery is not possible |
| On-call had to intervene — rollback, traffic reroute, manual failover | The system could not recover itself |
| Resolution time past the agreed threshold | Slow recovery is a defect independent of the cause |
| Monitoring failure — a human noticed before an alert fired | The most-skipped trigger and often the most valuable |

Ask the user for the organisation's actual thresholds if they are not stated. If none exist, say so plainly and use a stated assumption rather than inventing a policy.

The last row deserves its own emphasis. An incident found by a customer, a support ticket, or an engineer glancing at a dashboard is a detection failure regardless of how small the impact was. Those postmortems are the ones that improve alerting, so they are worth writing even when the outage was trivial.

### 2. Interrogate before drafting

Gather facts before writing a single sentence of narrative. Ask in one batch, and ask for sources rather than recollections:

- Timeline entries with timestamps and time zone — from chat logs, alert history, deploy records, not from memory.
- Impact figures and where each comes from: duration, users affected, requests failed, error-budget burn, revenue.
- What actually changed before the incident: deploys, config edits, feature flags, traffic shifts, upstream provider events.
- Who detected it and by what means; which alert fired, or that none did.
- What was tried that did not work — near-misses and dead ends carry most of the learning.

Where a figure is unavailable, write `[TK: metric]` in the document — for example `[TK: requests failed, from the load-balancer 5xx counter]`. Never estimate, interpolate, or round a number into existence. A `[TK:]` is an open question someone can close; a fabricated figure is a false statement that will be cited in a planning meeting six months from now.

### 3. Separate root cause, trigger and detection

These three are routinely collapsed into one paragraph, and separating them is most of the analytical value:

- **Trigger** — the event that started this occurrence. "Deploy of v2.14 at 09:41."
- **Root causes** — the conditions that allowed the trigger to cause harm. Usually several, usually pre-existing for months. "Connection pool sized for a single replica; no limit enforced at the client; staging runs one replica so the ceiling was never reached in test."
- **Detection** — how the failure became known, and how it should have become known. Always answer explicitly: would automated monitoring have caught this, and at what stage?

Push the causal chain until it reaches something the team can change in the system. Stop when the next "why" leaves the organisation's control.

### 4. Keep it blameless, structurally

Blameless means the analysis targets causes rather than people. This is not politeness; it is the mechanism that keeps reporting honest. Where reporting is punished, incidents get quietly resolved and never surface, and the same failure recurs with no data behind it. Praise, in the document itself, anyone who reported their own mistake — that behaviour is what makes the next postmortem possible.

**"Human error" is never a root cause.** It is the point at which the analysis stopped early. Treat it as a prompt: what made the wrong action easy and the right action hard? Reframe every people-shaped statement into a system-shaped one:

| Do not write | Write |
| --- | --- |
| X deployed without testing | The deploy path allowed an untested change to reach production |
| X ran the wrong command | The runbook's command was one character from a destructive variant, with no confirmation prompt |
| X missed the alert | The alert routed to a channel with 400 daily messages and no paging escalation |
| X forgot to update the config | Config drift between environments was undetected because nothing compared them |

Replace individual names with roles throughout — "the on-call engineer", "the release approver", "the platform team". Names belong in the author line, and in the thanks.

### 5. Write the document

Reproduce the Google SRE section set in this order. Do not drop sections; an empty section with a `[TK:]` is more useful than a silent omission.

1. **Title** — includes the incident number and a plain description of the failure.
2. **Date** — incident date, not writing date.
3. **Authors** — real names here.
4. **Status** — Draft / In review / Complete / Action items closed.
5. **Summary** — two or three sentences: what failed, for how long, what the user experienced.
6. **Impact** — quantified. See step 6.
7. **Root Causes** — the conditions, plural, from step 3.
8. **Trigger** — the proximate event.
9. **Resolution** — what actually restored service, distinguished from what was attempted.
10. **Detection** — how it was found and whether automation found it.
11. **Action Items** — see step 7.
12. **Lessons Learned** — three subsections: What went well, What went wrong, Where we got lucky. The third is the one people skip and the one that predicts the next incident; luck is an unfunded control.
13. **Timeline** — timestamped with time zone, from logs.
14. **Supporting information** — dashboards, queries, alert links, chat transcript, related postmortems.

`assets/postmortem-template.md` is the fill-in version of this structure. Copy it and work into it rather than composing free prose; the section order is what keeps the analysis from collapsing into narrative.

### 6. Quantify impact

Fill each line or mark it `[TK:]` with the source that would close it:

- Duration: time to detect, time to mitigate, time to full resolution — three distinct numbers.
- Users affected: count or percentage, and how that was derived.
- Requests failed or degraded, with the metric they came from.
- Error-budget burn: percentage of the period's budget consumed.
- Revenue or contractual impact, and whether an SLA credit is triggered.
- Internal cost: engineer-hours spent, work displaced.

### 7. Make action items real

Every action item carries four attributes, and an item missing any of them is not an action item — it is a wish:

**Owner** (a named person, not a team) · **Due date** (a date, not "next quarter") · **Priority** (using the org's existing scale) · **Tracker link** (the ticket must exist before publication).

**At least one action item must be a detection improvement.** Answer the question directly in the document: would we have caught this automatically, and what alert, SLO or synthetic check now exists so that we would?

Classify each item as prevent, detect, mitigate, or process. A set that is entirely "prevent" usually means detection was not examined.

Unfunded action items are the single most common way postmortems fail. The manager's job after publication is twofold: get the items real capacity in the next sprint — named in the sprint, not appended to a backlog — and protect the blameless frame during the review meeting, interrupting the first "why didn't you just" before it sets the tone.

### 8. Review and publish

Have someone uninvolved in the incident read it before publication. They are checking for three things: whether a reader without context can follow it, whether any name-shaped blame survived the rewrite, and whether every number has a source.

Then publish widely — company-wide where the culture allows. A postmortem read only by the team that had the incident teaches only that team. Circulating them is how the twentieth engineer avoids the failure the first one found.

## Output format

Produce the completed document following the section order in step 5, then append this handoff for the human:

```markdown
## Open questions
[Every [TK:] in the document, with who can close it and where the data lives.]

## Action items summary
[Table: item | owner | due | priority | tracker | class (prevent/detect/mitigate/process)]

## Review checklist
- [ ] No individual named outside Authors and thanks
- [ ] No root cause reducible to "human error"
- [ ] Root cause, trigger and detection are distinct sections
- [ ] Every number sourced or marked [TK:]
- [ ] At least one detection-improvement action item
- [ ] Every action item has owner, due date, priority, tracker link
- [ ] "Where we got lucky" is populated
- [ ] Uninvolved reviewer identified
```

## Anti-patterns

**Root cause: human error.** Ends the analysis exactly where it should begin, and leaves the system unchanged so the next person makes the same easy mistake.

**A number with no source.** "Roughly 5,000 users affected" becomes a fact in a board deck by the third retelling. `[TK:]` costs an awkward gap now and saves a wrong decision later.

**Action items with no owner or date.** They are recorded, never scheduled, and reappear verbatim in the next postmortem for the same failure.

**No detection action item.** The incident recurs at the same size because nothing changed about how quickly it is noticed.

**Skipping "Where we got lucky".** Every piece of luck is a control that does not exist yet. Naming it converts it into a funded action item.

**Narrative smoothing.** Prose that flows well but omits the twenty minutes spent on the wrong hypothesis hides the diagnostic gap, which is often the largest available improvement.

**Publishing to the team only.** The learning stays with the people who already had it.

## Reference files

- `assets/postmortem-template.md` — the fill-in template. Copy it at the start of step 5 rather than composing the sections from scratch.
