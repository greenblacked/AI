---
name: vendor-evaluation
description: "Run a buy decision to a defensible conclusion, including the decision not to buy: start from a written requirement and the current cost of the problem, do an honest build-versus-buy that counts three years of operating cost, agree scorecard weights before any demo, run a time-boxed proof of concept against real data with pass criteria written first, model three-year total cost of ownership rather than list price, run security and legal in parallel from week one, price the exit, and ship a recommendation memo. Use this skill whenever someone is choosing or comparing vendors, tools or platforms, asks whether to build or buy, wants a scorecard, a PoC plan, a TCO model, reference-call questions or negotiation leverage, or says things like \"which of these three should we pick\", \"is this worth the money\", or \"the renewal is in six weeks\". Do not use it for a technical choice with no purchase, procurement paperwork, hiring, or auditing a contract already signed."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Vendor Evaluation

A good evaluation ends with a decision someone can defend a year later: the requirement stated in a number, the winner, the runner-up and the specific reason it lost, the three-year cost, and what would change the answer. Deciding not to buy is one of the legitimate endings.

The job is hard because the process is almost always run backwards. Someone sees a demo, likes it, and the evaluation that follows is the search for reasons — criteria written to match the tool that has already won, weights tuned until the arithmetic agrees, a proof of concept run by the person who wants it to succeed. Vendors are good at this; their demo environment has clean data, the integration is pre-built, and the feature you will need in month four is on the roadmap. Meanwhile the numbers that decide whether this was a good purchase — the metric you cannot control, the renewal uplift, the cost of getting your data back out — are the ones nobody asks about while there is still leverage to ask. The sequencing rules below exist to make each of those failures visible while they are still cheap.

## Scope

Use for: choosing between SaaS products, platforms or managed services; a build-versus-buy decision; a renewal where switching is genuinely on the table; consolidating overlapping tools; designing a proof of concept or a scorecard; building a TCO model; preparing reference calls or a negotiation; writing the recommendation memo.

Do not use for: a technical or architectural choice with nothing to purchase — that is the `decision-record` skill; raising purchase orders and chasing procurement paperwork; hiring decisions; or reading an already-signed contract when no decision is pending.

## Sequencing rules

These are ordering constraints, not preferences. Each one is unrecoverable if you take it out of order.

1. **The requirement is written before the shortlist.** Otherwise the shortlist defines the requirement, which is how you end up buying a platform to solve a problem you never measured.
2. **Weights are agreed, written down and dated before the first demo.** Weights set afterwards are a rationalisation of the vendor you liked, and everyone in the room can tell.
3. **PoC pass criteria are written before the trial starts**, and every finalist runs the same script.
4. **Security and legal review start in week one, in parallel.** Started at signature, they are either a rubber stamp or a very expensive surprise.
5. **The exit is priced during the sales process**, while the vendor still wants something from you.
6. **Cost is three-year total cost of ownership**, never list price.

## Workflow

### 1. Write the requirement

Before any vendor is contacted, answer five things in writing. If they cannot be answered, the evaluation is premature and saying so is the correct output.

- **The problem**, in a sentence that names who has it.
- **Its current cost**, as a number: engineer-hours per month, incidents per quarter, revenue at risk, an audit finding with a deadline. If nobody can quantify it, ask what happens if this is still true in a year. An unquantified problem cannot justify any price, which means the evaluation has no floor.
- **What success looks like**, in a number with a date. "Mean time to detect under ten minutes by Q2" is a requirement. "Better observability" is a mood.
- **Constraints** that are genuinely binding: data residency, an existing contract, a compliance deadline, a headcount ceiling, the language your team actually writes.
- **Non-goals.** The adjacent problems this purchase is not solving. This is what stops a tool being bought to solve four problems and doing none of them well.

Separate hard requirements from strong preferences before scoring anything. A hard requirement is a disqualifier, and treating it as a heavily-weighted criterion instead lets a vendor score well overall while failing something you cannot live without.

If the purchase is an observability, alerting or on-call product, write the requirement against the alerting design you actually want rather than a feature list — the `alert-design` skill covers what that design looks like, and it will change which product wins.

### 2. Build versus buy, honestly

The build option is always on the table and is usually estimated dishonestly, because the estimate stops at first release.

| Cost | Build | Buy |
| --- | --- | --- |
| Initial | Engineer-months to first useful version, times the loaded rate | Implementation and integration effort |
| Run, per year | On-call, upgrades, dependency churn, capacity, the incidents it causes | Subscription, plus the internal owner's time |
| Opportunity | What the team did not build instead — usually the actual product | Lower, but not zero |
| Exit | None; you own it forever, including after its author leaves | Migration cost, which you should price now |
| Fit | Exact, and stays exact only while someone maintains it | Approximate, improves without your effort |

Build wins when the capability is genuinely differentiating, when the requirement is narrow enough that a small tool beats a platform, or when no product fits a binding constraint. Buy wins for undifferentiated infrastructure, for anything with a compliance surface you would rather someone else maintained, and whenever the honest three-year run cost exceeds the licence.

A build estimate that ignores three years of operating cost is not an estimate, and neither is one that assumes the person who builds it will still be on the team. Write both numbers down, including the do-nothing option, which is free and is sometimes right.

### 3. Agree the weights before any demo

Eight criteria cover most purchases. Weight them for this decision, sum to 100, and have the decision-maker sign the list with a date on it.

| Criterion | What it means | Typical weight |
| --- | --- | --- |
| Requirement fit | Does it solve the stated problem, measured against the success number | 25 |
| Operability | Day-two reality: upgrades, noise, who gets paged, how it fails | 15 |
| Security and compliance posture | Certifications with a scope you have read, not a logo | 10 |
| Data ownership and export | Whose data it is and how you get it back | 10 |
| Integration surface | Does it fit the systems you already run, without a bespoke bridge | 10 |
| Support model | Response times in the contract, escalation path, who answers at 2am | 10 |
| Roadmap and viability | Funding, customer base, whether the feature you need is real or promised | 10 |
| Total cost of ownership | The three-year number from step 6 | 10 |

Score each criterion 1, 3 or 5 against a written anchor — not 1 to 10, which invites a spread of 6s and 7s that means nothing. `references/scorecard.md` has the anchors, the worked example, and the rules for handling a tie.

Two disciplines make the scorecard honest. Weights change only in writing, once, with a stated reason, and never after a demo. And every score carries a one-line justification naming its evidence, so a reader can audit the arithmetic. A scorecard with no evidence column is a gut call wearing a table.

### 4. Disqualify cheaply, before the shortlist

Kill on paper what you can. An hour of reading beats a week of trial.

Common early disqualifiers: SSO or SCIM only on a tier you have not budgeted for; audit logs behind a separate paywall; no data residency in a region you are contractually bound to; a pricing metric you cannot control or forecast; no bulk export API; a sub-processor list that includes something your customers have already objected to; a single-region architecture when you have an availability requirement.

Aim to reach two or three finalists. Evaluating five properly costs more than the difference between the top two, and evaluating five badly is worse than evaluating two well.

### 5. Design the proof of concept

A demo is a sales artefact. A PoC is evidence, and only if it is designed as an experiment rather than a trial period.

- **Time-boxed** — two to three weeks, with an end date that does not move.
- **Real data**, or the closest thing your legal review permits. A vendor's sample dataset tells you about the vendor's sample dataset.
- **Your two hardest requirements**, not the ten easy ones. The easy ones all pass; they carry no information.
- **Pass criteria written and circulated before access is granted**, phrased so the result is not arguable: a number, a threshold, or a task completed within a stated time by a named person.
- **The same script for every finalist**, run by the same people. A PoC run once per vendor by whoever likes that vendor produces a ranking of enthusiasm.
- **Not run solely by the champion.** Have someone who is sceptical, and someone who will actually operate it, run the script too. If only the champion can make it work, that is a finding about the product.
- **Include the day-two tasks**: an upgrade, an on-call scenario, an intentional failure, adding a user, revoking a user, exporting the data.
- **Write the result per criterion as it happens**, not from memory at the end.

Where the product runs inside your infrastructure, its container images and Terraform modules are yours to review before the PoC gets production data — `image-hardening` and `iac-review` cover that.

### 6. Model three-year total cost of ownership

List price is the smallest number the vendor will show you. Model the rest.

| Line | The question to ask |
| --- | --- |
| Pricing metric | What are you actually billed for: seats, hosts, ingested volume, events, spans, API calls |
| Growth curve | Apply your own projected growth to that metric, not the vendor's example |
| The metric you cannot control | If billing tracks log volume or event count, a bad deploy is a bill. Ask for a cap or an alert |
| Overage behaviour | Blocked, throttled, or billed at a premium rate, and at what notice |
| Committed spend | Discount in exchange for a floor you must hit whether or not you use it |
| Implementation | Vendor professional services plus your own engineer-weeks |
| Integration | The connectors nobody counted: SSO, provisioning, ticketing, data warehouse |
| Training and change | Two hours per person is a real number when there are 200 people |
| Run cost | Your internal owner, the infrastructure it needs, the alerts it generates |
| Renewal uplift | Ask for the cap now. Uncapped renewal is the standard way a cheap year one becomes an expensive year three |
| Exit cost | What it costs to leave, in engineer-weeks and in dual-running months |

Compare the three-year totals side by side, including the do-nothing and build options. Where a number is unknown, write it as unknown rather than estimating it into the model — a false precision in a cost model is worse than a visible gap, because nobody re-examines it later.

### 7. Security, legal and data review, in parallel

Start these in week one and run them alongside the PoC. They kill deals, and the cheapest time to be killed is early.

- **Certification scope.** A SOC 2 Type II report is evidence about specified systems over a specified period. Read which systems, which period, and the exceptions section — a report covering the marketing site is not a report covering the product. For ISO 27001, read the statement of applicability.
- **Sub-processors.** Who else touches the data, in which countries, and how much notice you get before that list changes.
- **Data residency and retention.** Where it is stored and processed, how long it is kept, and what deletion actually means and how long it takes.
- **The DPA**, breach notification window in hours, and whether the notification obligation is to you or merely to a regulator.
- **Security features that are not on the paid tier you chose**: SSO, SCIM, audit-log export, IP allow-listing, role granularity. Price the tier you actually need, not the one in the quote.
- **Incident and pen-test history.** Ask for the last penetration test summary and for their last incident. A vendor that has never had an incident either has not been running long or is not telling you.
- **Business continuity**: their RTO and RPO, and what your options are if they are down for a day.

`references/diligence.md` holds the full question bank, the SOC 2 reading guide, and the reference-call script.

### 8. Reference calls you sourced yourself

The three references a vendor supplies are their three happiest customers. Take them, then find two of your own through your network, a community, or the vendor's own public customer list.

Ask questions that resist a rehearsed answer: what surprised you three to six months in; what does support look like at 2am on a Sunday; what did you have to build yourself; what does the upgrade path feel like; what do you wish you had negotiated; what would make you leave; what is your actual bill against your first quote. Ask about scale relative to yours — a happy customer a tenth your size is not evidence about your workload.

### 9. Negotiate, then price the exit

Leverage exists only before signature, so spend it on the terms that will hurt later rather than only on the headline discount.

- Ask for a cap on renewal uplift in writing, and for price protection on the metric that scales.
- Multi-year commitments buy a discount and cost you flexibility. They are worth it when the requirement is stable and the switching cost is already high; they are a trap when the market is moving.
- Quarter-end and year-end give you real leverage on price and very little on terms. Do not let their calendar set your decision date.
- Ramped pricing beats a full-year commitment for a product whose adoption is uncertain.
- Get the export commitment into the contract: format, completeness, and how long they will provide it after termination.
- Establish termination rights, and what happens to your data on termination.

Then write down what leaving costs — how the data comes out, in what format, how long it takes, what breaks, and who would do the work. Ask the vendor to describe it while they are still selling. A vendor who cannot answer clearly has told you something important about the exit.

### 10. Write the recommendation

Lead with the decision. The memo below is the deliverable; hand the durable version to the `decision-record` skill, which turns it into an ADR with the rejected options and the confirmation mechanism intact. If the purchase displaces an incumbent, the switch is a migration with a rollback point, not a licence change — plan it with the `cutover` skill.

## Output format

```markdown
## Recommendation
[Buy X / build / do nothing. One sentence. The decision needed and by when.]

## The problem and what success looks like
[The requirement in a number, and its current cost.]

## Runner-up and why it lost
[Name it and give the specific criterion. "Close on fit, lost on export and a 3x
three-year cost at our growth rate" — not "less mature".]

## Cost
[Three-year TCO per option, with the pricing metric and the assumed growth rate stated.
Unknowns marked as unknown.]

## Evidence
[PoC results against the pass criteria written beforehand. Reference calls, including who
you sourced yourself. Security review status.]

## Risks and mitigations
[Concentration, lock-in, the uncontrolled metric, viability. What was negotiated against
each.]

## Exit
[How we leave, what it costs, what is in the contract about it.]

## What would change this answer
[The specific fact that would flip the decision, and when we would next look.]
```

## Anti-patterns

**Weights set after the demo.** The single most common way an evaluation becomes theatre. The arithmetic then confirms the intuition, and everyone involved knows it, so the scorecard convinces nobody while costing three weeks. If it is a judgement call, write "this was a judgement call, based on the following experience" — that is defensible; a rigged matrix is not.

**Comparing list prices.** The cheaper list price routinely loses on three-year total cost once the pricing metric, overage and renewal uplift are modelled. Comparing list prices is comparing the number the vendor chose to make comparable.

**The PoC only the champion ran.** It proves the champion can operate the product, which was never in question. The people who will be on call for it need to run the same script, or you have measured enthusiasm.

**Security review at signature.** Either it is a rubber stamp, which means it is not a review, or it kills a deal after three months of work and a committed start date. Both outcomes are caused by the timing, not by the security team.

**No exit plan.** Discovered at renewal, when the cost of leaving is the vendor's negotiating position rather than yours. Price the exit before you sign, when the answer is still cheap to obtain.

**Evaluating three vendors before defining the requirement.** Produces a comparison of feature lists, since without a requirement there is nothing to weight. The tell is a scorecard where every criterion is a feature and none is an outcome.

**Buying a platform for a problem you have not measured.** The purchase is justified by the size of the tool rather than the size of the problem, and nobody can say afterwards whether it worked. If the problem has no number, get the number first.

## Reference files

- `references/scorecard.md` — read when building or reviewing the scorecard: criterion definitions, the 1/3/5 scoring anchors, a fully worked example with weights, tie-breaking, and the TCO model line by line.
- `references/diligence.md` — read when running the parallel security, legal and reference track: the vendor question bank, how to read a SOC 2 report's scope, the DPA and exit-clause checklist, the reference-call script, and the PoC test-plan template.
