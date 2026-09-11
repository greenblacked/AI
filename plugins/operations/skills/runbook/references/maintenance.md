# Keeping runbooks true

Read this when a runbook already exists. Writing one is the easy half; a document that
is trusted and wrong is the failure this file is about.

## Contents

- Why a wrong runbook is worse than none
- Verify by execution, not by reading
- The ownership and freshness record
- Review cadence
- When a runbook fails mid-incident
- Deleting a runbook

## Why a wrong runbook is worse than none

A responder with no runbook escalates in the first two minutes. A responder with a stale
one follows it confidently, runs a command against a namespace that was renamed six
months ago, gets an error they do not understand, and spends fifteen minutes deciding
whether the error means the system is broken or the document is. The document's
authority is what costs the time.

So the goal of maintenance is not that every runbook is current — that is unachievable
across a few hundred documents. It is that the reader can tell how much to trust the one
in front of them, and that the ones behind paging alerts are current.

## Verify by execution, not by reading

Reading a runbook proves nothing. The author reads their own document and sees what they
meant; the commands are checked against memory rather than against production. Every
verification method that works involves someone actually running the steps.

| Method | Cost | What it proves |
| --- | --- | --- |
| Game day or DR drill | Half a day | The whole procedure works, including the parts nobody remembered were manual |
| Staging walkthrough by a non-author | An hour | The commands run and the document is followable by someone without context |
| Real incident | Free, already paid for | The parts that were reached; nothing about the branches that were not |
| Reading it in review | Minutes | That it is well written. Not that it is true |

The strongest signal comes from `game-day`: pick the runbook, inject the failure it
describes, and have someone who did not write it drive from the document alone. The
author sits in the room and stays silent — every question the responder asks out loud is
a defect in the document, and the list of those questions is the edit list. Stamp the
last-verified date from the drill.

Where a drill is too expensive, the cheap substitute is a walkthrough in staging by the
newest person on the rota. It catches the two most common defects — a command that no
longer runs, and a step that assumes knowledge — for the price of an hour.

## The ownership and freshness record

Three fields at the top of every runbook, and one index across all of them:

- **Owner**: the rota or team, never a person. Ownership transfers with the service, and
  a runbook whose owner has left is a runbook nobody will update.
- **Last verified**: the date, who did it, and how — drill, walkthrough or real incident.
  "Edited" is not "verified"; a typo fix does not refresh the date.
- **Alerts that link here**: which pages land on this document. This is what makes the
  reverse check possible.

Then run two reverse checks periodically, both cheap to automate:

1. Every `runbook_url` in the alerting configuration resolves to a document that exists.
   A 404 at 3am is the worst possible time to discover a moved page.
2. Every runbook is reachable from at least one alert, dashboard or index. An
   unreferenced runbook is either dead weight or a missing link, and both are worth
   knowing about.

## Review cadence

Tie the cadence to the consequence of being wrong rather than to the calendar alone:

| Runbook behind | Verify | Why |
| --- | --- | --- |
| A paging alert | Every 6 months, and after any change to the service's deploy or topology | It is read under maximum time pressure |
| A failover, restore or DR procedure | Every 6 months, by drill | These are never exercised in normal operation, so they rot silently and fail completely |
| A ticket-severity alert | Annually | Read during working hours, with time to recover from an error |
| A procedure that has not been executed in a year | Ask whether it should exist at all | Either the system changed or the failure stopped happening |

Any change to the underlying system is the real trigger. A rename, a namespace move, a
new dependency, a migration to a different runtime — each invalidates commands. The
cheapest place to catch it is the pull request that makes the change: if the service
repository holds its runbooks, a reviewer sees them in the diff.

## When a runbook fails mid-incident

This is the highest-value moment for the document, and the one most often wasted,
because the responder is relieved the incident is over and the notes are in a channel
that scrolls away.

During the incident, capture the failure in the incident document as it happens: the
step number, what the runbook said, what actually happened. One line, no analysis.

Then make the fix a postmortem action item with an owner and a date, exactly like any
other. `postmortem` covers the write-up; what matters here is that "update the runbook"
is a real ticket against the document, not a bullet in a summary nobody re-reads. The
person who hit the defect writes the correction, because they are the only one who knows
what they needed and did not find.

If the runbook was so wrong that it sent the responder in the wrong direction, that is
itself worth a timeline entry. It is a contributing factor to the duration of the
incident and should be named as one.

## Deleting a runbook

Delete when the system it documents is retired, when the alert that links to it has been
deleted, or when the procedure it describes has been fully automated. A runbook for a
service that no longer exists is a trap: it is indexed, it is searchable, and it will be
found by someone matching on a symptom string years later.

Delete rather than archive where the archive is in the same search index as the live
documents. If archiving, put a dated "this system was retired" banner as the first line,
because that is all a responder will read.

The one thing not to do is leave it in place because deleting feels risky. An
unreferenced, unverified runbook for a dead system has no upside and one specific,
expensive downside.
