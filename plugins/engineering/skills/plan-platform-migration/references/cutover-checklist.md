# Cutover Checklist

Copy this checklist for every rehearsal and production wave. Replace every bracketed field
before the go/no-go decision.

## Contents

- [Change identity](#change-identity)
- [Preconditions](#preconditions)
- [Invariants and abort thresholds](#invariants-and-abort-thresholds)
- [Go/no-go](#gono-go)
- [Execution](#execution)
- [Verification](#verification)
- [Rollback](#rollback)
- [Communication](#communication)
- [Wave close](#wave-close)
- [Retirement gate](#retirement-gate)

## Change identity

- Migration: [name]
- Wave and cohort: [exact membership]
- Window: [start/end with timezone]
- Incident/change channel: [location]
- Decision log: [location]
- Change owner: [name]
- Go/no-go owner: [one name]
- Operations executor: [one name]
- Observers: [names and dashboards]
- Next communication time: [timestamp]

## Preconditions

- [ ] Scope and cohort resolve to the expected objects.
- [ ] Source and target versions or digests are recorded.
- [ ] Current backup or snapshot completed and restore was previously rehearsed.
- [ ] Replication/backfill lag is below [threshold].
- [ ] Reconciliation mismatch is below [threshold] using [query].
- [ ] Capacity headroom is at least [threshold] on source, target and shared dependencies.
- [ ] Alerts and dashboards cover the user path, not only component health.
- [ ] Support and dependency owners acknowledged the window.
- [ ] No conflicting deployment, maintenance or incident is active.
- [ ] Rollback commands were executed successfully in rehearsal [link/date].
- [ ] Point of no return is named: [event].

## Invariants and abort thresholds

| Invariant | Signal | Baseline | Abort threshold | Observer |
| --- | --- | --- | --- | --- |
| [availability] | [dashboard/query] | [value] | [value/duration] | [name] |
| [correctness] | [reconciliation] | [value] | [value/duration] | [name] |
| [latency] | [dashboard/query] | [value] | [value/duration] | [name] |
| [operations] | [pages/tickets] | [value] | [value/duration] | [name] |

An abort threshold is automatic unless the checklist names the person allowed to override
it and the evidence required. Silence is not approval.

## Go/no-go

- Decision: [go / no-go]
- Time: [timestamp]
- Evidence reviewed: [links]
- Exceptions accepted: [none or named exception, owner, expiry]
- Next decision time: [timestamp]

## Execution

Run one line at a time. Record start, end, operator, output location, and whether it changed
state.

| # | Action or command | Expected result | Actual result | Time/operator |
| --- | --- | --- | --- | --- |
| 1 | [command] | [observable result] | | |
| 2 | [command] | [observable result] | | |

Do not improvise a new mutation into this table during cutover. Pause, review it as a new
decision, and record why the existing plan was insufficient.

## Verification

- [ ] Synthetic user path succeeds from outside the platform boundary.
- [ ] Real cohort traffic reaches the intended target.
- [ ] Error rate and latency remain within thresholds for [duration].
- [ ] Writes are authoritative in the documented system.
- [ ] Replication, queues and reconciliation are within thresholds.
- [ ] Authentication, authorization and audit records are correct.
- [ ] Deployment and rollback paths still function.
- [ ] Support sees no unexplained increase in contacts.

## Rollback

- Triggered by: [signal/decision]
- Decision owner: [name]
- Last safe rollback time or event: [point]
- Data consequence: [none / replay / reconcile / accepted loss]
- If loss is accepted: [quantified scope, named approver, approval record]

| # | Rollback action | Expected result | Verification |
| --- | --- | --- | --- |
| 1 | [command] | [result] | [query/dashboard] |
| 2 | [command] | [result] | [query/dashboard] |

After rollback, keep the incident/change channel open until source behavior and every
invariant return to baseline. Preserve target evidence for diagnosis.

## Communication

Use this shape at start, decision points, rollback, and completion:

```text
Migration: [name], wave [n]
State: [preflight / executing / observing / rolled back / complete]
Exposure: [cohort or percentage]
Invariants: [green / named threshold missed]
Decision: [continue / hold / roll back]
Next update: [time]
```

## Wave close

- [ ] Observation window completed.
- [ ] Exit criteria met or exception recorded with owner and expiry.
- [ ] Unexpected findings added to the next wave's checklist.
- [ ] Temporary access, flags and capacity recorded for removal.
- [ ] Next cohort and earliest start approved.

## Retirement gate

- [ ] No supported caller uses the old path.
- [ ] Old writes have been disabled for the agreed quiet period.
- [ ] Retention, audit, legal hold and restore obligations are met.
- [ ] DNS, credentials, jobs, alerts, dashboards and runbooks are removed or redirected.
- [ ] Cost and ownership have transferred.
- [ ] Irreversible deletion has a named approver and recovery statement.
