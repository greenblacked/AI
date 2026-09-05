---
name: runbook
description: "Write, review or repair the operational document someone follows at 3am — the thing on the other end of an alert's runbook link: what the symptom means in user terms, how to confirm it is real rather than a monitoring artefact, what to capture before mutating anything, the mitigations ordered least-destructive first with the blast radius and the undo next to each, a decision table mapping observation to conclusion to next step, and an owner and last-verified date so it can be trusted. Use this skill whenever someone is writing or fixing a runbook, playbook, on-call procedure or operational checklist — including \"this alert has no runbook\", \"document what to do when the queue backs up\", \"write the on-call procedure for failover\", or \"our runbooks are out of date\". Do not use it to diagnose an incident happening now, to decide what should page, to plan a rehearsal, or to write the postmortem afterwards."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(kubectl:*), Bash(gh:*)
---

# Runbook

A good runbook is one a person who has never seen the system can follow, correctly, at 3am, without waking anyone else up.

The job is hard because runbooks are written in the wrong state of mind for the state of mind they are read in. They are written calmly by the person who built the thing, in daylight, with all the context loaded; they are read by someone half awake, stressed, unfamiliar with the service, on a phone, about to run a command against production. Everything the author knew implicitly becomes a gap the reader has to fill by guessing, and a guess at 3am is how a mitigation becomes the incident. The second failure is slower and worse: runbooks rot. The command changes, the dashboard moves, the named escalation contact leaves, and nobody notices because nobody reads a runbook until they urgently need it. A wrong runbook costs more than no runbook, because a missing one sends the responder to a human immediately while a wrong one sends them confidently in the wrong direction first.

`alert-design` requires every alert to carry a `runbook_url`. This skill writes what is on the other end of it. The gap between the two is where most alerting programmes quietly fail: the rules are good, the links are present, and every one of them lands on a page that says "investigate the issue".

## Scope

Use for: writing the runbook behind an alert or a recurring symptom; a failover, restore, key-rotation or scale-out procedure; reviewing an existing runbook against the system it claims to describe; repairing one that failed during a real incident; deciding which steps have earned automation.

Do not use for: diagnosing a live Kubernetes or production failure (`k8s-triage`), deciding whether a signal should page at all (`alert-design`), writing the incident write-up afterwards (`postmortem`), planning a rehearsal or chaos exercise (`game-day`), or drafting customer-facing status updates (`incident-comms`).

## The reader is the design constraint

Assume all four at once, because on the night they all hold:

- **Tired.** No inference. If a step requires connecting two facts stated in different sections, it will not happen.
- **Stressed.** No prose. Numbered steps, one action each, in the order they are performed.
- **Unfamiliar.** No internal jargon, no assumed knowledge of the service's architecture, no acronym used before it is expanded.
- **About to act.** Every command is going to be pasted into a real shell against real production. Write it as though you are running it yourself.

That set of constraints rules out most of what people put in runbooks. Background, rationale, architecture and history are all valuable — and all belong somewhere else, linked, not inline.

## What a runbook is not

| Document | Answers | Written when | Read when |
| --- | --- | --- | --- |
| **Runbook** | "What do I do right now?" | Calmly, in advance | During the failure |
| Architecture doc | "How does this work?" | At design time | While onboarding or changing the design |
| Postmortem | "Why did this happen and what changes?" | After the incident | Weeks later, by someone else |
| Training guide | "How do I learn to operate this?" | For a new joiner | Before being on call |

Mixing them is the most common way a runbook becomes unusable: three paragraphs of architecture in front of step 1 means the responder is reading design documentation while the error rate climbs. Link out to those documents from a "Background" section at the *bottom*, below every step.

## Workflow

Work top to bottom. The document you produce follows the same order, because it is the order a responder acts in.

### 1. Write the meaning line

One sentence, in user terms, at the very top: what is happening to whom while this alert is firing.

> Checkout is returning errors to customers. Some fraction of purchase attempts are failing.

Not "the `checkout-api` 5xx ratio exceeded its burn-rate threshold". The responder needs to know within five seconds whether this is worth the adrenaline, and the impact sentence is what tells them. If you cannot write this sentence, the alert on the other end may not deserve to page — take that back to `alert-design` rather than papering over it here.

Immediately below it, state the expected severity and whether customer communication is likely to be needed. That is the second decision the responder makes and it should not require reading further.

### 2. Write the confirmation step

Before anything is changed, the responder has to know the alert is true. Monitoring artefacts — a dead exporter, a scrape gap, a dashboard on a stale time range, a rule that fires on a single failed request — are a large share of pages, and the fix for a false page is not the fix for a real one.

Give one read-only command or one dashboard link, and say explicitly what a real problem looks like versus what a monitoring artefact looks like:

```bash
# Read-only. Is the error ratio actually elevated right now?
curl -sS --max-time 10 'https://prometheus.internal/api/v1/query' \
  --data-urlencode 'query=sum(rate(http_requests_total{job="checkout",code=~"5.."}[5m]))
                          / sum(rate(http_requests_total{job="checkout"}[5m]))' | jq '.data.result'
```

- A value above 0.01 sustained across two evaluations: real, continue to step 3.
- An empty result or `up{job="checkout"} == 0`: the exporter is gone, not the service. Go to the telemetry runbook instead.
- A value near zero: the alert has already cleared. Record it and stop.

### 3. Write scope and severity

Two or three read-only commands that answer "how much of it, and for how long". The responder uses this to decide whether to declare an incident and whether to wake anyone else, so it comes before any mitigation.

Say what each answer means. "Check the dashboard" is not a step; "if the affected fraction is above 10% or any paying tenant is fully down, declare a SEV2 and name an incident commander" is.

### 4. Say what to capture before anything is mutated

The fix destroys the evidence. Container logs vanish when the pod is replaced, Kubernetes events expire on a timer, the in-memory queue state is gone the moment the process restarts, and the connection pool that was exhausted is empty and healthy the second after the restart.

Put an explicit capture block between the diagnosis steps and the first mutating step, with the commands and where to paste the output. Fifteen seconds here is the whole difference between a postmortem with a cause and one that says "we restarted it and it went away".

### 5. Write the mitigations in order of reversibility

Least destructive first, and the reader works down the list only when the step above did not work. Each mitigation states three things without exception: what it does, its blast radius, and how to undo it.

| Order | Mitigation | Blast radius | Undo |
| --- | --- | --- | --- |
| 1 | Roll back to the previous release | New requests served by the old version; in-flight requests unaffected | Roll forward once the fix is ready |
| 2 | Scale out to 12 replicas | Cost only, if the cluster has capacity; none if it does not, and pods sit Pending | Scale back to 6 |
| 3 | Disable the recommendations feature flag | Product surface degrades for everyone; no restart, no dropped requests | Re-enable the flag |
| 4 | Restart the pods | Drops in-flight requests, loses the warm cache; roughly 90s of elevated latency after | Nothing to undo, but the state is gone |
| 5 | Fail over to the secondary region | All traffic moves; replication lag means up to 30s of recent writes may be missing | Failing back is a separate, slower procedure |

"Restart the service" with no blast radius is how a responder drops four hundred in-flight payments to clear a warning. If a mitigation is genuinely irreversible — a restore from backup, a destructive schema change, a cache purge that will take an hour to warm — mark it as requiring an explicit incident-commander decision and put it at the bottom on its own.

### 6. Write the decision points as a table

Any step where the reader has to make a judgement call gets a table mapping observation to conclusion to next step. A tired reader can match a row; they cannot reason from first principles.

| Observation | Conclusion | Next step |
| --- | --- | --- |
| Errors began within 10 minutes of a deploy | The release is the cause until proven otherwise | Mitigation 1, roll back |
| Errors across all replicas, latency to the database above 500ms | The dependency, not this service | Page the database on-call; do not restart |
| One replica erroring, the rest healthy | That instance or its node | Mitigation 4 on that pod only |
| Errors began at a round hour with no deploy | A scheduled job or a certificate expiry | Check the job schedule, then the certificate expiry command in step 3 |
| Nothing correlates and the ratio is climbing | Unknown, and it is getting worse | Declare, escalate to the service owner, go to step 7 |

The last row matters as much as the others. A runbook that assumes one of its known causes always applies leaves the responder stuck when none of them do; give them an exit.

### 7. Write escalation by role, with a time bound

Name roles and rotas, not people. "Escalate to Priya" is correct for about eleven months. Write "escalate to the payments on-call rota, via the `payments-oncall` PagerDuty schedule" instead — the schedule survives the person leaving.

State the trigger for each escalation as a condition and a clock: no improvement 15 minutes after mitigation 1, or any suspicion of data loss, or any customer-visible impact past 30 minutes. An escalation with no time bound produces the two-hour solo debugging session that ends in an escalation anyway, with a colder trail.

### 8. Make every command copy-pasteable and safe

This is where runbooks do direct damage. The rules are narrow:

- **Real flags, real values.** The command as written should run. `kubectl rollout undo deploy/checkout-api -n payments`, not `kubectl rollout undo deploy/SERVICE -n NAMESPACE`.
- **One clearly marked substitution point.** Where a value genuinely varies, put it in a single block at the top of the runbook, marked as the one thing to set, and reference the variable everywhere else. Placeholders scattered through the body get pasted literally at 3am — and `kubectl delete pod your-pod-here` either errors harmlessly or, worse, matches something.
- **Read-only and mutating commands visually separated.** Different sections, and a comment on the first line of every mutating block saying what it changes. The reader must be able to tell at a glance which half of the page is safe.
- **No pipe into a shell, no unbounded loop, no bare `delete` without a selector.** A runbook is executed under time pressure by someone not reading closely.
- **Every command has an expected output.** Show a line or two of what success looks like. Without it the reader cannot tell whether the step worked, and "it printed something" becomes the pass criterion.

```bash
# --- SET THIS ONCE, at the top of the session ---
export NS=payments
export SVC=checkout-api

# --- Read-only ---
kubectl get deploy "$SVC" -n "$NS" -o wide
# Expect: READY 6/6. Anything less is the problem.

# --- Mutating: replaces the running version with the previous revision ---
kubectl rollout undo deploy/"$SVC" -n "$NS"
kubectl rollout status deploy/"$SVC" -n "$NS" --timeout=180s
# Expect: "deployment "checkout-api" successfully rolled out" within ~90s.
```

### 9. Stamp it with an owner and a last-verified date

Both go in the document, at the top, visible without scrolling. The owner is a team or rota; the date is the last time someone proved the steps still work, not the last time someone edited a typo.

A runbook whose last-verified date is fourteen months old still tells the responder something useful: treat every command in it with suspicion. That is a far better outcome than silent confidence in a stale document. `references/maintenance.md` covers how verification actually happens and what to do when a runbook fails during a real incident.

### 10. Automate the step that is always the same

A step that is mechanical, has no judgement in it, and has been executed the same way twenty times is a script waiting to be written. Every manual repetition of it is an opportunity to typo a namespace at 3am.

The test is whether the step has a decision in it. "Check whether the queue depth is above 10,000 and if so scale the consumers" has a decision and stays in the runbook. "Run these four commands to collect the evidence bundle" has none, and should become one command that the runbook calls. Hand the script off to `code-scaffold` — it produces something with strict error handling, validated inputs and a dry-run mode, which is what you want for a script that only ever runs during an outage.

Automating the whole runbook is a different and much larger claim: an automated remediation that fires unattended needs its own guard rails and its own way to be switched off. Automate steps first.

## Where the runbook lives

Three properties, and each one has failed a real incident:

- **Reachable when the system it documents is down.** A runbook hosted on the cluster it describes, or in a wiki behind an SSO provider that depends on the failing service, is unavailable exactly when it is needed. Prefer the source repository plus a rendered mirror on independent infrastructure, and keep an offline export for the total-loss case.
- **Linked from the alert itself.** The `runbook_url` annotation is the only navigation path the responder has at 3am. A runbook nobody can find from the page is a runbook nobody reads.
- **Findable by symptom, not by internal service name.** The responder searches for "checkout timeouts" or "queue not draining", not for `svc-txn-router-v2`. Title by symptom, and list the alert names and error strings the reader would actually paste into a search box.

## Output format

Produce the runbook itself in this shape. `references/template.md` has the full fill-in version with a worked example.

```markdown
# Runbook: [symptom, in the words someone would search for]

**Owner:** [team or rota] · **Last verified:** [YYYY-MM-DD, by whom, how]
**Alerts:** [alert names that link here] · **Severity:** [expected]

## What this means
[One sentence about users. Then whether customer comms are likely needed.]

## 1. Confirm it is real
[One read-only check. What real looks like, what a monitoring artefact looks like.]

## 2. Scope and severity
[Read-only commands, and the threshold that decides whether to declare.]

## 3. Capture before changing anything
[The commands whose output the fix destroys, and where to paste it.]

## 4. Decide
[The observation to conclusion to next step table, including the "nothing matches" row.]

## 5. Mitigations, least destructive first
[Each with what it does, its blast radius, and how to undo it.]

## 6. Escalate
[Role or rota, the condition and the clock that triggers each escalation.]

## 7. After
[What to revert, and the postmortem trigger.]

## Background
[Links only. Architecture, dashboards, design docs. Below every step, deliberately.]
```

## Anti-patterns

**Prose instead of steps.** Three paragraphs describing what the responder should broadly consider. Under pressure, prose is skimmed, and skimmed prose loses the one conditional clause that mattered. Numbered steps with one action each.

**A command with a placeholder that gets run literally.** `kubectl delete pod POD_NAME -n NAMESPACE` gets pasted verbatim at 3am. Best case it errors and costs a minute; worst case a placeholder happens to be a real name. One marked substitution block at the top, variables everywhere else.

**A mitigation with no stated blast radius.** "Restart the service" says nothing about the in-flight requests it drops, the cache it cold-starts, or the ninety seconds of elevated latency that follows. This is how a mitigation becomes a second, larger incident, and it is the single most expensive omission in this document.

**No last-verified date.** The reader cannot distinguish a runbook confirmed last month from one written two years ago against a system that has since been rewritten. Both look equally authoritative, so both get trusted equally, and one of them is lying.

**A runbook that explains the architecture.** Every paragraph of background in front of step 1 is read during the outage, at the cost of minutes. It is also the section most likely to be out of date, because architecture drifts faster than commands. Link it from the bottom.

**Escalating to a named person who has left.** The responder pages a deactivated account, gets no answer, assumes they are asleep, and waits twenty minutes before trying anything else. Roles and rota schedules survive staff changes; names do not.

**A link the reader cannot open during the outage.** A dashboard behind the SSO that is down, a wiki hosted on the affected cluster, a document in a drive nobody on the rota has access to. Test every link from the on-call laptop, from outside the network, as a person who is not the author.

**Writing a runbook nobody will ever reach.** It exists, it is good, and no alert links to it and its title is the internal service codename. Wire the `runbook_url` at the same time you write it, and title it by the symptom.

## Reference files

- `references/template.md` — read when writing a new runbook: the complete fill-in skeleton with every section, plus a worked example for a checkout error-rate page showing the level of specificity the commands and the decision table need.
- `references/maintenance.md` — read when a runbook already exists: how to verify one during a game day rather than by reading it, the review cadence and the ownership record, what to do when a runbook fails mid-incident, and when to delete one outright.
