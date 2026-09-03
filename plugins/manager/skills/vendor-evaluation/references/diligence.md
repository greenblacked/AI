# Diligence: security, legal, references and the PoC plan

The parallel track from step 7, plus the reference-call script and the proof-of-concept
test plan. Start this in week one; every item here can kill a deal, and each one gets more
expensive to discover later.

## Contents

- [The vendor question bank](#the-vendor-question-bank)
- [Reading a SOC 2 report](#reading-a-soc-2-report)
- [Contract and DPA checklist](#contract-and-dpa-checklist)
- [Exit clauses worth having](#exit-clauses-worth-having)
- [Reference-call script](#reference-call-script)
- [Proof-of-concept test plan](#proof-of-concept-test-plan)
- [Negotiation checklist](#negotiation-checklist)

## The vendor question bank

Send these in writing and keep the answers with the evaluation. Written answers are
citable later; a verbal answer on a call is not, and the person who gave it will have moved
to another account by renewal.

**Data**

- What data do you store, where is it stored, and where is it processed?
- How long is it retained by default, and can we set that? What does deletion mean
  technically, and how long does it take to complete?
- Is our data used to train models or to improve your product, and is that opt-out or
  opt-in?
- Give us a complete bulk export of a realistic account. What format, what is excluded, how
  long does it take?
- Who at your company can read our data, under what controls, and is that access logged in
  a log we can request?

**Security**

- Latest SOC 2 Type II or ISO 27001 certificate plus the statement of applicability. What
  is in scope and what is excluded?
- Summary of your most recent independent penetration test, and the remediation status of
  its findings.
- Describe your most recent security incident and what changed afterwards.
- Which of SSO, SCIM, audit-log export, IP allow-listing, role-based access and
  customer-managed keys are on the tier we are buying, and which require an upgrade?
- Do you support scoped, rotatable API credentials with more than one key active at a time?
  (This looks minor at signature and becomes the reason a rotation needs an outage — see
  the `secret-rotation` skill.)

**Operations**

- Availability over the last 12 months, and a link to the public status history.
- RTO and RPO. What is our position if you are unavailable for a full day?
- How are we notified of breaking changes and deprecations, and with how much notice?
- What is the support SLA in the contract, by severity, and what is the escalation path
  outside business hours?

**Commercial**

- Exactly what is the billing metric, and what happens when we exceed the commitment?
- What is the renewal uplift, and will you cap it in writing?
- Who are three customers of roughly our size and shape we may speak to?

An evasive answer to any of these is itself data. Record it as the answer rather than
chasing it into a vagueness that ends up unrecorded.

## Reading a SOC 2 report

The logo means less than the report, and the report is short enough to read.

- **Type I versus Type II.** Type I says controls were designed appropriately on one day.
  Type II says they operated over a period, typically six or twelve months. Only Type II is
  evidence about how they actually run.
- **The period.** A report covering a window that ended fourteen months ago describes a
  company that may no longer exist in that form. Ask for the bridge letter.
- **The scope.** Which systems, products and locations are covered. A report scoped to the
  core platform does not cover the acquired product you are buying.
- **The trust services criteria included.** Security is standard; availability,
  confidentiality, processing integrity and privacy are each optional. If availability
  matters to you and it is not in scope, the report says nothing about it.
- **The exceptions section.** This is the part worth reading closely: exceptions the auditor
  noted, and management's response. A report with no exceptions is either a very small
  scope or a very short period.
- **Sub-service organisations and the carve-out method.** Controls at their cloud provider
  may be excluded from the report entirely, with complementary user entity controls listed
  as your responsibility. Read that list — it names things you have to do.

## Contract and DPA checklist

- Data processing agreement in place, with the transfer mechanism named for each region.
- Sub-processor list published, with advance notice of changes and a right to object.
- Breach notification obligation to you, stated in hours, not "without undue delay".
- Liability cap and what it is a multiple of. Confirm whether data-protection breaches sit
  inside or outside the cap.
- Audit rights, or the audit-report-in-lieu clause, and how often you can exercise them.
- Uptime SLA with a service credit that is meaningful — credits capped at the monthly fee
  are compensation for the fee, not for the outage, and should be treated as a signal
  rather than a remedy.
- Termination for convenience, with the notice period and any early-termination charge.
- Assignment and change-of-control: what happens if they are acquired by a competitor of
  yours, or by anyone your customers have objected to.
- Publicity and logo rights. Default to declining; it is free to trade away later.

## Exit clauses worth having

Ask for these while the deal is unsigned. Each one costs the vendor almost nothing at
signature and is unobtainable at renewal.

- A committed data export: format, completeness including historical data, and the maximum
  time to deliver it.
- Continued export access for a defined period after termination — 30 to 90 days — so a
  migration is not a cliff.
- Deletion certification after that window.
- Price protection on renewal, expressed as a cap.
- The right to run a parallel migration without paying twice for overlapping months, or a
  short dual-running allowance.

Then write the exit plan itself: how the data comes out, in what shape, what would need
rebuilding, how long the migration takes, and who does it. That plan is what makes the
lock-in risk in the memo a number rather than an adjective. Executing it later is a
migration with a rollback point — the `cutover` skill covers running one.

## Reference-call script

Thirty minutes. The vendor-supplied references are worth taking, but at least two
references should be ones you found yourself; a customer who has no relationship with the
account team answers differently.

1. What were you replacing, and what problem were you solving? (Establishes whether their
   requirement resembles yours.)
2. How long from signature to real production use, and what was the surprise?
3. What surprised you three to six months in, once the honeymoon ended?
4. What did you end up building yourself that you expected to get from the product?
5. What does support look like when it is urgent and out of hours? Give me the last time
   you needed them badly.
6. How has your bill tracked against your first-year quote, and why?
7. What happened at your first renewal?
8. What broke during an upgrade or a migration?
9. Who operates it day to day, and how much of their time does it take?
10. What would make you leave? And knowing what you know, what would you negotiate
    differently?

Ask question 3 and question 10 of every reference. They generate the two answers that
change decisions. Note the scale the reference operates at — a customer a tenth your size
is evidence about a different product experience.

## Proof-of-concept test plan

Copy this shape and fill it in before the trial starts. Circulate it to the vendor too: a
vendor who sees the pass criteria in advance will either help you meet them or tell you
they cannot, and both outcomes are useful.

```markdown
# PoC: [product] — [start date] to [end date, fixed]

## Requirements under test
1. [Hardest requirement, phrased as a measurable outcome]
2. [Second hardest]

## Data
[Which real dataset, how it gets there, what legal approved, how it is removed afterwards]

## Participants
Operator: [someone who will be on call for it]
Sceptic: [someone who did not pick it]
Champion: [may participate, may not be the only one]

## Pass criteria (written before access was granted)
| # | Criterion | Threshold | Result | Evidence |
|---|---|---|---|---|
| 1 | [outcome] | [number or time] | | |
| 2 | [outcome] | [number or time] | | |

## Day-two tasks (each run and timed)
- Add a user; remove a user; verify the removal took effect
- Apply an upgrade or a version change
- Trigger a realistic failure and observe what the product does
- Perform a complete data export and inspect what came out
- Run one on-call scenario end to end at a realistic hour

## Notes
[Written during the trial, not reconstructed afterwards]
```

Run the identical plan for each finalist. A PoC that diverges per vendor produces a
comparison of the PoCs.

## Negotiation checklist

- Know your walk-away: the do-nothing option and its cost, written down before the first
  pricing conversation.
- Have a genuine second option still live. A single-vendor negotiation is a price
  announcement.
- Their quarter-end and year-end give real movement on price and very little on terms; do
  not let their calendar set your decision date, and do not accept a discount that expires
  in 48 hours as a reason to skip the security review.
- Trade the things that cost you little: a case study, a reference call, a longer term when
  the requirement is genuinely stable.
- Get the renewal cap, the export commitment and the support SLA in the contract. Ranked by
  what you will regret, those beat several percent on the headline price.
- Do not sign before security and legal have finished. A start date agreed in advance of
  their sign-off is how a review becomes a formality.
