---
name: headcount-case
description: "Build the written case for headcount, a budget increase or a backfill that a finance partner or executive will approve. Opens with the ask in one line (roles, level, loaded cost over 12 and 24 months, date) and the decision required, prices the cost of not hiring from the team's own data, beats two cheaper alternatives, shows ramp honestly (benefit lands after the start date), answers objections with figures, names what would stop if declined, and sets a two-quarter success metric, every number marked measured, estimated or assumed. Use for \"I need to justify two more engineers\", \"finance wants a business case for the hire\", \"should we backfill this role\", \"how do I ask for budget\". Not for buying a tool (vendor-evaluation), pay bands (compensation-benchmarking), progress reports (status-update), goal setting (okr-planning), or funding a platform investment (tech-debt-case)."
allowed-tools: Read, Grep, Glob
---

# Headcount Case

A headcount case is done when a finance partner or executive can approve, defer or decline it from one page, and every figure on that page carries a source or is labelled as a guess. The output is a short document: the ask, the cost of not hiring, the alternatives that lose, the ramp, and the measure that will show the hire worked.

The usual failure is a case built on feeling: the team is stretched, morale is low, we are behind. All of that may be true and none of it is a number a budget owner can weigh against another team's request. The second failure is the flattering timeline, where a hire starting in March is counted as capacity in March. A new engineer costs the team capacity for the first three to six months, because someone has to onboard them, and the benefit arrives after the spend. A case that hides this is found out at the first review and loses the credibility of every other figure in it.

## Scope

Use for: a new role, a team expansion, a backfill of a departed role, a contractor-to-permanent conversion, and a budget increase that is mostly people cost.

Do not use for: choosing and buying a tool (`vendor-evaluation`), setting pay bands or an offer (`compensation-benchmarking`), reporting on work in flight (`status-update`), setting goals the headcount would serve (`okr-planning`), or arguing for time to pay down a platform (`tech-debt-case`).

## Workflow

### 1. Write the ask first

Before any evidence, write one line: how many roles, which level and function, the fully loaded cost over 12 and 24 months, and the date the person is needed. Then write the decision the reader must make and by when ("approve two engineers in the Q1 plan by 15 November"). If you cannot write this line, the case is not ready, and the evidence gathering will wander.

Fully loaded means salary or band midpoint, bonus and equity at the company's usual accrual, payroll taxes and benefits, recruiting cost (agency fee or internal recruiter time), equipment and software seats, and the ramp cost in step 4. Ask the finance partner for their loading factor rather than inventing one; it is usually a multiplier on base pay. `references/cost-model.md` has the layout.

### 2. Price the cost of not hiring

This is the section that decides the outcome, and it must come from the team's own data, not from industry averages. Gather three things.

- **Committed work that will not ship.** List the roadmap items already promised, their estimated effort in engineer-weeks, and the capacity available. The gap is the queue that slips. Name each slipped item and what is attached to it: revenue, a contract date, a regulatory deadline, a customer.
- **Absorbed load.** Hours per month already spent on incidents, on-call, support escalations and manual toil, from the ticket system, the pager history and timesheets where they exist. Convert to engineer-equivalents (a rough month of focused capacity is 100 to 120 hours; state your figure).
- **Risk carried.** A single owner of a critical system, an unstaffed on-call rotation, an audit finding. State the exposure as probability times impact where you can, and as a plain statement where you cannot.

Mark each figure measured, estimated or assumed, and give the source (query, dashboard, document). A table of three columns, figure, label and source, is enough.

### 3. Beat at least two cheaper alternatives

A reader will think of the alternatives within a minute; the case is stronger when it has already lost to them on the record. Cover each of these and say what it would cost and why it falls short:

- **Reprioritise.** Which committed items could be dropped, and what does dropping them cost? If the answer is that nothing can be dropped, show the ranking that proves it.
- **Contract or agency.** Cost per month against permanent, the knowledge that walks out at the end, and the onboarding drag that repeats.
- **Tool or automation.** The toil hours it would remove, its cost and its build time. Be honest where it covers part of the gap; a partial win belongs in the case.
- **Stop a project.** Name the one you would stop. This also feeds step 6.

An alternative that wins is a good result: the case becomes a smaller ask or a different one.

### 4. Show the ramp honestly

Draw the capacity curve, not a single date. Assume the hire starts at the requested date after realistic time to hire (state the time-to-fill for this role from recent data, not the hope), contributes little in the first month, consumes mentor time through months one to three, and reaches full productivity at a point you state, commonly three to six months and longer for a complex domain. Show net capacity of the team, which dips before it rises. Give two dates: the start date and the date the benefit exceeds the cost.

For a backfill, add the vacancy gap: the months between departure and the replacement being productive, and the knowledge already lost. A backfill is not free just because the budget line exists; the case is that the line is still needed at its current level.

### 5. Answer the objections with figures

Write the four or five objections this reader will raise and answer each with a number or a source. The standing ones are: why not wait a quarter (the cost of delay per month from step 2), why this level (what the work requires, and the cost difference of the level below), why not offshore or contract, why not fix the process first, and what happens to the headcount if the project ends. If an objection has no good answer, say so and say what you would do about it. A concealed weakness found by the reader reflects on the whole case.

### 6. Name the trade-off if declined

Say what you would stop, delay or accept if the answer is no: the projects slipping, the on-call changes, the risk left open. This is not a threat; it is the information the reader needs to see that declining is a decision with a cost. Offer a smaller version of the ask (one role instead of two, a later start) where one exists.

### 7. Set the success metric

Pick one or two metrics that will show the hire worked within two quarters of the start date, measured the same way as in step 2: the queue cleared, toil hours reduced, lead time, incident load. Give the baseline, the target and the date of the check. Commit to reporting them whether or not they were met.

## Output format

```markdown
## Headcount case: [team], [roles]

**Ask.** [N roles, level, 12 and 24 month loaded cost, needed by date.]
**Decision needed.** [What, from whom, by when.]

### Cost of not hiring
[Table: figure, measured / estimated / assumed, source.]

### Alternatives considered
[Reprioritise, contract, tool, stop a project: cost and why each falls short.]

### Ramp and benefit date
[Start date, net capacity curve, date benefit exceeds cost.]

### Objections
[Each with a figure.]

### If declined
[What stops, what slips, the smaller alternative.]

### Success measure
[Metric, baseline, target, check date.]
```

## Anti-patterns

**Feelings as evidence.** "The team is burnt out" is a reason for you and not a figure for them. Convert it into absorbed hours, attrition cost or missed dates.

**Capacity from day one.** Counting the hire as full capacity at the start date overstates the benefit and is the first thing a finance partner checks.

**One option presented.** A case with no alternatives reads as an assumption that hiring is the answer. Show the options that lost.

**Unlabelled numbers.** An estimate that looks like a measurement is found out once and discredits the rest. Label each figure.

**Padding the ask to survive negotiation.** A reviewer who cuts it by a third finds you have both the cut and the credibility problem. Ask for what the evidence supports.

**No exit.** A case with no metric and no check date cannot be repeated next year, because nobody will know whether the last hire worked.

## Reference files

- `references/cost-model.md` read when pricing the ask: the fully loaded cost layout over 12 and 24 months, the ramp curve arithmetic, and a worked example for one engineer.
- `references/case-template.md` read when drafting the document: a one-page template with the evidence table, the alternatives grid and a list of the objections that recur.
