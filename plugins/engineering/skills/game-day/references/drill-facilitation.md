# Facilitating a drill

Read this when the exercise is about the humans and the process rather than the
injection: unannounced on-call rehearsals, the observer's sheet, disaster-recovery and
restore tests against stated RPO and RTO, and running the debrief so findings leave the
room as tickets.

## Contents

- Human drills worth running
- Getting to unannounced
- The observer's sheet
- Disaster-recovery and restore drills
- The debrief
- Findings that recur

## Human drills worth running

The system half of a game day is usually the half that passes. These are the exercises
that find the expensive gaps.

**Unannounced page.** A synthetic but realistic alert fires to the real on-call at a real
hour. Measures detection, acknowledgement, escalation, and whether the runbook survives
contact. The single most informative drill available, and the one that needs the most
trust in place first.

**Runbook removal.** Run a familiar scenario with the runbook deliberately unavailable.
Everything the responder has to reconstruct from memory is either missing from the
runbook or badly placed in it. Uncomfortable, quick, and it produces a precise list of
documentation defects.

**Primary responder unreachable.** The person who always fixes this one is on a plane.
Measures bus factor honestly, and produces the finding nobody volunteers in a planning
meeting. Tell that person in advance and have them stay silent; do not surprise them
with being excluded.

**Comms drill.** Give someone a scenario and fifteen minutes to produce a customer-facing
status update, an internal summary, and the decision about whether to post publicly at
all. Customer communication is improvised during nearly every real incident, and it is
the part that ends up quoted.

**Escalation path.** Follow the on-call escalation as written, at the hour it would
actually happen. Rotas go stale: people leave, phone numbers change, a secondary is
listed who left the company. Verify against the roster in the tool, not against
someone's recollection.

**Incident command handover.** Run an incident long enough to force a handover between
two ICs. Handover is where context is lost in every long real incident, and it is never
practised.

## Getting to unannounced

Unannounced drills produce the only honest detection numbers, and they carry a real
social cost if the team has not seen how findings are handled. Escalate deliberately:

1. **Announced, scheduled.** Everyone knows what and when. Measures the mechanism, the
   runbook and the comms. Nothing about detection.
2. **Announced window.** "Some time this week." Measures detection with the anxiety
   removed, which is a reasonable compromise for a long time.
3. **Unannounced, business hours.** Real detection numbers, full team available.
4. **Unannounced, out of hours.** Only once the previous three have run clean, only with
   the rota's explicit agreement, and only when the findings from earlier rounds visibly
   got fixed.

The precondition for every step is that findings are treated as system defects. The first
time a drill result appears in a performance conversation, this programme is over — people
will pre-position for the next one and the numbers stop meaning anything.

Two things must be true even at step 4: someone outside the drill can confirm within
seconds that it is an exercise, and the responder can end the drill at any point with no
explanation required.

## The observer's sheet

One person, taking timestamps and nothing else. Wall-clock, not elapsed — elapsed is
computed later, and wall-clock lines up with the logs and the alert history.

```text
T+00:00  10:00:00  INJECTION: deregistered eu-west-1a targets from checkout-tg
         10:00:34  first 5xx visible in the SLI dashboard
         10:04:12  ALERT CheckoutErrorBudgetFastBurn -> #alerts-checkout (not the pager)
         10:07:40  responder acknowledged in channel
         10:08:10  QUESTION ASKED ALOUD: "is this zone-aware or not?"      <- finding
         10:09:55  opened the wrong dashboard (payments overview)          <- finding
         10:12:30  WRONG TURN: restarted checkout pods, no effect          <- finding
         10:16:05  first correct action: shifted weight away from 1a
         10:18:40  steady state restored
         10:18:41  ABORT not required
```

Rules for the observer: write everything, interpret nothing, help nobody. Every question
asked out loud is a finding — the responder is telling you what the documentation does
not say. Every wrong turn is a finding, and those are the most valuable lines in the
file; they are the traps that would have cost an hour at 3am.

Record where the alert went, not just that it fired. "Fired to a channel, not to the
pager" is the most common single cause of a bad detection number, and it is a
five-minute fix in the routing config — see `alert-design`.

## Disaster-recovery and restore drills

DR drills are graded against numbers the organisation has already committed to, so state
them before the exercise and measure against them afterwards.

- **RPO** — how much data you are permitted to lose. Measure it as the actual gap between
  the restored state and the moment of failure, not as the backup schedule's promise.
- **RTO** — how long recovery is permitted to take. Measure end to end: decision time,
  the restore itself, verification, DNS or traffic cutover, and the point at which users
  can actually transact again. Teams routinely measure the restore command and report it
  as the RTO, which understates the real number by a factor of three or more.

Run the restore from the documented procedure, executed by someone who did not write it.
That constraint is what turns a restore test into a documentation test, and the
documentation is what will be used at 4am by whoever is on call.

Record the gaps that only appear in a real restore: an encryption key held by one person,
a role that exists in the source account and not the target, an object outside the
snapshot, a configuration value that lives only in someone's terminal history, a restored
database that comes up with production credentials pointing at the wrong environment.

For a full region or provider failover, run the drill in the direction you would actually
use in anger, and then run the failback. Failback is usually less rehearsed than
failover, which is how a successful DR test turns into a second outage a day later.

## The debrief

Within 24 hours, 45-60 minutes, everyone who took part.

1. **The observer reads the timeline aloud.** No commentary from anyone until it is
   finished. It grounds the discussion in what happened rather than what people recall.
2. **The hypothesis, verdict first.** Confirmed or falsified, and which clause failed. A
   falsified detection clause with a working failover is the normal outcome and should be
   said plainly.
3. **The four numbers.** Detect, acknowledge, correct action, recover. Compare against the
   previous exercise if there was one; the trend matters more than the absolute.
4. **Every question and wrong turn, one by one.** For each: what would have prevented it?
   That answer is the finding, and it is nearly always a documentation, alerting or
   tooling change rather than a code change.
5. **Write the tickets in the room.** Title, owner, due date, tracker link, into the
   record before anyone leaves. This is the step the whole exercise exists for.
6. **Name the next experiment.** Usually the thing you were too nervous to inject today.

Blameless in the `postmortem` sense: a wrong turn is a defect in the system's legibility,
never in the person. The person who took it did the team a favour by finding the trap
during a drill.

Publish the record where the postmortems live, including the "what we did not test"
section. A drill report read as broader assurance than it earned is worse than no report,
because it retires a worry nobody actually addressed.

## Findings that recur

Across teams, the same handful come up almost every time. Check for them explicitly
rather than waiting to rediscover them:

- The alert fired to a channel rather than the pager, and detection time was dominated by
  someone happening to look.
- The runbook link resolves to an archived or moved page.
- The runbook documents the diagnosis and not the mitigation, so the responder read it and
  then improvised anyway.
- Dashboards are per-service, and nobody could see the user-facing SLI in one place.
- The failover works and the failback has never been tried.
- One person knows the recovery procedure and was not on call.
- Nobody knows who is authorised to declare an incident or post to the status page.
- Capacity in the surviving zones was adequate at drill traffic and would not have been at
  peak. Repeat the experiment at peak once, deliberately, before believing the result.
