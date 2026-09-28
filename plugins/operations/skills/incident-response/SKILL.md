---
name: incident-response
description: "Declare, command and mitigate a live production incident on any surface — a managed database failover, a third-party outage, a VM fleet, serverless, a CDN or DNS provider — mitigation first, diagnosis second. Assign an Incident Commander who is not a resolver, set severity once without debating it, scope the blast radius, mitigate by symptom (rollback, failover, feature-flag off, shed load, scale, switch dependency), capture evidence before the platform deletes it, and separate mitigated from resolved. Use this skill whenever someone says \"we have an incident\", \"the database won't fail over\", or \"prod is down and I'm IC\". Not for Kubernetes symptoms (k8s-triage), customer-facing wording (incident-comms), the write-up (postmortem), a durable procedure (runbook), alert or SLO tuning (alert-design), a rehearsed drill (game-day), or a red pipeline with no customer impact (ci-triage)."
allowed-tools: Read, Grep, Glob
---

# Incident Response

An incident is handled well when customer impact stops first and the explanation comes
second, on any surface — a managed database, a third-party dependency, a fleet of VMs, a
serverless function, a CDN, a queue.

The job is hard for the same reason on every surface: the instinct that makes someone a
good engineer — understand the system before you change it — is the wrong instinct
during an outage, and the platform underneath makes no difference to that fact. A
managed Postgres failover, a payment provider's status page turning red and a Lambda
error-rate spike are three different diagnoses and the same discipline: declare, name who
is in charge, stop the bleeding with the cheapest reversible action, and capture the
evidence that the platform will delete on its own schedule. This skill is the platform-agnostic
half of that discipline — command, severity, mitigation strategy, evidence, comms cadence,
handoff, and the line between mitigated and resolved. It hands off the moment the failing
surface is a Kubernetes workload, because that half has its own commands and its own
skill.

## Scope

Use for: declaring and running a live incident on any production surface — a managed
database that will not fail over cleanly, a third-party API or payment provider outage, a
VM or bare-metal fleet, a serverless function, a CDN or DNS provider, a message broker;
assigning incident-command roles; setting severity; choosing a mitigation strategy by
symptom; deciding when an incident is mitigated versus resolved.

Do not use for: a Kubernetes workload's symptoms — CrashLoopBackOff, OOMKilled,
ImagePullBackOff, Pending pods, a Service with no endpoints — which is `k8s-triage`;
customer-facing and status-page wording, which is `incident-comms`; the write-up after
service is restored, which is `postmortem`; a durable operational procedure written in
advance, which is `runbook`; tuning what pages or an SLO, which is `alert-design`; a
rehearsed drill rather than a real incident, which is `game-day`; a red CI pipeline that
has not caused customer impact, which is `ci-triage`; sizing a system for expected load,
which is `capacity-planning`; and turning raw scrollback into a postmortem draft, which is
the `incident-scribe` subagent.

## Workflow

Steps 0 through 2 are ordered and non-negotiable — everything after them adapts to the
symptom.

### 0. Declare early

Name an Incident Commander, open one channel, open one live incident document, and say
all three out loud so there is no ambiguity about who is running this. Declare if you need
a second team, if it is customer-visible, if it is unresolved after an hour of focused
analysis, or if you are about to do something you cannot undo. If unsure, declare —
de-escalation costs one message, and the alternative is an unbounded "I've almost got it"
with no timeline and no artefacts. Open an empty postmortem document at the same time,
even with nothing in it yet — it gives the write-up an owner and a place to land evidence
from the first minute rather than a scramble to reconstruct one afterwards. See
`references/incident-command.md` for the full role structure, when to declare, and how
roles scale down for a small incident.

### 1. Assign roles — the IC is not a resolver

The Incident Commander holds the state of the incident, assigns roles, and decides. The
IC does not debug, does not run commands, and does not carry another role at the same
time: "Delegate all repair actions, the Incident Commander is NOT a resolver," and "you
cannot take on another role at the same time as being an Incident Commander" (PagerDuty's
incident-response documentation, response.pagerduty.com). Roles scale down for a small
incident — one person can hold every role explicitly, which is fine, so long as everyone
knows which one they are holding right now.

### 2. Set severity, and do not debate it

Set it in the first few minutes from impact, not from the fix's difficulty. Default to
the higher severity whenever it is ambiguous, and do not relitigate it on the call:
PagerDuty's guidance is explicit — "if you are unsure which level an incident is … treat
it as the higher one. During an incident is not the time to discuss or litigate
severities," and "we always assume it's the higher severity." Revising it upward later
costs nothing; the hour of silence spent arguing about whether this is really a SEV1 costs
the response. See `references/incident-command.md` for a worked severity table and comms
cadence per level.

### 3. Scope the blast radius

One region, one dependency, one tenant, or everything? This decides which mitigation
applies and stops you debugging a downstream provider when the fault is your own load
balancer, or the reverse. Check your own edge and control plane first — a provider's
status page lagging behind reality is the default, not the exception.

### 4. Pick the mitigation by symptom

Take the cheapest reversible action that stops customer impact, and verify against the
real customer-facing metric afterwards — not a green health check, which can stay green
while the metric that matters stays broken.

| Symptom | Mitigation |
| --- | --- |
| Correlates with a recent deploy or config change | Roll it back. PagerDuty's own incident-commander checklist names this first: "Bad Deployment: Roll it back." |
| Scoped to one region, AZ or provider | Fail over traffic to another region, cluster or provider |
| One feature or code path is implicated | Turn the feature flag off |
| The system is up but overwhelmed | Shed load, rate-limit, or degrade a non-critical path |
| Saturation with capacity available | Scale out |
| One dependency is degraded and has a fallback | Switch to the backup dependency, or circuit-break the failing one |

Verify against the SLI after each action. If the first mitigation does not work, return
here rather than stacking a second one on top — two simultaneous changes make the
recovery unattributable.

### 5. Capture evidence before it expires

Every platform deletes its own evidence on a schedule nobody reads until they need it:
log retention windows, a provider's incident-history page, a managed database's event
log, a load balancer's connection log. Screenshot or export the dashboard, the error rate,
the provider's status update and its timestamp, and the exact command or console action
you took, before it ages out — the fifteen seconds this costs is the difference between a
postmortem with evidence and a shrug.

### 6. Communicate on a cadence

Name a comms owner in the first few minutes who is not the IC and not touching the
system, and hand outward-facing wording to `incident-comms` — acknowledging on impact
rather than on diagnosis, and a next-update promise that gets kept even when there is
nothing new. A responder call can go quiet; a stakeholder update cannot: PagerDuty's
Internal Liaison role is written to give the executive team a status update roughly every
30 minutes. Naming the next update time turns an open-ended outage into a bounded wait.

### 7. Hand off explicitly

Before the commander is tired enough to decide badly, hand off with current state, what
is in flight, what must not be done, and when the next update is due — acknowledged by
the incoming commander before the outgoing one leaves. Never hand off the Incident
Commander and the person mutating the system in the same few minutes: keep one line of
continuity across every transition. See `references/incident-command.md` for the handoff
script.

### 8. Mitigated is not resolved

Mitigated means customer impact has stopped. Resolved means the cause is fixed and every
temporary measure is gone or has an owner and a ticket to remove it. Use those exact
words so nobody mistakes one for the other. Before closing: the customer-facing metric
has been normal long enough to be believable, every temporary change has a decision to
keep it or a ticket to revert it, and the postmortem opened at declare time has an owner
and a date.

### 9. Hand off to postmortem

The write-up, the blamelessness rules and the action-item structure are the `postmortem`
skill's job — hand off to it rather than attempting it in the incident channel. If you
have raw scrollback and timestamps but no draft yet, the `incident-scribe` subagent turns
that into a first pass.

## Kubernetes workload? Hand off to k8s-triage

If the failing surface is a Kubernetes workload — a pod that will not start, stay up or
serve, a cluster or control-plane problem, a decision about rolling back a Deployment —
declare here using steps 0 through 2, then move diagnosis and mitigation to `k8s-triage`,
which covers the `kubectl`-level workflow, the deploy-correlation check, the evidence
commands and the symptom decode table this skill does not. Come back here for the comms
cadence, handoff and mitigated-versus-resolved discipline once the Kubernetes-specific
work is under way.

## Incident report format

Fill this in as you go, not at the end:

```markdown
## Impact
[Who is affected, how, and the SLI with its current value.]

## Status
INVESTIGATING | MITIGATING | MITIGATED | RESOLVED — with the time it changed.

## Timeline (UTC)
[First alert, declaration, each decision, each mutation, each verification.]

## Evidence
[Dashboards, the decisive log lines, provider status updates. Paste, do not summarise.]

## Changes made
[Every mutation, who ran it, and whether it is permanent or must be reverted.]

## Current hypothesis
[One or two sentences. Strike through disproved ones rather than deleting them.]

## Follow-ups
[Owner and ticket for each. Includes anything temporary still in place.]
```

## Reference files

- `references/incident-command.md` — the incident-command role structure and why
  separation increases autonomy, declare criteria, a severity table with comms cadence,
  the live incident document template, the handoff script, and closing criteria. Read it
  at step 0, or whenever the response grows past two people.

## Anti-patterns

**The IC debugging instead of commanding.** The single most expensive habit here. An IC
deep in a stack trace has stopped being the IC, and nobody has noticed yet — the
structure that was supposed to keep one person deciding has quietly lost that person to a
terminal. Delegate the repair action and stay the person holding the state.

**Paging everyone past span of control.** Beyond seven or eight people reporting directly
to one Incident Commander, the response gets slower, not faster — "if you have more than
7 or 8 people directly reporting to the Incident Commander things can quickly get
overwhelming" (PagerDuty). Mobilise extra help through a liaison role, not by paging the
whole org into one channel.

**Litigating severity on the call.** Every minute spent arguing whether this is really a
SEV1 or a SEV2 is a minute not spent mitigating, and the argument is never settled by more
discussion — it is settled by defaulting to the higher severity and moving on.

**Not escalating.** Hesitating to page someone more senior at 3am because the problem
might resolve itself, or might not be that bad, costs more than the page does: PagerDuty's
guidance is not to hesitate to page someone more knowledgeable when stuck on a problem at
3am. The cost of an unnecessary page is a few minutes of someone's night; the cost of an
incident that needed them and did not get them is measured in hours.
