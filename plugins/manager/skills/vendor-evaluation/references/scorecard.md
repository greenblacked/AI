# Scorecard and cost model

The mechanics behind steps 3 and 6 of the workflow: what each criterion means, how to score
it without inventing precision, a worked example, and the three-year cost model line by
line.

## Contents

- [Criterion definitions](#criterion-definitions)
- [Scoring anchors](#scoring-anchors)
- [A worked scorecard](#a-worked-scorecard)
- [Hard requirements are not criteria](#hard-requirements-are-not-criteria)
- [Reading the result, and ties](#reading-the-result-and-ties)
- [The three-year cost model](#the-three-year-cost-model)
- [Sensitivity: the two numbers to flex](#sensitivity-the-two-numbers-to-flex)

## Criterion definitions

Write these definitions into the scorecard before scoring. Half of all scoring
disagreements are two people using one word for two things.

**Requirement fit.** Does it move the success metric from step 1, evidenced by the PoC
rather than by the feature matrix. Score the requirement as written, not the requirement as
the demo reframed it.

**Operability.** What day two costs. Who installs upgrades and how often; whether it
generates alerts and who receives them; what it does when a dependency is slow; how much
configuration lives outside version control; whether one person becomes the only operator.
This is the criterion most often scored from the demo, where it is invisible.

**Security and compliance posture.** Certifications whose scope you have read, the tier the
security features actually sit on, sub-processors, and incident history. Not the badge row
on the pricing page.

**Data ownership and export.** Whose data it is under the contract, whether there is a
complete bulk export in a documented format, how long an export takes at your volume, and
whether historical data comes with it. Test the export during the PoC — this criterion is
routinely scored from a documentation page that describes an API nobody has called.

**Integration surface.** How it connects to what you already run: identity, ticketing, chat,
the data warehouse, your CI. Count the connectors you would have to build and maintain
yourself, and score those as ongoing cost rather than a one-off.

**Support model.** Response and resolution targets in the contract rather than on the
website, escalation path, whether support is 24/7 or business hours in a timezone that is
not yours, and whether the tier you are buying includes a named contact.

**Roadmap and viability.** Funding stage and runway, customer count and churn signals,
release cadence over the last year, and whether the feature you are relying on exists
today. Score anything promised for a future release as absent — if the decision depends on
it, make it a contract commitment instead.

**Total cost of ownership.** The three-year number from the model below, scored relative to
the alternatives rather than absolutely.

## Scoring anchors

Score 1, 3 or 5. A ten-point scale produces a cluster of 6s and 7s that encodes nothing but
politeness, and it makes small weight changes flip the ranking.

| Score | Meaning |
| --- | --- |
| 5 | Meets the criterion with evidence from the PoC or a document we read. No work required from us. |
| 3 | Meets it with a workaround, an extra tier, or engineering we have scoped and costed. |
| 1 | Does not meet it, or we could not verify it. Unverified scores as 1, which is what makes vendors produce evidence. |

Every score carries a one-line justification naming the evidence: a PoC result, a contract
clause, a reference call, a document. A score with no evidence line is removed from the
total, not defended.

Scoring "unverified" as 1 is deliberate. The alternative — a blank, or a charitable middle
score — quietly rewards the vendor who answered least.

## A worked scorecard

Three finalists for an on-call and incident-response tool. Weights agreed and dated before
the first demo.

| Criterion | Weight | A | B | C |
| --- | --- | --- | --- | --- |
| Requirement fit | 25 | 5 | 5 | 3 |
| Operability | 15 | 3 | 5 | 3 |
| Security and compliance | 10 | 5 | 3 | 5 |
| Data ownership and export | 10 | 1 | 5 | 3 |
| Integration surface | 10 | 5 | 3 | 3 |
| Support model | 10 | 3 | 3 | 5 |
| Roadmap and viability | 10 | 5 | 3 | 1 |
| Total cost of ownership | 10 | 3 | 5 | 5 |
| **Weighted total** | **100** | **390** | **430** | **340** |

Read it as a document, not as a ranking. B wins, and the memo should say why in one line:
comparable fit to A, better on day-two operability and export, and a lower three-year cost
despite a higher list price. A lost on export — score 1, evidenced by a PoC attempt that
produced a partial CSV with no history — which is a criterion the team weighted at only 10
but which drives the exit cost. That is worth a sentence in the memo rather than being
buried in the arithmetic.

Note what the table does not do: it does not decide. A 40-point gap on a 1000-point scale
is noise, and the honest response to two vendors within a few percent is to pick on the
grounds that are hardest to quantify — usually operability or the reference calls — and say
so plainly.

## Hard requirements are not criteria

Anything you genuinely cannot live without is a gate applied before scoring, not a weighted
row. Data residency in a specific region, an on-premises deployment option, a compliance
certification your customers contractually require, an integration with a system you cannot
replace.

Putting a hard requirement in the scorecard lets a vendor fail it and still win on total,
which produces the worst outcome available: a purchase that scores well and does not work.
Keep the gates in a short list above the table, marked pass or fail, and disqualify on a
fail without further discussion.

## Reading the result, and ties

- **A clear winner, by more than about 10%.** Write it up. Name the runner-up's specific
  losing criterion.
- **Within 10%.** The scorecard has done its job by narrowing to two. Decide on the
  criteria that resist scoring — how the reference calls felt, which team will operate it,
  which vendor answered hard questions straight — and record that reasoning honestly. A
  judgement call recorded as a judgement call is defensible; a re-weighted table is not.
- **Nothing above the do-nothing option.** A legitimate result. Write the memo anyway: the
  requirement, what was evaluated, why none cleared the bar, and what would have to change.
  That document saves the next person from repeating the work in six months.

If someone asks to revisit the weights after seeing the totals, the answer is one change,
in writing, with a stated reason, and both versions kept. Usually the request is really an
argument that a criterion was defined badly, which is worth fixing in the definition rather
than in the number.

## The three-year cost model

Build one table per option, including build and do-nothing. Year one, two and three
separately — averaging hides the uplift, which is the point of the uplift.

| Line | Notes |
| --- | --- |
| Licence, year 1 | At the tier that actually includes the features you need, not the quoted tier |
| Licence, years 2-3 | Apply the contracted uplift, or 7-10% if uncapped, and mark it as an assumption |
| Growth on the pricing metric | Your growth rate applied to seats, hosts, volume or events. State the rate |
| Overage | Model one bad month: a runaway log producer, a traffic spike, a team onboarded early |
| Implementation | Vendor professional services plus your engineer-weeks at a loaded rate |
| Integration engineering | Per connector you must build; add annual maintenance for each |
| Training and change management | Hours per person times headcount, plus the productivity dip |
| Internal ownership | The fraction of a person who owns the tool, forever. Rarely zero |
| Infrastructure | Agents, collectors, egress, storage on your side |
| Exit provision | The migration cost, and any dual-running period, at the end of the term |

Two conventions keep the model honest. State every assumption inline — growth rate, loaded
rate, uplift — so a reader can disagree with the assumption rather than the total. And
leave unknowns visibly unknown; an estimate entered to complete the table becomes a fact by
the third time the spreadsheet is opened.

## Sensitivity: the two numbers to flex

Before presenting, re-run the model twice.

**Double the growth rate on the pricing metric.** If a plausible growth scenario makes the
cheaper option the expensive one, that is the finding, and it belongs in the memo's risk
section with the mitigation you negotiated — a cap, a committed rate, an alert threshold.

**Halve the adoption.** Many purchases are priced on seats or hosts and justified on full
adoption that does not arrive. If the business case only works at 100% adoption, say so
explicitly, and prefer ramped pricing over a full commitment.

These two flexes catch most of the purchases that look fine at signature and become the
subject of a cost-reduction exercise eighteen months later.
