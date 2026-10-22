---
name: activation-analysis
description: "Define activation from your own data and find where new users stall: cohorts by sign-up week, candidate early actions scored against week-8 retention, the winning event and threshold proven with a randomised nudge test, not declared from a correlation, each drop-off checked for tracking artefacts first, one testable hypothesis per drop-off, and a retention curve that must flatten before anyone calls the product retained. Use this skill whenever someone asks \"what is our aha moment\", \"define activation\", \"where do new users drop off in onboarding\", \"why don't trial users convert\" or \"which first-week action predicts retention\". Not for why paying customers cancel (churn-analysis), a sudden overnight move in a metric (metric-anomaly-triage), watching people use a prototype (usability-test-plan), or whether the problem is worth solving at all (problem-validation)."
allowed-tools: Read, Grep, Glob
---

# Activation Analysis

Activation analysis is done when the team has an activation definition (an action, a threshold and a time window) that was chosen from data, has been shown to cause retention by a randomised test rather than merely to accompany it, and a list of onboarding drop-offs each carrying one hypothesis and the test that would check it.

The usual failure is declaring an aha moment from a correlation. Users who invite a colleague in week one retain three times better, so the team builds an invite prompt, invites go up and retention does not move: the invite was something engaged users did, not what made them engaged. The second failure is optimising activation in a product whose retention curve never flattens. If almost everyone leaves eventually, there is no retained state to activate people into, and the work belongs to the product's core value, not its onboarding.

## Scope

Use for: defining activation for a product or a new feature; finding the early actions that predict retention; diagnosing where new or trial users stall in onboarding; deciding whether onboarding or the core product is the problem.

Do not use for: why established, paying customers cancel or shrink (`churn-analysis`); a sudden move in an activation number overnight (`metric-anomaly-triage`); observing people attempt tasks in a prototype (`usability-test-plan`); whether the underlying problem is real before anything is built (`problem-validation`); adding the missing events (`instrumentation`).

## Workflow

### 1. Define the retained state before the activation event

Activation means "the user has reached the state that predicts they will stay", so define staying first. Pick the product's natural use frequency (daily for messaging, weekly for most work tools, monthly for billing or reporting tools) and the action that counts as real use, not a login. A user is retained in week 8 if they did that action at least once in the eighth week after sign-up. For a monthly-use product, move the horizon out (month 3, for example) rather than forcing a weekly window onto it; the horizon must be long enough that the novelty of signing up has worn off.

Write the definition down before scoring any candidate event, so it cannot drift towards whichever event looks best.

### 2. Cohort by sign-up week and read the curves

Build weekly sign-up cohorts and plot, for each, the share retained in each week since sign-up. Read three things:

- **Does it flatten?** A curve that drops and then levels off at a non-zero share has a retained core. A curve still declining steadily at week 12 does not yet; say so plainly, because activation work cannot create a retained state the product does not offer.
- **Where is the steepest loss?** Usually the first one or two weeks. That is where activation lives.
- **Are newer cohorts better or worse?** A shift between cohorts points at a change in acquisition or in the product at that date.

`references/activation-queries.md` has the cohort query and the candidate-scoring query. Read it before writing either.

### 3. Check every drop-off for tracking artefacts first

Before explaining any funnel drop, check that it is not the measurement:

- The step event fires on every path: single sign-on, invited users, mobile and web, users who skip optional steps.
- The event was not introduced, renamed or moved between client and server during the period.
- Anonymous and signed-in identities are joined, so a user who signs up on one device and continues on another is not counted twice.
- Ad blockers and consent choices remove client-side events unevenly; compare against a server-side record of the same step where one exists.

A drop that disappears when measured from the production database was never a drop.

### 4. Score candidate early actions against retention

List 10 to 20 actions a user can take in the first days (create the first project, connect a data source, invite a colleague, complete a first export). For each action and a few thresholds (at least once, three times, on two separate days) within a fixed early window, usually the first 7 days, compute on older cohorts:

| Measure | Question it answers |
| --- | --- |
| Retention of users who did it, against those who did not | How strongly it separates stayers from leavers |
| Share of retained users who did it | Whether it describes most retained users or a niche |
| Share of all new users who did it | Whether there is room to move it |

Prefer the action and threshold that is both common among retained users and rare among those who left. An action only power users take separates well and covers few. Then check the choice on newer cohorts it was not chosen on; a winner that does not hold out of sample was noise.

### 5. Prove it causally with a nudge test

A correlation selects a candidate; it does not prove one. Design a randomised test that raises the rate of the candidate action for a random half of new users (a checklist step, a template that makes it one click, a prompt at the right moment) and changes nothing else. Write the primary metric (week-8 retention, or an earlier proxy agreed in advance), the minimum effect worth detecting and the sample size before launch, and hand the design to whoever runs experiments in your organisation.

Read the result in two parts. If the nudge raised the action and retention rose, the action is causal enough to call it activation. If the action rose and retention did not, the action was a marker of engaged users, not a cause; go back to step 4 with the next candidate. Until a test reads, call the definition provisional.

### 6. Write one hypothesis per drop-off

For each step where many new users stop, write one hypothesis in a testable form: "Users stop at connecting a data source because they do not have credentials to hand; if so, users who are offered a 'send to my admin' option will complete it more often." One hypothesis per drop-off keeps the test interpretable; three changes shipped together tell you nothing about which mattered. Rank drop-offs by the number of users lost multiplied by the retention gap between those who pass and those who stop.

## What to hand back

- The retained-state definition and the cohort retention curves, with a plain statement of whether they flatten.
- The candidate table with retention lift, coverage and reach, and the out-of-sample check.
- The activation definition (action, threshold, window) marked provisional or proven, with the test design or result.
- The drop-off list: step, users lost, tracking check result, one hypothesis, and the test for it.

## Anti-patterns

**The famous number.** Borrowing another company's activation threshold, or picking a round one, skips the only step that makes the definition yours.

**Correlation declared as cause.** The most predictive action is often what engaged people do anyway. Without the nudge test, the team optimises a symptom.

**Activation work on a curve that never flattens.** Faster onboarding into a product people leave anyway moves the drop by a week and nothing else.

**Explaining a drop that is a missing event.** A funnel step that only fires on web makes mobile look like it falls off a cliff.

**Several fixes at once.** A redesigned onboarding with five changes improves or worsens the number and teaches nothing about which change did it.

## Reference files

- `references/activation-queries.md` — read before writing queries: the sign-up cohort retention query, the candidate-action scoring query, the out-of-sample check, and a worked candidate table with how to read it.
