# Rota structure

## Sizing arithmetic

On call one week in N means N minus one weeks off between shifts. With a primary and a secondary on different weeks, each person spends two weeks in N on call.

| Engineers | Weeks between primary shifts | Share of the year as primary |
| --- | --- | --- |
| 4 | 3 | 25% |
| 6 | 5 | 17% |
| 8 | 7 | 12.5% |

Google's SRE book sizes a single-site rotation at a minimum of eight engineers, and a dual-site one at six per site. Smaller teams are not forbidden from running a rota, but the numbers above are what they trade away. Options for a team below the guidance:

- Cover business hours only and make out-of-hours cover best-effort, stated in writing.
- Join a larger rotation with a neighbouring team that runs similar technology.
- Add a second site, even a small one, so nobody takes routine night pages.
- Lower the service's cover promise to what the team can honestly keep.

## Primary and secondary

- The primary takes the page. The secondary is paged if the primary does not acknowledge within a set time, and is available to help with a hard incident.
- A secondary that is never paged and never helps is not a secondary. Check the data for escalations.
- A secondary should be someone who can take over; a new joiner shadows rather than serves.

## Handover note

A short written note from the outgoing person, followed by a short live exchange:

```markdown
Rotation handover, [date]
Open incidents or follow-ups: ...
Alerts that were noisy this shift, and what I did about them: ...
Anything I changed (silences, thresholds, manual workarounds still in place): ...
Things I expect to bite next: ...
```

## Recovery

- A night with a sleep-interrupting page earns a late start; two such nights in a shift earn a day off, taken within the following two weeks.
- The time is owed back automatically and visibly. If people have to ask for it, many will not.
- Record recovery taken against recovery owed in the same ledger as swaps.

## Fairness ledger

| Person | Holiday shifts (year) | Weekend shifts | Swaps covered for others | Swaps others covered for them | Recovery owed | Recovery taken |
| --- | --- | --- | --- | --- | --- | --- |

Review it each quarter. A person whose covered swaps far exceed their owed ones is subsidising the rota, and that is where resentment starts. Agree the rules for public holidays in advance so that nobody has to negotiate them.

## Compensation and time off

Read the written policy and ask HR, then record:

- What is paid or credited for simply being on call.
- What is paid or credited for each out-of-hours page or incident.
- Whether time off in lieu is available, and how it is claimed.
- Whether legal minimum rest periods apply where your engineers work. Rules differ by country and contract, so confirm with HR or legal advisers and do not rely on this document.

When nothing is written, propose a written policy as a change-list item. Pay is not a substitute for fixing the load, but an unpaid load beyond contract hours is a separate problem to settle openly.
