# Incident Command

Read this when declaring, when the response has more than two people in it, when nobody is
sure who is allowed to type, or when the current commander has been running the incident
for more than two hours. The role structure is Google's SRE incident management model; the
reasoning below is theirs and is worth stating because it is counterintuitive.

## Contents

- [Why roles, and why separation increases autonomy](#why-roles-and-why-separation-increases-autonomy)
- [The roles](#the-roles)
- [When to declare](#when-to-declare)
- [Severity](#severity)
- [The live incident document](#the-live-incident-document)
- [Comms cadence](#comms-cadence)
- [Handoff](#handoff)
- [Closing the incident](#closing-the-incident)

## Why roles, and why separation increases autonomy

The intuition is that assigning roles constrains people. The opposite holds. A clear
separation of responsibilities gives each responder *more* autonomy, because they do not
have to second-guess their colleagues: the person on operations can make and execute a
change without asking whether someone else is already halfway through a conflicting one,
and the commander can decide without relitigating who owns the decision. Ambiguity is what
actually slows people down — two engineers each waiting to see whether the other will act,
or both acting at once on the same Deployment.

The second reason is cognitive load. An engineer who is simultaneously debugging, updating
the status page, answering an executive in a DM, and deciding whether to fail over will do
all four badly. Splitting the work is not ceremony; it is the only way any of it gets done
properly under stress.

## The roles

**Incident Commander (IC).** Holds the high-level state of the incident and holds
*de facto every role that has not been explicitly delegated*. This is the important part:
if there is no Communications Lead, the IC owns comms, and if there is no Planning Lead,
the IC owns planning — there is never a gap. The IC structures the response, assigns
roles, drives decisions, and keeps the incident document accurate. The IC does not debug
and does not run commands. An IC deep in a stack trace has stopped being the IC, and
nobody has noticed yet.

**Operations Lead (OL).** The only person who mutates the system. Every `kubectl apply`,
rollback, scale, restart, failover and config change goes through the OL, who announces
each one in the channel before running it and reports the result after. Others propose;
the OL executes. This is what prevents the failure where three engineers independently
roll back, scale up and delete pods within the same thirty seconds, and nobody can later
say which change produced the recovery — or which one caused the second outage.

**Communications Lead (CL).** Owns stakeholder updates: the status page, the customer
message, the executive summary, the support team's talking points. Shields the OL and IC
from the incoming question stream. The CL writes updates from the incident document rather
than by interrupting the OL.

**Planning Lead (PL).** Handles everything on a longer horizon than the current action:
files bugs, tracks follow-up items, arranges relief and handoffs, tracks what has been
changed and needs reverting later, and organises food and rest for a response running past
a few hours. Sounds trivial; it is why hour six goes better than it otherwise would.

For a small incident one person holds all four, which is fine and explicit — the IC holds
what is not delegated. The point is that the roles are *named*, so everyone knows whether
they are currently the person who types.

## When to declare

Declare if any of these is true:

- You need a second team's help, or you are about to page someone outside your rota.
- The problem is customer-visible, or will be within the hour.
- It is still unresolved after an hour of focused analysis by one person.
- You are considering a mitigation you cannot easily undo — a data restore, a failover, a
  force delete on a StatefulSet.
- Somebody senior is asking for updates. If comms need managing, it is an incident.

If you are unsure whether to declare, declare. De-escalation is cheap: you close the
channel, note it in the document, and go back to what you were doing. The failure mode
that hurts is the two-hour "I've almost got it" that turns into a customer escalation with
no timeline, no artefacts and no shared understanding of what has been tried.

## Severity

Set it in the first five minutes and revise as you learn more. Severity drives the comms
cadence and who gets woken up, nothing else.

| Sev | Meaning | Comms cadence |
| --- | --- | --- |
| SEV1 | Complete outage, or data loss or corruption in progress | 30 minutes, plus on any material change |
| SEV2 | Major degradation, a critical path broken, or a significant subset of customers affected | 30 minutes |
| SEV3 | Partial or minor degradation with a workaround in place | 2 hours, or on change |
| SEV4 | No customer impact; tracked so it does not get lost | On resolution |

Revising severity upward is normal and carries no penalty. Delaying it because upgrading
feels like an admission is how a SEV2 becomes a SEV1 with an hour of unexplained silence
in front of it.

## The live incident document

One document, created at declare time, linked in the channel topic, writable by everyone
in the response. It replaces the need to scroll a thousand-message channel and it is what
the postmortem is written from.

```markdown
# INC-<id> — <one line: what is broken, for whom>
Status: INVESTIGATING | MITIGATING | MITIGATED | RESOLVED
Severity: SEV<n>        Declared: <UTC>       Next update: <UTC>
IC: @name   OL: @name   CL: @name   PL: @name
Channel: #inc-<id>      Postmortem: <link, created now, empty is fine>

## Impact
Who is affected, how, and how you know. Include the SLI and its current value.

## Timeline (UTC, newest at the bottom)
14:02  First alert: checkout p99 latency above 2s
14:05  Declared SEV2. IC @a, OL @b
14:09  rollout history shows deploy/checkout revision 47 at 13:58 — correlates
14:11  OL: kubectl rollout undo deploy/checkout -n prod  → revision 46
14:14  p99 back to 180ms. Status MITIGATED

## Current hypothesis
One or two sentences. Cross it out when disproved rather than deleting it — the
disproved hypotheses are the most useful part of this document later.

## Changes made (every mutation, so they can be reverted)
- 14:11  rollout undo deploy/checkout prod (47 → 46) — @b
- 14:30  memory limit 512Mi → 1Gi on checkout — @b — TEMPORARY, revert after fix

## Open questions / follow-ups
- Why did the canary not catch this?
```

The "changes made" section is the one people skip and the one that matters most. Without
it, the cleanup after the incident is archaeology, and temporary mitigations become
permanent by forgetting.

## Comms cadence

Publish on a fixed interval, from the start, and publish *even when there is nothing new*.
The purpose of the cadence is not information transfer; it is to stop stakeholders from
interrupting the responders to ask for information. A silent channel generates DMs to the
OL, which is precisely the person who must not be interrupted.

The no-news update is the important one and it has three parts: what is known, that
nothing has changed, and when the next update lands.

> **14:30 UTC — INC-241, SEV2, still investigating.** Checkout latency remains elevated;
> roughly 12% of checkout requests are timing out. We have ruled out the 13:58 deploy.
> No change since the last update. Next update 15:00 UTC.

Always name the next update time. It converts an open-ended outage into a bounded wait,
and it is the single cheapest thing you can do to reduce pressure on the response.

Every update states impact in customer terms, not in Kubernetes terms. "12% of checkouts
are failing" is an update; "the checkout ReplicaSet is CrashLoopBackOff" is a log line.

## Handoff

Hand off before you are tired enough to make the decision badly — roughly every two to
three hours for an active SEV1 or SEV2. The handoff must be explicit and *acknowledged*;
an unacknowledged handoff means the incident briefly has no commander, which is how a
mitigation gets left half-applied.

Outgoing IC posts in the channel:

> **Handoff: IC @outgoing → @incoming, 16:00 UTC.**
> **State:** SEV2, MITIGATED. Checkout p99 at 180ms since 14:14 after rolling back
> deploy/checkout to revision 46. Not resolved: revision 47 is still broken and unshipped.
> **In flight:** @b is diffing 46 against 47. Memory limit on checkout is temporarily at
> 1Gi and must be reverted.
> **Do not:** re-apply revision 47 without a canary.
> **Next update due:** 16:30 UTC. Document: <link>
> @incoming — please confirm you have it.

Incoming IC replies with an explicit acknowledgement — "Confirmed, I have IC as of 16:02"
— and only then does the outgoing IC leave. Then update the roles line in the document and
the channel topic, so someone arriving cold reads the current commander rather than the
first one.

Hand off the OL role the same way, and never hand off IC and OL in the same five minutes:
keep one line of continuity across every transition.

## Closing the incident

**Mitigated is not resolved.** Mitigated means the customer impact has stopped. Resolved
means the cause is fixed and the temporary measures are gone. Say which one you mean, in
those words, every time — the gap between them is where reverted rollouts get re-applied
and where a "temporary" memory limit becomes the architecture.

Before closing:

- The SLI is back to normal and has stayed there long enough to be believable, not just
  long enough for one scrape interval.
- Every entry in "changes made" is either permanent by decision or has a ticket to revert.
- Temporary capacity is either kept deliberately or scaled back.
- The postmortem document — created at declare time — has an owner and a date.
- The final comms update says explicitly that the incident is closed and where the
  postmortem will appear.

The postmortem itself is a separate job with its own discipline; the companion
`postmortem` skill in this repository covers the writing, the blamelessness rules and the
action-item structure. Do not attempt it inside the incident channel at 3am.
