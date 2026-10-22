---
name: poc-plan
description: "Scope and run a customer proof of concept or pilot as the vendor so it ends in a decision rather than drifting: success criteria taken from the buyer's own problem, measurable and signed by the buyer before any environment is set up; a fixed window of two to four weeks with a named customer sponsor and a decision date; a mid-point checkpoint that can end it early; and an exit review that states results against each criterion and the agreed commercial next step. No criteria means no POC. Use when a customer wants a POC, asks for a pilot or trial before buying, a POC has run over and nobody can say if it passed, or someone says \"they want to try it on their data first\" or \"the pilot keeps getting extended\". Not for answering the RFP itself (rfp-response), evaluating a product we are buying (vendor-evaluation), or testing a prototype's usability with users (usability-test-plan)."
allowed-tools: Read, Glob, Grep
---

# POC Plan

A proof of concept is done well when it ends on its decision date with a result the buyer
agrees with, measured against criteria the buyer signed before it started, and with the
commercial next step already agreed for the case where it passes. The deliverable is the
signed plan at the start and the exit review at the end.

The job is hard because a POC is easy to start and hard to finish. The buyer asks to "try
it", the sales engineer sets up an environment the same week, and nobody writes down what
success means. Three weeks later the customer has new ideas, the champion has gone quiet,
the trial is extended twice, and the outcome is an opinion. A POC without criteria is free
consulting, and one without a sponsor is evidence nobody with authority will read. The
rules below make the POC a short experiment with a decision attached.

## Scope

Use for: a proof of concept, technical validation, pilot or extended trial that a
prospect or customer asks for before buying; rescuing one that has drifted; deciding
whether to agree to one at all.

Do not use for: writing the RFP response that may accompany it (`rfp-response`);
evaluating a product when we are the buyer (`vendor-evaluation`); a usability study of a
prototype with users (`usability-test-plan`).

## Gates

These are conditions, not suggestions. If one is not met, the POC does not start.

1. **Criteria before setup.** Success criteria are written from the buyer's problem,
   measurable, and signed by the customer sponsor before any environment, account or data
   transfer is set up. Setup started without criteria removes the only leverage that gets
   them written.
2. **A named customer sponsor** with authority to make or recommend the purchase, who
   attends the kickoff and the exit review.
3. **A fixed window of two to four weeks** with a decision date. Long enough to test the
   criteria; short enough that the buyer's attention lasts.
4. **The next step agreed in advance**: what happens commercially if the criteria are met.

## Workflow

### 1. Qualify the request

Ask what decision the POC is meant to support, who will make it, and what happens if it
succeeds: is there budget, a timeline, a buying process. A POC requested before any of
that is known is often a way to defer a decision or to gather evidence for a competitor's
negotiation. Where the buyer needs production proof rather than technical feasibility,
propose a paid pilot with a limited scope instead; a free POC run in production is a
deployment without a contract.

### 2. Write the criteria from the buyer's problem

Start from the problem in the buyer's words, then write three to five criteria. Each one
names the metric, its current baseline, the target, how and from what data it will be
measured, and who on the customer side measures it. "Reconciliation of a month's invoices
completes in under two hours on their data, measured by their finance lead, against a
current two days" is a criterion. "Evaluate performance" is not.

Keep the list short and pick the requirements the decision turns on. Ten criteria produce
a scorecard nobody acts on, and the easy ones pass without telling anyone anything.
`references/success-plan-template.md` has the plan template and examples of criteria
rewritten from vague to measurable.

### 3. Agree scope, data and roles, then sign

The plan states what is in and out of scope, the environment and who provides it, the
data to be used and the approvals it needs, the roles on both sides, the timeline with the
checkpoint and the decision date, and the commercial next step. Start data and security
approvals on the first day; they are the commonest cause of a POC that loses its first
week. If production or personal data is involved, settle how it is handled and deleted
before transfer with the people who own data protection.

The customer sponsor signs the plan. A plan agreed only by the technical evaluator can be
overruled by someone who never saw it.

### 4. Run it against the criteria

Hold a kickoff with the sponsor. Record progress against each criterion as it happens,
with evidence, in a log both sides can see. Hold a short weekly check-in.

New requests during the POC go into a change log. A new criterion is added only in
writing, with the sponsor's agreement and, where it adds work, a new decision date. Scope
added informally is how a three-week POC becomes three months.

### 5. Hold the mid-point checkpoint

At the half-way point, review each criterion with the sponsor: on track, at risk, or
failing. End the POC early, or reset it in writing, when a criterion cannot be met, when the
sponsor has disengaged, or when the buyer's priorities have changed. Ending early is a good
outcome; it saves both sides two weeks and keeps the relationship honest.

### 6. Run the exit review on the decision date

Present the result against each signed criterion: met, partly met or not met, with the
evidence. The sponsor states the decision. If the criteria are met, move to the commercial
step agreed in the plan; if not, say what would have to change and whether it is worth
another attempt.

Then close down: remove access, delete or return the customer's data as the plan states,
and record the outcome and the reasons for the win-loss review. Do not extend the POC
instead of holding the exit review; an extension without a review is a decision deferred.

## Output format

```markdown
## POC: [customer], [dates], decision on [date]

### The problem, in the buyer's words
[One or two sentences.]

### Success criteria (signed by [sponsor], [date])
| # | Metric | Baseline | Target | Measured by | Result |

### Roles
[Customer sponsor, customer technical lead, our account owner, our technical lead.]

### Scope, data and environment
[In, out, data source and approvals, deletion at the end.]

### Timeline
[Kickoff, checkpoint, decision date.]

### Next step if criteria are met
[The agreed commercial step and its date.]

### Exit review
[Per criterion result, decision, next step, data deletion confirmed.]
```

## Anti-patterns

**Setting up the environment before the criteria exist.** The leverage to get criteria
written disappears the moment the buyer has a working account.

**Criteria written by the vendor alone.** They test what the product does well rather than
what the buyer needs, so passing them does not move the decision.

**The silent extension.** The decision date passes, the trial keeps running, and the
champion is now the only person still logging in. Hold the exit review on the date.

**No sponsor at the exit.** The technical evaluator likes the product and has no authority
to buy it. The result needs to be heard by the person who decides.

**Production data with no deletion plan.** The customer's data is still in a trial tenant
a year later, which is a finding for their auditors and ours.

## Reference files

- `references/success-plan-template.md` — read when writing the plan: the full template
  for the signed success plan, vague criteria rewritten as measurable ones, the
  mid-point checkpoint questions, and the exit review agenda.
