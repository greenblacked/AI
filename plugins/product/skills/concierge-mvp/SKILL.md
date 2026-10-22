---
name: concierge-mvp
description: "Deliver a product's outcome by hand to the first five to ten customers before automating anything, and let what happens decide what gets built. Log every manual step with the time it took and the customer's reaction, so the log becomes the spec; automate only a step that has run ten or more times and costs over fifteen minutes; track the cost of serving each customer by hand; stop when customers do not come back unprompted, because automating a service nobody repeats only makes the failure cheaper to run. Use when a team wants to validate before building the workflow, do things that don't scale, run a manual or concierge pilot, or decide which manual steps to automate first. Not for measuring demand before anyone is served (fake-door-test), co-designing with a cohort of partner companies (design-partner-program), or a game concept's go or no-go (game-greenlight)."
allowed-tools: Read, Glob, Grep
---

# Concierge MVP

Done means five to ten customers in one segment have been served by hand for long enough to see whether they come back on their own, every manual step is in a log with its duration and the customer's reaction, the cost of serving each customer is known, and the next step — automate named steps, keep going by hand, or stop — follows from rules written at the start.

The usual failure is automating too early. The team serves three customers by hand, finds it tedious, and starts building the pipeline, choosing which steps to automate by how annoying they were rather than how often they recur or whether customers valued them. The automated version then encodes guesses. The other failure is never stopping: a concierge service customers tolerate but never ask for again can run for months, because each week feels like progress.

## Scope

Use for: delivering a service manually to a first small cohort; deciding which steps to automate and in what order; deciding whether to continue at all.

Do not use for: measuring demand before anyone is served, which is `fake-door-test`; running a structured programme of partner companies who co-design the product and give feedback on builds, which is `design-partner-program`; deciding whether a game concept goes ahead, which is `game-greenlight`; writing the specification for the automated version, which is `feature-spec` once the log exists.

## Workflow

### 1. Write the promise, the cycle and the exit rule first

Before serving anyone, write:

- **The promise**: the outcome the customer gets, in their terms. "Your month-end reconciliation, done and checked, by the third working day."
- **The natural cycle**: how often the job recurs for this customer. Weekly, monthly, per project. Repeat usage can only be judged against it.
- **The exit rule**: stop if customers do not come back unprompted within two cycles of their first delivery. Unprompted means the customer initiates the next request without a reminder or a nudge from you.
- **The time box**: a fixed end date for the concierge phase, long enough for the last customer recruited to pass two natural cycles after their first delivery, since the exit rule cannot be judged sooner.

Write these down and date them. A rule written after the first disappointing month always finds a reason to continue.

### 2. Recruit five to ten customers in one segment, and charge

Take them from the responders to a demand test, from problem interviews, or from existing users with the job. Keep them in one segment so the log describes one process rather than several averaged together.

Charge something from the first delivery, even at a discount. Payment is the cleanest test of value, and free customers give polite feedback. Tell customers that people, not software, are doing the work. Pretending a human service is automated (a Wizard of Oz test) is a different method with its own consent and data questions; do not drift into it by default.

### 3. Deliver with the least tooling that works

Use spreadsheets, shared documents, email and calendar holds. Write code only when a step cannot be done by hand at all. Every tool you build now is a guess about the process before the log exists.

Customer data handled by people is still customer data: agree in writing what you will access and keep, store it in a controlled place, restrict who can see it, and delete what you do not need when the phase ends. Data-protection rules vary by jurisdiction, so check them; this is procedure, not legal advice.

### 4. Log every step the same day

Each time anyone does anything for a customer, add a row: date, customer, step name, what triggered it, who did it, minutes spent, inputs needed from the customer, what went wrong or had to be redone, and the customer's reaction in their words. Use a fixed verb-noun step name ("match bank lines", "chase missing receipts") so the same step can be counted across customers.

Log on the day. A log reconstructed at the end of the week loses the redo, the five-minute chase and the throwaway remark that explains what the customer actually valued. The template is in `references/step-log.md`.

### 5. Track cost and repeat usage per customer

For each customer, keep running totals: hours, cost (hours at a loaded rate plus any tools), revenue, and the dates of each unprompted request. Cost per customer falling over time shows the process is being learned; cost flat or rising with every new customer shows the process does not standardise and may never automate cheaply.

### 6. Review weekly and pick automation candidates by rule

Roll the log up by step: runs, median minutes, total minutes, redo rate, and the reactions recorded against it. A step is a candidate for automation only when it has run ten or more times and its median run costs over fifteen minutes. Below ten runs you do not yet know the step's variations; below fifteen minutes the saving rarely pays for the code and its upkeep.

Order candidates by total minutes, highest first. Then read the reactions:

| What the log shows | Action |
| --- | --- |
| Customers notice and praise the step | This is the product; automate it carefully and keep its quality |
| Nobody notices the step | Try removing it before automating it |
| The step is mostly redo or chasing | Fix the input or the hand-off before automating |
| The step varies every time | Keep it manual and log more runs |

The roll-up and the rule are spelled out in `references/step-log.md`.

### 7. Decide at the time box

Apply the rules written in step 1:

1. **Stop** if most customers did not come back unprompted within two cycles. Automating a service nobody repeats only makes the failure cheaper to run. Tell customers, finish their current delivery, and write down what you learned.
2. **Continue by hand** if customers are repeating but no step has met the automation rule yet.
3. **Automate** the steps that met the rule, in the order from step 6, while the rest stay manual.

Each automated step is specified from the log: its inputs, outputs, the variations recorded and the failures seen. Hand that to `feature-spec`.

## Output

```markdown
## Rules (written [date])
[Promise, natural cycle, exit rule, time box.]

## Cohort
[Customers by id, segment, start date, price paid.]

## Repeat usage
[Per customer: deliveries, unprompted requests, dates.]

## Cost
[Per customer: hours, cost, revenue; trend across the cohort.]

## Step roll-up
[Per step: runs, median minutes, total minutes, redo rate, typical reaction.]

## Decision
[Stop, continue by hand, or automate named steps, with the rule each follows.]
```

## Anti-patterns

**Automating the annoying step.** Annoyance is not frequency or value. Use the counts and the reactions.

**Free pilots.** Customers who pay nothing will say it is useful and never return. Charge from the start.

**Five segments in one cohort.** Each segment runs a different process, so no step reaches ten comparable runs. Keep to one.

**Nudging repeat usage.** A reminder that produces a second request measures the reminder. Count only unprompted requests.

## Reference files

- `references/step-log.md` — read before the first delivery and at each weekly review: the log columns, the per-customer cost sheet, the weekly roll-up, and the automation and exit rules in table form.
