---
name: k8s-triage
description: "Triage and mitigate a broken Kubernetes workload or a live production incident, mitigation first and diagnosis second — declare, test whether it is deploy-related and roll back, scope the blast radius, capture evidence before mutating anything, pattern-match the symptom, then escalate through rollback, scale-out, load shedding, failover, drain and restore. Use this skill whenever a pod, deployment, service or cluster is misbehaving — CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending or unschedulable pods, running but never Ready, stuck Terminating, DNS failures, RBAC 403s, a Service with no endpoints — and equally for casual phrasings like \"my pod won't start\", \"the deploy broke prod\", \"k8s is down\", \"why is this pending\", or \"we have an incident\". Not for authoring new manifests, capacity planning, or writing the postmortem once service is restored."
---

# Kubernetes Triage and Incident Response

Restore service first. Understand the failure afterwards, from evidence you captured on the way past.

The job is hard because the instinct that makes someone a good engineer — understand the system before you change it — is the wrong instinct during an outage. The goal of incident response is not knowledge; it is service. Every "let me just check one thing" in front of a rollback is a decision to extend the outage by however long that check takes, made without saying so out loud. The other half of the difficulty is that Kubernetes destroys its own evidence on a timer: events expire after an hour, the log of a crashed container is gone the moment someone deletes the pod, and the ReplicaSet history is trimmed by a revision limit. So the discipline is narrow and specific — mitigate fast, but capture the artefacts on the way, because the fifteen seconds it costs to save them is the difference between a postmortem and a shrug.

## Scope

Use for: a workload that will not start, will not stay up or will not serve; a live incident of any severity; a cluster or control-plane problem; deciding whether to roll back.

Do not use for: writing new manifests or Helm charts, capacity and cost planning, cluster upgrades planned in advance, or writing the postmortem after service is restored — that is the companion `postmortem` skill's job, and this skill hands off to it.

## Workflow

Steps 0 and 1 are ordered and non-negotiable. Everything after them adapts to what you find.

### 0. Declare

Name an Incident Commander, open one channel, open one live incident document. Say the three out loud in the channel so there is no ambiguity about who is running this.

Declare if you need a second team, if it is customer-visible, if it is unresolved after an hour of focused analysis, or if you are about to do something you cannot undo. If unsure, declare — de-escalation costs one message, and the alternative is a two-hour "I've almost got it" that ends in an escalation with no timeline and no artefacts.

Open the postmortem document now, empty. See `references/incident-command.md` for roles, severity, the document template and comms cadence.

### 1. Is it deploy-related?

The highest-yield question in Kubernetes operations, and the reason to ask it before anything else is that it is answerable in under a minute and its answer is also the fix.

```bash
kubectl rollout history deploy/"$NAME" -n "$NS"
kubectl rollout history deploy/"$NAME" -n "$NS" --revision=<n>   # shows change-cause
kubectl get rs -n "$NS" -l app="$NAME" --sort-by=.metadata.creationTimestamp
kubectl get deploy "$NAME" -n "$NS" -o jsonpath='{.metadata.annotations.kubernetes\.io/change-cause}{"\n"}'
```

The newest ReplicaSet's `creationTimestamp` is the rollout time. Compare it against the timestamp of the *first* alert, not the loudest one. Within a few minutes, and the deploy is the cause until proven otherwise. Also check anything else that ships: Helm (`helm history <release> -n <ns>`), a config or Secret change, an operator upgrade, a feature flag.

If the answer is yes, or probably yes, roll back now:

```bash
kubectl rollout undo deploy/"$NAME" -n "$NS"                     # previous revision
kubectl rollout undo deploy/"$NAME" -n "$NS" --to-revision=<n>   # a known-good one
kubectl rollout status deploy/"$NAME" -n "$NS" --timeout=180s
```

Then verify the SLI recovered — the actual customer-facing metric, not pod readiness. Pods can be Ready while the error rate stays at 40%.

Diagnose afterwards, from the artefacts. The old ReplicaSet is still there with its full spec; `kubectl rollout history --revision=<n>` shows the template diff; the logs you captured in step 3 are on disk. Nothing is lost by rolling back first, and an outage is shortened by exactly the length of the investigation you did not do in front of it.

If `rollout history` shows `<none>` for every change-cause, you cannot tell what shipped. Roll back anyway and file the missing annotation as a follow-up.

### 2. Scope the blast radius

One pod, one node, one AZ, one namespace, or cluster-wide? This determines what class of thing is broken and stops you debugging an application when a node is dying.

```bash
kubectl get pods -A -o wide --field-selector=status.phase!=Running | head -40
kubectl get nodes -o wide
kubectl get nodes -o json | jq -r '.items[] | . as $n | (.spec.taints // [])[] | "\($n.metadata.name)\t\(.key)=\(.value // ""):\(.effect)"'
kubectl get --raw='/readyz?verbose'
```

One pod of many replicas points at that pod or its node. Every pod on one node points at the node — check `kubectl describe node` for `DiskPressure`, `MemoryPressure` or `PIDPressure`, and check its taints. One AZ points at the cloud provider or zonal storage. One namespace points at a shared dependency, a quota, or a NetworkPolicy. Cluster-wide points at the control plane, DNS, or the CNI — `/readyz?verbose` names the failing control-plane check directly.

### 3. Capture evidence, in this order, before mutating anything

Fixed order because it runs in about thirty seconds and because each command answers a question the next one depends on. Save the output into the incident document.

```bash
# 1. State of every pod, with the reasons, in one shot
kubectl get pods -n "$NS" -o custom-columns='NAME:.metadata.name,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,WAITING:.status.containerStatuses[*].state.waiting.reason,LASTTERM:.status.containerStatuses[*].lastState.terminated.reason,EXIT:.status.containerStatuses[*].lastState.terminated.exitCode,NODE:.spec.nodeName'

# 2. Events, oldest first — the default order is useless
kubectl get events -n "$NS" --sort-by=.metadata.creationTimestamp | tail -40
kubectl events --for pod/"$POD" -n "$NS" --types=Warning

# 3. Full object state, including conditions and the resolved image digest
kubectl describe pod "$POD" -n "$NS"

# 4. Logs — --previous is mandatory for anything that has restarted
kubectl logs "$POD" -n "$NS" -c "$CONTAINER" --previous --tail=200
kubectl logs "$POD" -n "$NS" -c "$CONTAINER" --tail=200
kubectl logs -n "$NS" -l app="$NAME" --tail=50 --prefix     # across all replicas

# 5. Actual resource usage against the limits
kubectl top pod -n "$NS" --containers
kubectl top node
```

**Events expire after an hour.** The `kube-apiserver` `--event-ttl` default is `1h0m0s`, so an incident that started ninety minutes ago has no events left, and `get events` returning nothing means nothing. This catches people out constantly: they conclude "no events, so no scheduling problem" when the events simply aged out. For anything older than an hour go to the event exporter, the logging pipeline, or the audit log. If your cluster has no event exporter, note that as a follow-up — it is cheap and it is exactly what you want during the incident you cannot reproduce.

When the container has no shell, or crashes before you can exec in, use ephemeral containers:

```bash
# Attach a debug container sharing the target's process and network namespace.
# --target is required to see the app's processes; distroless images need this.
kubectl debug -it "$POD" -n "$NS" --image=busybox:1.28 --target="$CONTAINER" --profile=general

# Copy the pod and override the crashing entrypoint, leaving the original untouched
kubectl debug "$POD" -n "$NS" -it --copy-to="$POD"-dbg --set-image='*=busybox:1.28' -- sh

# Copy with process namespace sharing, to inspect the real process from a debug image
kubectl debug "$POD" -n "$NS" -it --image=ubuntu --share-processes --copy-to="$POD"-dbg

# Node-level: host filesystem under /host, host namespaces
kubectl debug node/"$NODE" -it --image=ubuntu --profile=sysadmin
```

`--profile` values are `legacy`, `general`, `baseline`, `restricted`, `netadmin` and `sysadmin`. `legacy` is the default and is on its way out — pass `general` explicitly. Use `netadmin` for packet capture and `NET_RAW` work, `sysadmin` for privileged host access, and `restricted` where Pod Security admission enforces the restricted policy. Delete the copied pod when finished; it counts against quota and confuses the next responder.

### 4. Pattern-match

Take the `WAITING` or `LASTTERM` reason and the exit code from step 3 into `references/decode-table.md`. It gives, per symptom, the one piece of evidence that decides between causes and the causes ordered by prior probability. Work top-down and stop at the first that matches — do not build a theory that requires two simultaneous faults until you have eliminated the single-fault explanations.

The headline decodes, for orientation: exit 1 is an application or config error; 137 is OOMKilled or a SIGKILL after the grace period; 143 is SIGTERM, usually a liveness probe; 126 and 127 are entrypoint problems and mean a distroless image with shell-form `CMD` more often than not. CrashLoopBackOff backs off 10s, 20s, 40s, 80s, 160s and caps at 300s, so a pod that looks frozen may just be waiting.

### 5. Mitigate, in escalating order

Take the cheapest reversible action that stops customer impact. Each step is more disruptive and harder to undo than the one above it, so do not skip down the list because a lower step feels more decisive.

| Order | Mitigation | Use when | Cost |
| --- | --- | --- | --- |
| 1 | `kubectl rollout undo` | Anything correlating with a deploy | Seconds, fully reversible |
| 2 | Scale out — `kubectl scale --replicas=N` | Saturation, or too few healthy replicas | Cost only, if capacity exists |
| 3 | Shed load or disable a feature flag | The system is up but overwhelmed; one code path is the culprit | Degraded feature, no restart |
| 4 | Fail over — shift traffic to another region, cluster or AZ | The failure is scoped to one location | Minutes, and failing back is work |
| 5 | `kubectl cordon` then `kubectl drain --ignore-daemonsets --delete-emptydir-data` | One node is the fault and pods can move | Reschedules everything; needs capacity |
| 6 | Restore from backup | Data loss or corruption | Slow, lossy, hardest to undo — needs an explicit IC decision |

Announce each action in the channel before running it and record it in the "changes made" section of the incident document, including anything temporary that must be reverted later. Only the Operations Lead runs mutations.

Verify against the SLI after each one. If the first mitigation does not work, go back to step 2 rather than stacking a second mitigation on top — two simultaneous changes make the recovery unattributable and can interact badly.

### 6. Communicate on a cadence

Publish every 30 minutes for SEV1 and SEV2, from the declaration, and publish even when there is nothing new. Every update states impact in customer terms and names the time of the next update.

> **14:30 UTC — INC-241, SEV2, still investigating.** Roughly 12% of checkout requests are timing out. We have ruled out the 13:58 deploy. No change since the last update. Next update 15:00 UTC.

The no-news update is the one that matters: silence is what generates DMs to the person who must not be interrupted. Naming the next update time turns an open-ended outage into a bounded wait.

### 7. Hand off explicitly

Every two to three hours on an active incident, before the commander is tired enough to decide badly. The handoff states current state, what is in flight, what must not be done, and when the next update is due — and the incoming commander acknowledges it in the channel before the outgoing one leaves. Never hand off IC and Operations Lead in the same five minutes. The script is in `references/incident-command.md`.

### 8. Mitigated is not resolved

Mitigated means customer impact has stopped. Resolved means the cause is fixed and the temporary measures are gone. Use those exact words so nobody mistakes one for the other — the gap between them is where a rolled-back release quietly gets re-applied and where a "temporary" memory limit becomes the design.

Before closing: the SLI has been normal long enough to be believable; every temporary change either has a decision to keep it or a ticket to revert it; the postmortem opened at declare time has an owner and a date. The companion `postmortem` skill in this repository covers the writing itself — hand off to it rather than attempting it in the incident channel.

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
[Pod states, exit codes, the decisive log lines and events. Paste, do not summarise.]

## Changes made
[Every mutation, who ran it, and whether it is permanent or must be reverted.]

## Current hypothesis
[One or two sentences. Strike through disproved ones rather than deleting them.]

## Follow-ups
[Owner and ticket for each. Includes anything temporary still in place.]
```

## Reference files

- `references/decode-table.md` — the full symptom table: CrashLoopBackOff and exit codes, OOMKilled, image pull failures, Pending and unschedulable, Running but not Ready, stuck Terminating, DNS, RBAC 403, Services with no endpoints. Read it at step 4, and read the relevant section before proposing any cause.
- `references/incident-command.md` — roles and why separation increases autonomy, declaration criteria, severity levels, the live incident document template, comms cadence, the handoff script. Read it at step 0, or whenever the response grows past two people.

## Anti-patterns

Each of these looks like diligence and costs minutes of outage or destroys the evidence.

**Diagnosing before rolling back a suspicious deploy.** The single most expensive habit in this document. If the timeline correlates, the rollback is both the mitigation and the test of the hypothesis, and it takes less time than reading the logs would. Every minute spent understanding first is a minute of outage bought with nothing.

**`kubectl delete pod` as a reflex.** It destroys the `--previous` log, discards the pod's events and conditions, and masks the loop by resetting the restart count — so the same failure now looks intermittent. The Deployment recreates the pod into the identical failure anyway. Capture first, then delete if you must.

**Reading only the current logs on a CrashLooping pod.** The current container has produced nothing because it is not running. `--previous` is where the failure is. Concluding "no errors in the logs" from an empty current log has sent more people down more wrong paths than any other mistake here.

**`get events` without `--sort-by`, and not knowing they expire.** The default order is not chronological, so the relevant event is anywhere in the list. And with a 1-hour TTL, an empty result on an older incident means the evidence aged out, not that nothing happened.

**A liveness probe pointed at a dependency.** Converts a downstream outage into a self-inflicted restart storm: every pod fails its probe, restarts, loses its warm cache and connection pool, and cannot recover even after the dependency does. Readiness may reflect a dependency; liveness must only reflect whether the process itself is wedged.

**Raising memory limits as the standing fix.** Against a limit that was genuinely too low it is correct once. Against a leak it buys time proportional to the headroom and nothing else, and it converts a loud failure into a slower, quieter one that now happens at 4am instead of during deployment.

**Everyone typing kubectl at once.** Three people roll back, scale up and delete pods within thirty seconds, service recovers, and nobody can say which change did it — or which one caused the next incident. One Operations Lead, announcing each mutation before running it.

**No `change-cause` annotation.** `rollout history` shows `<none>` for every revision, so it is useless at the exact moment you need it. Set it in CI, with the commit SHA and the PR, on every deployment.
