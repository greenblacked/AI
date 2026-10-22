---
name: switchback-test-design
description: "Design and analyse an experiment where units interact, so a user-level split is biased — marketplaces, dispatch, matching, pricing, shared inventory, ops queues: randomise time windows or regions instead of users, make each window longer than the effect's carryover after measuring it, balance arms within blocks of region and hour, drop a washout slice after each switch, size by simulating the schedule on history, and analyse at window level with block-clustered errors or randomisation inference, saying up front that units are fewer and noisier. Use when someone asks how to test a dispatch or surge algorithm, says drivers or stock are shared between arms, or mentions a switchback or geo test. Not for an ordinary user-level A/B test (experiment-design), a rollout ramp (release-strategy) or an effect nobody randomised (causal-inference-review)."
allowed-tools: Read, Write, Glob, Grep
---

# Switchback Test Design

The design is done when a schedule assigning arms to region-and-time windows exists before launch, with a window length justified by measured carryover, a washout rule, a power estimate from simulating that schedule on history, a window-level analysis plan, and a sentence telling stakeholders how many effective units the test has and how wide its interval will be.

The usual failure is running a user-level A/B test on a system where users share something. If treated riders get a better dispatch algorithm, they take drivers that control riders would have had; treatment looks better and control looks worse than either would at full rollout, so the measured difference overstates the effect, sometimes by more than the effect itself. The second failure is a switchback whose windows are shorter than the system's memory: queue lengths, driver positions and prices left over from the previous arm leak into the next window, and the test measures a blend.

## Scope

Use for: two-sided marketplaces (riders and drivers, buyers and sellers); dispatch, routing and matching algorithms; dynamic pricing; shared inventory or budget; operations queues where one item's handling changes another's wait; any case where treating one unit changes another's outcome.

Do not use for: a user-level A/B test where users do not share a constrained resource, which is `experiment-design`; choosing rollout percentages and bake times, which is `release-strategy`; estimating the effect of a change that was launched without randomisation, which is `causal-inference-review`; a split that came out wrong in a user-level test, which is `srm-diagnosis`.

This skill pre-approves no shell command. It reads serving logs, schedules and tickets, which other people wrote, and a pre-approved interpreter or `git` would let instructions planted there run without anyone agreeing to them. The Python, SQL and shell in this skill and its references run only when the user approves each command.

## Workflow

### 1. Name the interference and choose the unit

Write one sentence naming what the arms share: drivers in a city, warehouse stock, a price every buyer sees, an agent pool. That shared resource sets the boundary of a unit: everything that competes for it must get the same arm at the same moment.

| Situation | Unit | Why |
| --- | --- | --- |
| Effect clears within minutes to hours; many periods available | Time window within a region (switchback) | Many units, each region its own control over time |
| Effect persists for days (pricing that changes repeat behaviour, supply that relocates) | Region, held for the whole test (geo test), ideally matched pairs | Windows short enough for power would be contaminated |
| Few regions, short carryover | Region by time window | Uses both dimensions for more units |
| Regions interact (drivers cross boundaries) | Larger regions, or time windows across all regions together | The unit must contain the interference |

### 2. Measure the carryover

Find how long the system takes to settle after a change, from history: past deploys of the same component, configuration changes, outages, or a short pilot switching every few hours. Plot the outcome (wait time, match rate, queue length) against time since the switch and read where it levels off. That time is the carryover.

Window length must exceed the carryover, and the first part of every window, at least the carryover long, is a washout dropped from analysis. Add the switch mechanism's own propagation time — how long until every server serves the new arm — to the washout. If the carryover is a large share of a feasible window, move to region-level units.

### 3. Build a balanced schedule in blocks

Group windows into blocks that share conditions — a region and a day, or a region and a day-part — and randomise arms within each block so every block contains both arms equally often. Balance hour of day and day of week across arms: rush hour must not land mostly in one arm. Generate the whole schedule before launch from a recorded seed, store it, and treat it as the assignment log. Read `references/schedule-and-power.md` for a generator.

### 4. Size it by simulating the schedule on history

The sample size is the number of windows, not users. Take several past weeks of the outcome at window level, lay the planned schedule over them with no real treatment, estimate the "effect" exactly as the analysis will, and repeat across many random schedules. The standard deviation of those estimates is the standard error the design will deliver; at alpha 0.05 two-sided and power 0.8 the minimum detectable effect is about 2.8 times it. If that is larger than the effect worth detecting, lengthen the test, add regions, or reduce noise with block fixed effects and a pre-period covariate, before launch rather than after.

### 5. Implement the switch and the logging

Log, on every event, the window id and the arm actually in force when the event started, from the serving system itself rather than reconstructed from the schedule. Decide how to attribute events that span a switch (an order created in one window, completed in the next): by start time, with events starting in the washout excluded. Monitor realised against scheduled windows during the test; windows lost to outages are dropped from both arms' blocks, not filled later.

### 6. Write the analysis plan

Aggregate to one row per window: the outcome over the window after washout, the arm, the region, the block and the hour band. Estimate the effect as the difference between arms with block fixed effects, and compute the standard error clustered at a level that contains the windows whose outcomes are correlated (a region and its days, not the single window), or by randomisation inference: re-draw schedules with the same blocking many times, compute the estimate under each, and read the p-value as the share at least as extreme as the observed one. Randomisation inference stays valid with few units, where clustered standard errors computed from only a few dozen clusters or fewer tend to be too small. Read `references/window-level-estimation.md` for the queries and code.

Name the primary metric and guardrails at window level, and state that the estimate is the market-level effect — what happens when everyone gets the treatment — which is the one a user-level test could not give.

### 7. Set expectations before launch

Tell the owner, in the plan: the number of analysable windows, the expected interval width from step 4, the run length, and that the test measures the whole-system effect at the cost of being noisier and slower than a user-level test. A team that expects millions of units and gets a few hundred windows otherwise reads a wide interval as a failed test.

## Output format

```markdown
## Interference
[What is shared; why a user split is biased; direction of the bias.]

## Unit and schedule
[Unit, window length, blocks, balancing rule, seed, schedule location.]

## Carryover and washout
[How measured, the curve or numbers, washout length including propagation.]

## Power
[Windows, simulated standard error, minimum detectable effect, run length.]

## Analysis
[Window-level table, estimator, fixed effects, clustering or randomisation inference, metrics.]

## Expectations
[What the interval will look like and what the estimate means.]
```

## Anti-patterns

**User-level randomisation on a shared resource.** Treatment borrows from control and the difference overstates the rollout effect.

**Windows shorter than the carryover.** Each window measures the arm before it as much as its own.

**Analysing events as if independent.** Thousands of orders in a window are one unit; treating them as many gives intervals far too narrow.

**Sizing from user counts.** Power comes from windows and their variance. Simulate on history.

**Unbalanced time of day.** If treatment draws more rush hours, the test measures rush hour.

**Re-deriving the arm from the schedule.** The serving system's own record of what ran is the assignment; the schedule is what was intended.

## Reference files

- `references/schedule-and-power.md` — read at steps 2 to 4: measuring carryover from history, a blocked schedule generator, and the A/A simulation that gives the standard error and minimum detectable effect.
- `references/window-level-estimation.md` — read at step 6: the window aggregation query, the fixed-effects regression with clustered errors, and a randomisation-inference routine.
