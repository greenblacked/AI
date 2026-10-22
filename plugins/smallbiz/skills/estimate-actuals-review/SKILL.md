---
name: estimate-actuals-review
description: "Measure how wrong your estimates are and correct them. At every project close, log one row per task type (estimated hours, tracked hours, ratio); after 8-10 projects take the median ratio per task type, not the mean, and apply it as a personal multiplier in fixed-price-quote. Split overruns into underestimated work, unpaid client-added scope and your own rework, each with its own fix. Report effective hourly rate (fee over all tracked hours, including unbilled email and calls, net of subcontract cost). Gate: no project is closed until its row is logged. Use for 'my quotes are always too low', 'I keep running over budget', 'how do I get better at estimating', 'project finished, was it profitable'. Not for the forward estimate (fixed-price-quote), incident reviews (postmortem), team delivery metrics (delivery-review) or per-client rates (client-profitability-review)."
allowed-tools: Read, Glob, Grep
---

# Estimate Actuals Review

A finished review has one logged row per task type for every closed project, a median ratio per task type once enough projects exist, the overrun split into its three causes, and an effective hourly rate for the project just closed.

The usual failure is remembering estimates as better than they were. Without a record, an overrun is blamed on the client or bad luck, and the next quote repeats the same optimism. A log turns a feeling into a number you can multiply by.

## Scope

Use for: closing a fixed-price or capped project, calibrating future estimates, and judging whether a finished job paid.

Do not use for: the forward-looking estimate itself (`fixed-price-quote`), engineering incident reviews (`postmortem`), team delivery metrics (`delivery-review`) or the same rate aggregated per client each quarter (`client-profitability-review`).

## Workflow

### 1. Track time against task types from the start

Estimates can only be compared with actuals if both use the same buckets. Use a short, stable list of task types that match how you quote (for example discovery, design, build, content, testing, project management, revisions). Track every hour against one, including client email, calls and admin, which are the hours most often missing. If time was not tracked, reconstruct from calendar and messages and mark the row as reconstructed; do not use reconstructed rows for the multiplier.

### 2. Gate: log the row before closing

No project is marked closed, and its final invoice is not treated as the end of the job, until its rows are in the log. Do it the week of delivery, while the numbers are still fresh. Columns and a worked example are in `references/log-and-multiplier.md`.

One row per task type, whether it ran over or not: project, task type, estimated hours, tracked hours, client-added hours, rework hours, ratio ((tracked minus client-added minus rework) divided by estimated), reconstructed yes or no. A task type with no estimate (unplanned work) is logged separately as a missing estimate and has no ratio.

### 3. Split every overrun into a cause

Overrun hours on a task type belong to one of three buckets. The fix differs, so lumping them hides the lesson.

| Bucket | Meaning | Fix |
| --- | --- | --- |
| Underestimated work | The task was in scope and took longer than you said | The multiplier in step 4 |
| Client-added scope | Unpaid extras, extra revision rounds, late changes | Change-order discipline: see `scope-creep-response`, and tighten the scope document |
| Own rework | You redid something because of mistakes or a misread brief | A quality check before delivery and a clearer brief at the start |

Only the first bucket should feed the multiplier, which is why the ratio strips the other two out. Feeding it client-added scope inflates your quotes for a problem a change order solves.

### 4. Compute the multiplier after 8 to 10 projects

For each task type, take the median of the ratios across every non-reconstructed row, including tasks that came in on or under estimate, so the multiplier can fall below 1.0 where you over-estimate. Client-added and rework hours are already removed from the ratio. Use the median, not the mean: one disaster project skews a mean, and the point is the typical error. Publish the result as a personal multiplier table, for example "build 1.4, content 1.25, project management 1.6", and apply it to the raw estimate in `fixed-price-quote`. With fewer than 8 projects, apply nothing automatic; use the table as a warning and add a stated buffer. Recompute every 5 closed projects and watch whether the ratios fall toward 1.0, which means the estimating is improving.

A task type with fewer than 3 data points has no multiplier of its own; use the overall median until it does.

### 5. Report the effective hourly rate

Per project: effective rate = fee / tracked hours, where tracked hours include all unbilled email, calls and rework. Where you subcontracted, use fee minus subcontract cost over your own tracked hours, and note the subcontract margin separately (fee charged for that work minus cost paid). Compare the effective rate with the target from `billing-rate-calculation`. A project that "went fine" at half your target rate is a loss that never showed up on an invoice.

### 6. Decide one change

After each review, write one concrete change: a new multiplier, a scope clause, a delivery checklist item, or a decision not to take this kind of project at that price. A review with no decision is bookkeeping.

## What to hand back

```text
Project: [name] - fee [amount] - tracked hours [n]
Rows logged: [task type - est - tracked - client-added - rework - ratio]
Effective rate: [amount/hour] against target [amount/hour]
Overrun split: underestimated [h], client-added [h], rework [h]
Multiplier table: [task type - median ratio - n projects] or "not enough data (n of 8)"
Change decided: [one line]
```

## Anti-patterns

- **Using the mean.** One disaster dominates it; the median shows the usual miss.
- **Letting client scope into the multiplier.** It makes quotes dearer for a problem a change order fixes.
- **Leaving out unbilled hours.** Email and calls are the most common reason a profitable-looking job was not.
- **Closing before logging.** The row never gets written once the next project starts.
- **Trusting reconstructed time.** Mark it and keep it out of the multiplier.

## Reference files

- `references/log-and-multiplier.md` - read at steps 2, 4 and 5: the log layout, a worked median calculation and the effective-rate formula with a subcontract example.
