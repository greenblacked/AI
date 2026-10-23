---
name: saga-design
description: "Design or review a multi-step business process that spans services, databases or third parties without a distributed transaction. Persist the saga's own state in one row before step 1, classify each step as compensable, pivot or retriable-after-pivot and order them that way, make every compensation idempotent and semantic and safe when the forward step never ran or is still in flight, give every step a timeout that ends in a terminal state, and prove it by killing the coordinator at every state write. Use when you hear \"booking spans payment, inventory and shipping\", \"how do we roll back when step 3 fails\", \"design the compensation\", \"orders stuck in pending\", \"alternative to two-phase commit\". Not for outbox or inbox (event-driven-reliability), endpoint contracts (api-design), migrating systems (plan-platform-migration), schema changes (db-migration)."
allowed-tools: Read, Glob, Grep, Edit, Write
---

# Saga Design

Done means the process has a persisted state machine, every step is classified and ordered by how reversible it is, every compensation survives being run twice or out of order, and a test that kills the coordinator at every point ends in all-done or all-compensated. The usual failure is a happy-path chain of calls with a try/catch around it: the first crash between two calls leaves a charge with no reservation, and nothing in the system knows.

## 1. Write the saga's own state first

Before step 1 runs, insert one row: saga id, business key, current step, status, deadline, attempt counts, and the input needed to continue. Every transition is a single conditional update (`UPDATE ... SET step = $next WHERE id = $id AND step = $current`), so two workers resuming the same saga cannot both advance it. Without this row there is nothing to resume, nothing to compensate from and nothing to query when it sticks.

Statuses worth having: `running`, `compensating`, `completed`, `compensated`, `failed_needs_human`. The last three are terminal.

## 2. Classify every step

| Class | Meaning | Examples |
| --- | --- | --- |
| Compensable | Has a semantic undo | Reserve stock, hold a seat, authorise a card |
| Pivot | Point of no return; once it succeeds the saga commits forward | Charge captured, ticket issued, goods shipped |
| Retriable after pivot | Cannot be undone, but can be retried until it succeeds | Send receipt, update loyalty points, notify warehouse |

Read `references/step-classification.md` for how to classify an awkward step and a worked ordering.

## 3. Order the steps

1. Compensable steps first.
2. The pivot is the first irreversible step. Steps most likely to fail permanently go before it, as compensable steps or as the pivot itself, so a failure happens while everything before it can still be undone.
3. Only retriable steps after the pivot, retried with backoff until they succeed or reach `failed_needs_human`.

If a step after the pivot can fail permanently, it was misclassified: either it belongs before the pivot or the business needs a manual path.

## 4. Design each compensation

- **Idempotent.** Key it by saga id and step. Running it twice has the effect of running it once.
- **Semantic, not a delete.** Refund, void, release the hold, issue a credit note. The history of what happened stays visible and auditable.
- **Safe when the forward step never ran or is still in flight.** Record cancellation intent first (`step_x_cancelled = true` on the saga row, or a tombstone keyed by saga id on the participant). A forward request that arrives later checks it and is refused. Without this, a timed-out request that finally lands after its compensation ran leaves an orphan.
- **Not blocked by a failed forward.** A compensation that needs the forward result to exist must read the remote first and treat "not found" as success.

## 5. Make intermediate states visible

State what the world looks like between steps and show it honestly: `pending` with a deadline, `reserved` rather than `sold`, `payment_authorised` rather than `paid`. Users and downstream code then never act on a state that may still be rolled back. Reads that need a settled answer filter on terminal states.

## 6. Timeouts, stuck sagas and unknown outcomes

- Every step has a timeout that ends in a terminal state, not a wait.
- Stuck sagas are a query with an owner: status not terminal and `updated_at` older than the step's deadline. Run it on a schedule, page on the oldest age, and name the team that owns each saga type.
- When a call times out, the remote outcome is unknown. Read the remote (by the idempotency key you sent) before compensating anything; compensating a charge that did land, or retrying one that did, are both corruptions. Idempotency keys and retry budgets are the job of `timeout-and-retry-budget`.

## 7. Orchestration or choreography

Use a durable orchestrator (a workflow engine or a table-driven coordinator whose state survives restarts) when there are more than three participants, when compensation order matters, or when someone needs to ask what state an order is in. Use choreography, each service reacting to events, only for short linear flows where no one needs a global view. Choreography beyond that hides the state machine in the interactions between services, which is where stuck sagas go to be unfindable. Delivering the commands and events reliably is the outbox's job (`event-driven-reliability`).

## 8. Test by killing it

Read `references/failure-injection.md` for the harness. The gate:

1. Kill the coordinator after every state write and between every pair of remote calls; restart; the saga resumes.
2. Inject a failure at every step, once as an error and once as a timeout whose request later succeeds.
3. Run each compensation twice and out of order.
4. The end state of every run is all-done or all-compensated, with no orphaned reservation, charge or message. Assert it by querying each participant, not by reading the saga row.

## Hand back

The state machine (states, transitions, deadlines), the classified and ordered step table, each compensation with its idempotency key and its behaviour when the forward step did not run, the stuck-saga query with its owner, orchestrator or choreography with the reason, and the kill-point test results.

## Anti-patterns

**Compensating by deleting.** It erases the evidence and cannot be run safely twice; use a counter-entry.

**Treating a timeout as a failure.** The remote may have succeeded. Reconcile first.

**Putting the riskiest step last, after irreversible ones.** That is what turns a routine decline into a manual refund queue.

**A saga with no row of its own.** Its state lives in the call stack and dies with the process.
