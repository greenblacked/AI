# The runbook template, and a worked example

## Contents

- The fill-in skeleton
- Notes on the sections people get wrong
- Worked example: checkout error-rate page

## The fill-in skeleton

Copy this whole block, replace every bracketed span, and delete any section that
genuinely does not apply — an empty heading reads as an unanswered question during an
incident. Keep the order: it is the order the responder acts in.

```markdown
# Runbook: [the symptom, phrased the way someone would search for it]

**Owner:** [team or rota, not a person]
**Last verified:** [YYYY-MM-DD] by [rota] during [game day / drill / real incident]
**Alerts that link here:** [AlertName, AlertName]
**Expected severity:** [SEV2 if customer-visible, SEV3 otherwise — say which]
**Customer comms likely:** [yes / no]

## Set these once

    export NS=[namespace]
    export SVC=[service]

[The single substitution point. Every command below uses these variables.]

## What this means

[One sentence. Who is having a worse time and what they cannot do.]
[One sentence on what is unaffected, so the responder does not over-declare.]

## 1. Confirm it is real

[One read-only command or dashboard link.]

- [Value or output that means the problem is real] -- continue to step 2.
- [Value or output that means the telemetry is broken] -- go to [the telemetry runbook].
- [Value or output that means it has already cleared] -- record and stop.

## 2. Scope and severity

[Two or three read-only commands.]

[The threshold that decides whether to declare an incident, stated as a number.]

## 3. Capture before changing anything

[The commands whose output the fix destroys. Where to paste the output.]

## 4. Decide

| Observation | Conclusion | Next step |
| --- | --- | --- |
| [signal] | [cause] | [which mitigation] |
| Nothing above matches | Unknown cause | Escalate, step 6 |

## 5. Mitigations, least destructive first

### 5.1 [Name]

[What it does.]
**Blast radius:** [what it disrupts, for whom, for how long]
**Undo:** [the exact command or procedure]

    [command]
    # Expect: [what success prints]

[Repeat per mitigation, in increasing order of destructiveness. Mark any irreversible
one as requiring an explicit incident-commander decision.]

## 6. Escalate

| Condition | Escalate to | How |
| --- | --- | --- |
| [condition and clock] | [rota] | [schedule or channel] |

## 7. After

[Anything temporary that must be reverted, with the command.]
[The condition under which this becomes a postmortem.]

## Background

[Links only: architecture, dashboards, design docs, the service's own README.]
```

## Notes on the sections people get wrong

**"What this means" is not the alert expression.** Restating the query tells the
responder nothing they did not get from the page. Write the customer sentence.

**"Confirm it is real" has to be able to say no.** If every branch of the confirmation
step leads to "continue", it is not a confirmation step. The false-page branch is the
one that saves the most time over a year.

**The capture step is between diagnosis and mitigation, not at the end.** Placed at the
end it is read after the evidence is gone.

**Blast radius is per mitigation, not a paragraph at the top.** The responder reads one
mitigation, not the document. Whatever is not next to the command does not exist.

**The escalation table needs a clock in every row.** "If it gets worse" is not a
trigger; "no improvement 15 minutes after 5.1" is.

## Worked example: checkout error-rate page

This is the level of specificity to aim for. Note that every command runs as written,
every mutation states its blast radius, and no step requires knowing how checkout works.

```markdown
# Runbook: checkout returning 5xx to customers

**Owner:** payments-oncall
**Last verified:** 2026-08-14 by payments-oncall during the Q3 failover game day
**Alerts that link here:** CheckoutErrorBudgetFastBurn, CheckoutErrorBudgetSlowBurn
**Expected severity:** SEV2
**Customer comms likely:** yes, if above 5% for more than 10 minutes

## Set these once

    export NS=payments
    export SVC=checkout-api

## What this means

Customers are getting errors when they try to pay. Some fraction of purchase attempts
are failing outright; the money is not taken, so this is lost revenue rather than a
reconciliation problem. Browsing, search and account pages are unaffected.

## 1. Confirm it is real

Open the checkout overview dashboard, panel "5xx ratio, 5m":
https://grafana.internal/d/checkout/overview

- Ratio above 0.01 for two consecutive evaluations: real. Continue to step 2.
- Panel shows "No data": the exporter is down, not checkout. Go to the
  checkout-no-telemetry runbook and stop here.
- Ratio below 0.001: already recovered. Note the times in the alert thread and stop.

## 2. Scope and severity

    kubectl get deploy "$SVC" -n "$NS" -o wide
    # Expect: READY 6/6. Fewer ready replicas is itself the problem.

    kubectl get pods -n "$NS" -l app=checkout-api -o wide
    # Look at NODE: all failures on one node points at the node, not the app.

Declare a SEV2 and name an incident commander if the ratio is above 0.05, or if any
single tenant is at 100% errors, or if it has been above 0.01 for 10 minutes.

## 3. Capture before changing anything

Every command below is read-only. Paste the output into the incident document; the
rollback in 5.1 destroys all three.

    kubectl logs -n "$NS" -l app=checkout-api --tail=200 --prefix > /tmp/checkout-logs.txt
    kubectl get events -n "$NS" --sort-by=.metadata.creationTimestamp | tail -40
    kubectl describe deploy "$SVC" -n "$NS" | sed -n '1,60p'

## 4. Decide

| Observation | Conclusion | Next step |
| --- | --- | --- |
| A rollout finished within 10 minutes of the first alert | The release | 5.1, roll back |
| Logs show "context deadline exceeded" calling ledger-api | The dependency | Page ledger-oncall. Do not roll back; it will not help |
| One pod erroring, five healthy | That instance | 5.4, restart that pod only |
| Errors started at a round hour, no deploy | Scheduled job or certificate | Check the nightly reconciliation job, then cert expiry |
| Nothing above matches | Unknown, and climbing | Escalate, step 6 |

## 5. Mitigations, least destructive first

### 5.1 Roll back to the previous release

Serves new requests from the previous known-good version.
**Blast radius:** in-flight requests are unaffected; the rollout is gradual over ~90s.
Any feature shipped in the current release disappears for customers.
**Undo:** roll forward with the fixed image once it is built.

    kubectl rollout undo deploy/"$SVC" -n "$NS"
    kubectl rollout status deploy/"$SVC" -n "$NS" --timeout=180s
    # Expect: deployment "checkout-api" successfully rolled out

Then re-check the dashboard from step 1. Pod readiness is not the success criterion —
the 5xx ratio is.

### 5.2 Scale out to 12 replicas

Use when the errors are timeouts under load rather than a bad release.
**Blast radius:** cost only, if the cluster has capacity. If it does not, the new pods
sit Pending and nothing improves.
**Undo:** scale back to 6.

    kubectl scale deploy/"$SVC" -n "$NS" --replicas=12
    # Expect: deployment.apps/checkout-api scaled

### 5.3 Disable the recommendations feature flag

Removes the slowest call from the checkout path.
**Blast radius:** every customer loses product recommendations on the checkout page.
No restart, no dropped requests.
**Undo:** re-enable the flag in the same console.

Set checkout.recommendations to false at https://flags.internal/checkout

### 5.4 Restart one pod

Last resort for a single bad instance.
**Blast radius:** drops that pod's in-flight requests — roughly 40 requests — and starts
cold, so its latency is elevated for about 90 seconds.
**Undo:** nothing to undo, but the pod's logs and state are gone. Do step 3 first.

    kubectl delete pod "$POD" -n "$NS"
    # Expect: the Deployment recreates it within seconds.

## 6. Escalate

| Condition | Escalate to | How |
| --- | --- | --- |
| No improvement 15 minutes after 5.1 | payments engineering lead | payments-oncall schedule |
| Logs point at ledger-api or the database | ledger-oncall | ledger-oncall schedule |
| Any suspicion of double-charging or lost orders | payments lead and finance duty | payments-oncall, then the finance-duty rota |
| Customer impact past 30 minutes | incident commander decides on comms | See incident-comms |

## 7. After

Re-enable anything disabled in 5.3 and scale back from 5.2 once the SLI has been normal
for 30 minutes. A rollback under 5.1 needs a roll-forward plan before the next release.

Any occurrence above SEV3 gets a postmortem with an owner within 24 hours.

## Background

- Checkout architecture: https://wiki.internal/payments/checkout-architecture
- Dependency map: https://wiki.internal/payments/dependencies
- SLO definition: https://wiki.internal/payments/slo
```
