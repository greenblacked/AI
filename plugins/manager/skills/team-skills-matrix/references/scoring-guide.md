# Scoring guide

Read this when scoring or setting up the sheet: behavioural anchors for the four levels,
the layout and how to calibrate the team in one sitting.

## In this file

- Anchors by kind of capability
- Sheet layout
- Calibrating together
- Counting availability

## Anchors by kind of capability

| Capability | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Operational (restore the database from backup) | Has not seen it done | Has followed the runbook with someone present | Has restored independently, in a drill or real case | Has taught it and led a real restoration under pressure |
| Delivery (cut a release) | Has not released | Released with a buddy | Releases alone, handles a failed step | Has fixed the release process itself and trained others |
| Domain (explain how invoices are reconciled) | Cannot describe it | Can describe the happy path | Can trace a mismatch to its cause | Can explain the edge cases and the history of why |
| Incident (respond when the queue backs up) | Never paged on it | Joined as second responder | First responder, resolved a real page | Has led the review and changed the alerts |

Anchor each row to something observable. If the team cannot tell whether a person is a
two or a three on a row, the row is too vague; split it.

## Sheet layout

One sheet, rows are capabilities, columns are people, with extra columns for:

- Source: incident reference, roadmap item or recurring task.
- Count at level 2 or above, computed, counting only people available over the next two
  quarters.
- Flag: yes when the count is below two.
- Risk score: impact (1 to 3) multiplied by likelihood of absence (1 to 3).
- Last scored: date, so stale rows stand out.

Keep a second tab per quarter rather than overwriting, so trends are visible.

## Calibrating together

Score in a single sitting with the whole team and the lead. For each row, each person
states a level with the evidence (last time they did it, what happened), then the group
adjusts. Begin with two rows everyone knows well, to fix what a two and a three mean, and
only then move to the rest. Disagreements are useful: a person scoring themselves one
where colleagues say two usually holds a standard the team should know about.

## Counting availability

Do not count a person for a row if they are on notice, on leave through the next quarter,
about to move teams, or part time such that they would not be reachable in the relevant
hours. Mark the person "not counted" in the shared sheet with no reason given, so the count can
be recomputed when circumstances change. The lead keeps the reasons privately; an
unannounced departure, leave or move is never written in the shared file.
