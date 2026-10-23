---
name: roadmap-disruption-triage
description: "Decide what to do when a key customer, an executive or a competitor's move tries to force something onto a committed roadmap: write the trade-off ledger before answering (the item moving in, the named items slipping, their new dates, who must be told), sort the demand into promise, proof or pressure, test claimed revenue against a signed contingency rather than a forecast, offer three costed options (do it, a smaller version, do not), and log the decision with a re-plan trigger. Use for \"the CEO wants this now\", \"our biggest customer says they will leave unless\", \"a competitor just shipped it, drop everything\" or \"sales escalated over our heads\". Not for the routine request backlog (request-triage), setting quarterly goals (okr-planning), reporting a slip afterwards (status-update) or attacking a plan before committing (spec-premortem)."
allowed-tools: Read, Glob, Grep
---

# Roadmap Disruption Triage

A disruption is handled when the person who asked has an answer they can repeat, every item that moved has a new date and an owner who knows, the claimed justification has been tested against something signed or measured, and the decision sits in a log with the condition that would reopen it.

The usual failure is saying yes in the room. The new item goes in, nothing is named as coming out, and the cost turns up a month later as three commitments that slipped without anyone deciding they should. The second failure is the mirror image: refusing on principle, so the next escalation goes around the product team entirely. Both come from answering before the trade-off is written down.

## Scope

Use for: an executive asking for something "now"; a large customer making a renewal or expansion conditional on a feature; a competitor launch that prompts calls to change course; a sales escalation that bypassed the normal intake; a partner or regulator date that collides with committed work.

Do not use for: the steady flow of feature requests from sales and customers, which is `request-triage`; setting the quarter's goals in the first place, which is `okr-planning`; writing the update that reports the outcome, which is `status-update`; stress-testing a new plan before it is committed, which is `spec-premortem`; retiring something already shipped, which is `feature-sunset`.

## Workflow

### 1. Buy a short, dated pause

Acknowledge the request and give a date for the answer, normally within the week. "I will come back to you on Thursday with what it costs and what moves" is a commitment the requester can accept; "let me think about it" is not. The pause exists to write the ledger, not to wait for the request to go away. If the requester insists on an answer now, the honest answer is the cost you already know: name the committed item it would displace.

### 2. Restate the demand as an outcome

Write one paragraph: who is asking, on whose behalf, what they need to be true and by when, and what they believe happens if it is not. Ask the requester to confirm it. Half of disruptions shrink here, because the outcome needed ("the customer's security team needs to see SSO on the roadmap before procurement signs") is smaller than the feature named ("build SSO this month").

### 3. Write the trade-off ledger before answering

Get a range estimate for the new item from the team that would build it. Then list, by name, the committed items that slip if it goes in, each with its current date, its new date, who was promised it (customers, other teams, the board) and who will tell them. Capacity is fixed in the short term; if you cannot name what slips, the hidden answer is quality, on-call load or overtime, and those go in the ledger too.

Read `references/trade-off-ledger.md` for the ledger, the options table and the decision log entry.

### 4. Sort the demand into promise, proof or pressure

- **Promise**: the company already committed in writing (an order form, a contract clause, a public dated commitment). It is owed; the question is only when and how. This is procedure, not legal advice: legal confirms what a contract commits the company to.
- **Proof**: evidence that delay costs something measurable — a signed contingency, deals lost with this as the recorded reason, churn with this as the stated cause.
- **Pressure**: urgency without either — an executive's conviction, one loud call, a competitor's press release with no lost deals behind it.

Test claimed revenue against a written contingency: an order form or renewal held pending delivery by a date, or an email from the customer's signatory saying so. A forecast, a pipeline stage or "they said on the call" is pressure, however large the number. For a competitor move, count the deals in the last two quarters where it was the recorded loss reason. Read `references/demand-classification.md` for the tests, the questions to ask and what counts as evidence for each class.

### 5. Offer three options with their cost

Always put three on the table, so the choice is between costs rather than between yes and no:

1. **Do it**: the full request, with the ledger's slipped items and dates.
2. **A smaller version**: the least that meets the outcome from step 2 — a dated commitment instead of a build, a manual or services workaround, a partial scope, a configuration of something that exists. It is usually the one chosen.
3. **Do not**: what you say instead, and the risk accepted, in revenue and relationship terms.

Each option carries what slips, the revenue tested in step 4, the risk, and whether it can be reversed later. Recommend one, and say why.

### 6. Let the owner of the trade-off decide with the cost visible

The person who decides is whoever owns the roadmap the slipped items belong to, or the executive above all of them when items slip across teams. An executive who asked for the item may overrule the recommendation; the point is that they do it looking at the ledger, not that they agree with you. Record who decided.

### 7. Tell people in order

Owners of slipped items hear first, then customers who were promised them (from their account owner, not from a release note), then the requester with the decision and the reason they can repeat. A slipped commitment the customer learns about from the changelog costs more trust than the slip.

### 8. Log the decision with a re-plan trigger

Add an entry to the decision log: date, demand, class, options, choice, decider, slipped items and new dates, and the trigger that reopens it — the contingency not signed by its date, the build overrunning its range by a stated amount, or the same customer asking again for more. Count disruptions per quarter. More than one or two a quarter on the same team means the roadmap commits further out than the business can hold, and the fix is a shorter commitment horizon, not better triage.

## Output format

```markdown
## Demand
[Who, on whose behalf, outcome needed, by when, confirmed by requester on date.]

## Class
[Promise, proof or pressure, with the evidence or its absence.]

## Ledger
[New item and estimate range; each slipped item with old date, new date, who was promised it, who tells them.]

## Options
[Do it / smaller version / do not, each with cost, revenue tested, risk and reversibility. Recommendation and why.]

## Decision
[Option chosen, decider, date, communication order, re-plan trigger and review date.]
```

## Anti-patterns

**Yes in the meeting.** The cost is real and arrives later, unowned. Answer on a date with the ledger.

**"It will only take a week."** An estimate from the requester is not an estimate. Get a range from the team that builds it.

**Unnamed slippage.** "We will absorb it" means something slips without a decision. Name the item.

**Forecast treated as proof.** Pipeline revenue is a hope. Only a signed contingency or recorded losses count.

**A binary choice.** Yes or no forces a winner and a loser. The smaller version is usually the right answer and only appears if you write it down.

**Silent slips.** A customer who finds out from the changelog that their date moved is a churn risk you created.

## Reference files

- `references/trade-off-ledger.md` — read at steps 3, 5 and 8: the ledger template, the options table, the decision log entry and re-plan triggers.
- `references/demand-classification.md` — read at step 4: tests for promise, proof and pressure, the questions that surface a contingency, and how to weigh a competitor move.
