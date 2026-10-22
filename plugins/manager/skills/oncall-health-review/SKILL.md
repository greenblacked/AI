---
name: oncall-health-review
description: "Assess whether an on-call rotation is sustainable for the people on it and fix the structure — 90 days of paging data per person (out-of-hours pages, sleep-interrupting pages 23:00-07:00, pages per shift, time to resolve), flags for any night with more than two interrupting incidents, rotation size against the SRE book's eight-engineer single-site guidance, primary/secondary split, handover, protected recovery time, the fairness ledger and written compensation policy, and load sorted into fix the alert, fix the system, or staff for it. Use for \"on-call is burning people out\", \"is our rota fair\", \"should we pay for on-call\", \"nobody wants to be primary\", \"team of four, can we do 24/7\". Not for which signals page (alert-design), targets (slo-design), meetings (design-team-cadence), organisation-wide attrition (retention-review), or the per-rule export ledger (page-history-reader)."
allowed-tools: Read, Grep, Glob
---

# On-call Health Review

A rotation review is done well when it names, from data, who is carrying how much, says whether the rotation's shape can ever be sustainable, and ends in a ranked change list with a threshold that triggers action next quarter.

The usual failure is treating burnout as an attitude problem or an alerting problem only. A team of four with a primary and a secondary is on call two weeks in four, and no amount of alert tuning changes that arithmetic. The opposite failure is a structure argument made without numbers, which leaves the people on the worst shifts unconvinced that anything is being done.

## Scope

This is procedure, not legal advice; check rest-period and pay rules with the employer's legal or HR function.

Use for: judging whether a rotation is sustainable; checking fairness and compensation; deciding whether a small team can offer round-the-clock cover; fixing a rota people avoid.

Do not use for: deciding which signals should page (`alert-design`); setting reliability targets (`slo-design`); the meeting system (`design-team-cadence`); organisation-wide attrition (`retention-review`).

## Workflow

### 1. Pull 90 days of paging data

Export every page for the rotation for the last 90 days from the paging tool, with these fields at minimum: the person paged, the time created, acknowledged and resolved, the service or rule, and whether a human acted or it auto-resolved. Ninety days gives enough shifts per person to see a pattern and short enough to reflect the current system.

If the export is thousands of rows, delegate the per-rule ledger (step 6) to `page-history-reader`, which returns metrics per rule only and treats responder names as sensitive. Compute the per-person table another way: the reference script, or the paging tool's own per-user report. For a small export, `references/page-data.md` has a script that computes the per-person table from a CSV.

Convert times to each engineer's local time before bucketing. A page at 02:00 UTC is a daytime page for someone in Singapore.

### 2. Compute the per-person table

For each engineer, over the 90 days:

- Shifts taken, and shift days on call.
- Out-of-hours pages (outside their local working hours, and weekends).
- Sleep-interrupting pages, those created between 23:00 and 07:00 local time.
- Pages per shift.
- Median and 90th percentile time to resolve.
- Auto-resolved alerts that nobody touched, as their own column.
- Nights with more than two interrupting incidents (see step 3).

Count a page that was acknowledged and acted on, not an auto-resolved alert, as the interruption measure. Both go in the table, kept apart.

### 3. Apply the flags

Flag, and name the person and the shift:

- Any single night (or 12-hour period) with more than two interrupting incidents. Report the count of such nights per person and the worst one.
- Any engineer paged out of hours on more than a quarter of their on-call days.

Two incidents in a night or 12-hour shift is the working limit (the SRE book's own figure is two per 12-hour shift) because an incident takes more than an hour of real work once diagnosis, fix and follow-up are counted, and a second interruption within a night leaves almost no sleep. Never average over a week-long shift or the team: one night with nine pages is about 1.3 a night across a week and disappears. Report counts and the worst case.

### 4. Check the structure before the behaviour

Ask these in order. A bad answer here explains the data and no change in alerts will fix it.

| Question | What to look for |
| --- | --- |
| Rotation size | Google's SRE book sizes a single-site rotation at a minimum of eight engineers, or six per site across two sites. The eight-engineer minimum assumes a primary and a secondary, so a team of four with a secondary is on call two weeks in four |
| Primary and secondary | Is there a secondary, and does the secondary get paged in practice, or does the primary carry everything |
| Handover | Is there a written note from the outgoing person (open incidents, flaky alerts, anything in flight) and a short live exchange |
| Recovery | Does a shift with sleep-interrupting pages earn protected time owed back (a late start, a day off) that people take rather than forfeit |
| Follow-the-sun | Is a second site possible, so nobody takes night pages routinely |

If the rotation is below the size guidance, say so plainly and put "grow the rotation, narrow the hours covered, or lower the service's cover promise" on the change list. A team of four can offer business-hours cover with an out-of-hours best-effort policy; it cannot honestly offer 24/7 cover with fairness.

### 5. Check the fairness ledger

Read who covered holidays, public holidays, weekends and swaps over the last year, and whether the load fell on the same few people (often the ones who say yes). Keep a simple ledger: person, holiday shifts, swap debts owed and owing. Make the rule for holidays explicit, for example rotating the holiday shifts so nobody has the same one twice before everyone has had it once.

Read the compensation or time-off policy as written: what is paid or credited for on-call, for an out-of-hours page, for a night interruption. Do not rely on what people believe the policy is. Legal obligations on rest periods and on-call pay vary by country and sometimes by contract; check the local rules with HR and say so in the report rather than assuming. Where nothing is written, that is a finding.

### 6. Sort the load into three buckets

For every recurring source of pages (use the per-rule ledger from `page-history-reader` for this), choose one:

1. **Fix the alert.** It pages on something that does not need a human at night: tune it, route it to a ticket, or delete it. Hand the rule to `alert-design`.
2. **Fix the system.** The alert is right and the system keeps failing the same way: it needs engineering work, with an owner and a date.
3. **Accept and staff for it.** The load is real and legitimate. Then rotation size, pay and recovery are the response.

Do not leave anything in a fourth bucket called "keep an eye on it".

### 7. Output a ranked change list and a threshold

Rank changes by pages removed or hours of sleep protected per unit of effort. Put the structural items (rotation size, secondary, recovery, written policy) next to the alert and system items, since they are often the cheapest.

Set one threshold that triggers action next quarter without another debate, for example: any engineer with more than N sleep-interrupting pages in a quarter, or any night above two interrupting incidents, opens a review within a week. Put the next review date on the calendar and name its owner.

## Hand back

The per-person table, the flagged shifts, the structure findings against the size guidance, the fairness and policy findings, the three-bucket sort, the ranked change list with owners and dates, the threshold, and the next review date.

## Anti-patterns

**Averaging across the team.** The mean looks acceptable while two people absorb the worst nights. Report the worst shifts and the per-person table.

**Fixing alerts while the rota stays at four.** Pages fall and the structure still gives people one week in four with no break.

**Counting auto-resolved alerts as load.** They distort the table in both directions. Keep human actions and auto-resolves separate.

**Assuming the policy.** The compensation or time-off policy is described from memory; the actual text says something else, or nothing.

**A volunteer rota.** Fairness depends on a few people saying yes. The ledger shows it, and it ends when they leave.

## Reference files

- `references/page-data.md` — read at step 1 and step 2: the export fields to request, a script that computes the per-person table from a CSV, and the checks for time zones and auto-resolves.
- `references/rota-structure.md` — read at step 4 and step 5: rotation sizing arithmetic, primary and secondary patterns, handover note template, recovery rules and the fairness ledger layout.
