---
name: delivery-review
description: "Assess the delivery health of a team or programme and say what to change — DORA metrics read the way they were defined, flow and capacity reality, prioritisation frameworks matched to the decision actually being made, and OKRs graded as designed. Produces a ranked findings report with impact and effort per finding, what to change first, and what to stop doing. Use this skill whenever someone asks how a team is doing on delivery, why shipping feels slow, whether a roadmap is realistic, how to prioritise a backlog or rank competing items, which framework applies (RICE, ICE, WSJF, cost of delay), or how to write and grade OKRs — including phrasings like \"we keep missing dates\", \"is this team healthy\", or \"help me rank these\". Do not use it to assess an individual engineer's performance, which these metrics do not support, or to write up an incident."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(gh:*), Bash(git:*)
---

# Delivery Review

A good delivery review names a small number of changes the team can make, each tied to evidence the reader can check, and is equally clear about what to stop.

The job is hard because the output is prose and prose is cheap. It is trivially easy to write a review that sounds authoritative — "cycle time is elevated, dependencies are a concern, recommend tighter WIP limits" — and is unfalsifiable, un-actionable, and would read identically for any team on earth. Two disciplines prevent that. First, interrogate the human for evidence before writing anything: every claim in the review traces to a number, an artefact, or a named observation. Second, where a number was not supplied, write `[TK: metric]` and say where it would come from. A missing measurement is a finding in its own right; smoothing over it produces a review that cannot be argued with and therefore cannot be used.

## Scope

Use for: assessing a team's or programme's delivery health, diagnosing why delivery feels slow, sanity-checking a plan against capacity, choosing and applying a prioritisation framework, ranking a backlog, setting or grading OKRs, and preparing a delivery report for leadership.

Do not use for: individual performance review or comparison between engineers — DORA and flow metrics measure the delivery system, and using them per-person reliably produces gaming rather than improvement. Also not for incident analysis, and not as a substitute for talking to the team.

## Workflow

### 1. Establish what is actually being asked

Three quite different requests hide under "review our delivery": a health assessment (how are we doing), a diagnosis (why is this slow), or a decision (what should we do next, in what order). Name which one before gathering data, because they need different evidence and produce different outputs.

Then establish the unit of analysis — a team, a programme spanning teams, a single value stream — and the period under review. A review with no period is not comparable to anything.

### 2. Gather evidence, and mark what is missing

Ask for these in one batch, with sources. Anything not supplied becomes `[TK: metric]` in the output, never an estimate.

- Deployment frequency, lead time for changes, change failure rate, failed deployment recovery time, rework rate — with the definitions the team currently uses, which are often not DORA's.
- Cycle time distribution: not the mean. Median, 85th and 95th percentile.
- Current WIP per person and per team; count of blocked items and their age.
- The last two planning periods: committed versus delivered, and what displaced the difference.
- Unplanned work as a share of capacity — on-call, support escalations, keep-the-lights-on.
- Cross-team dependencies with a date on the critical path.
- The current OKRs or goals, and how they were graded last period.

### 3. Read the DORA metrics correctly

The 2024 set, with the definitions that matter:

| Metric | Definition | Common misreading |
| --- | --- | --- |
| Deployment frequency | How often code reaches production | Treated as a target; splitting commits raises it while changing nothing |
| Lead time for changes | Commit to running in production | Measured from ticket creation, which is a different (also useful) number |
| Change failure rate | Share of production deployments causing degraded service that needs a hotfix, rollback or patch. Elite around 5%, low performers around 40% | Confused with CI failure rate |
| Failed deployment recovery time | Time to restore service after a failed deployment. DORA renamed MTTR in 2024 specifically to exclude failures not caused by a change | Still reported as MTTR, quietly including provider outages and capacity incidents |
| Rework rate | Share of deployments that are unplanned bug-fix deployments | Ignored, though it is often the clearest signal of quality debt |

Two warnings to carry into every review. DORA measures the delivery system, not individuals — a per-engineer DORA dashboard converts a diagnostic instrument into a performance ranking, and the rational response is to game it. And CI redness is not change failure rate: a red build is the system working, a change failure is the system failing in production. Putting the two on one dashboard teaches people to optimise the wrong one, usually by weakening the tests.

Read the metrics as a set. High deployment frequency with a rising change failure rate is not throughput, it is instability. Low change failure rate with quarterly deploys is not quality, it is batching risk into rare, large releases.

### 4. Examine flow

Throughput metrics say how fast the pipe runs. Flow says where the work sits.

- **Work in progress.** Unlimited WIP is the most common root cause of long cycle time and the cheapest to fix. Ask for a count, not an impression.
- **Cycle time distribution, not its mean.** The mean hides the tail, and the tail is where the pain, the escalations and the missed commitments live. Report median with 85th and 95th percentile; a wide gap between median and p95 is a predictability problem, which is usually more damaging than a slow median.
- **Queue time versus touch time.** Most items spend the large majority of their life waiting — for review, for a dependency, for an environment, for a decision. Reducing touch time when queue time dominates is effort spent in the wrong place.
- **Blocked-work ageing.** Track the age of blocked items, not just the count. An item blocked for three weeks is a different problem from five blocked yesterday.
- **Dependency risk.** For each cross-team dependency on the critical path: who owns it, what their queue looks like, and what the plan is if it slips. A dependency with no named owner is a date with no owner.
- **Capacity reality.** A plan assuming 100% project capacity fails in week three, every time. Reserve 40-50% for keep-the-lights-on, on-call, support and unplanned work, then plan against what remains. If the team's actual unplanned share is known, use it; if not, mark it `[TK: unplanned work share, from the last two sprints]` and treat the plan as unvalidated.

### 5. Classify the decision before reaching for a framework

This ordering rule matters more than any individual framework, and skipping it is why prioritisation exercises consume weeks and change nothing.

| Situation | Approach |
| --- | --- |
| Reversible and cheap | Just do it. No framework, no score, no meeting |
| Irreversible or expensive | A decision record: options, the call, why, what would reverse it |
| Many similar items competing for one queue | This — and only this — is what the scoring frameworks are for |

Then pick the framework by what the decision needs, not by habit. Full scoring mechanics, worked examples and failure modes are in `references/prioritisation.md`; read it before scoring anything.

- **RICE** = (Reach × Impact × Confidence) / Effort. Reach must be a real number over a real period from a real dashboard — this is where RICE dies in practice, when Reach becomes a guess. Impact uses 3 / 2 / 1 / 0.5 / 0.25; Confidence 100 / 80 / 50%. Below 50% confidence, stop scoring and go and learn something instead. Effort in person-months.
- **ICE** = Impact × Confidence × Ease, each 1-10. Fast and coarse, and highly gameable because one person can move the ranking by a point per column. Score blind in a group, then discuss only the outliers.
- **Cost of Delay** — the economic loss per unit time of not having the thing, expressed in currency per week. The only one of these that answers "why not just do them all", because it makes the cost of the queue visible. **CD3** = Cost of Delay ÷ Duration gives optimal sequencing for independent items sharing one queue.
- **WSJF** = Cost of Delay ÷ Job Size, where CoD = user-business value + time criticality + risk reduction or opportunity enablement. Score relatively on modified Fibonacci and anchor each column by setting its smallest item to 1.

Every prioritised item ships with a **kill criterion**: the metric that says it worked, and the threshold or date at which you stop and revert. Most teams skip this, which is how a roadmap accumulates items nobody can cancel because nobody agreed in advance what failure would look like.

### 6. Check the goals

Cover OKRs when the team has them or is about to adopt them. The essentials, with the reasoning and the common failures in `references/okrs.md`:

- 3-5 objectives, each with 3-5 key results. More than that is a backlog wearing a costume.
- Graded 0.0-1.0, with 0.6-0.7 as the healthy target for aspirational goals. Consistent 1.0s mean the targets were set to be safe.
- **Never tied to compensation or performance review.** Tying them produces sandbagging, then reliable 1.0 scores, and the system stops carrying information. This is the single failure that kills OKRs outright.
- Transparent across the org, so dependencies between teams surface before the quarter starts.
- The discriminator: a key result achievable by doing an activity is a task, not a key result. "Ship the new pipeline" is a task; "median lead time under 2 days for 80% of services" is a key result.
- Separate committed OKRs (expected to land at 1.0) from aspirational ones (expected around 0.7). Grading them on one scale makes both meaningless.
- Track health metrics alongside — the things that must not break while pursuing the objective. They belong beside the key results, not as key results.

### 7. Rank the findings and say what to stop

Each finding gets evidence, impact and effort. Ranking is by impact-over-effort with sequencing constraints applied, not by which finding was easiest to write.

The "stop doing" section is mandatory and is the part most reviews omit. A review that only adds work has added work. Look specifically for: metrics collected and never used, ceremonies with no decision output, WIP that exists only because nothing was ever cancelled, and reports produced for an audience that stopped reading.

## Output format

```markdown
## Verdict
[Three sentences. Health of the delivery system, the single largest constraint,
and the one change that would move it most.]

## Evidence base
[Table: metric | value | source | period. Every unsupplied metric appears here
as [TK: metric] with where it would come from. This table is the review's
foundation — a review resting mostly on [TK:] rows says so in the verdict.]

## Findings, ranked
[Per finding: what is happening | evidence | consequence if unchanged |
impact (high/med/low) | effort (S/M/L) | recommended change | owner]

## Change first
[One to three items, with why these and why now, and what they unblock.]

## Stop doing
[Explicit list. Each with what it currently costs and what is freed by stopping.]

## Measurement gaps
[What could not be assessed, why it matters, and the cheapest way to start
measuring it.]
```

## Anti-patterns

**Metrics without a period or a source.** "Cycle time is 6 days" is unfalsifiable and unimprovable. Every number carries a window and an origin.

**DORA per engineer.** Converts a system diagnostic into a performance ranking. The team learns to split commits and defer risky work, and the metrics improve while delivery does not.

**Change failure rate and CI failure rate on one dashboard.** They measure opposite things. Combining them pressures people to weaken the tests, which raises the metric that actually matters.

**Reporting the mean cycle time.** The mean is the one summary statistic that hides the tail, and the tail is the reason anyone asked for the review.

**Scoring a decision that did not need scoring.** A reversible, cheap change put through RICE costs more in meeting time than the change itself.

**Reach invented rather than measured.** RICE with a guessed Reach is a ranking of confidence in one's own guesses, presented as arithmetic.

**Prioritised items with no kill criterion.** Nothing ever leaves the roadmap, so capacity is consumed by things whose case has already collapsed.

**OKRs wired to compensation.** Targets get sandbagged within one cycle and the grades stop meaning anything.

**Planning against 100% capacity.** The plan breaks in week three and the team spends the rest of the quarter explaining variance instead of delivering.

**A review with no "stop doing" section.** Adding recommendations to a team already over WIP makes the diagnosed problem worse.

## Reference files

- `references/prioritisation.md` — RICE, ICE, Cost of Delay, CD3 and WSJF in full: scoring scales, worked examples, anchoring, and how each is gamed. Read before scoring or ranking anything.
- `references/okrs.md` — writing, grading, committed versus aspirational, health metrics, and the failure modes. Read when the review touches goal-setting.
