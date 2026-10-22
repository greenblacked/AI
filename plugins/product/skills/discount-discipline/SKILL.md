---
name: discount-discipline
description: "Put deal-desk rules around discounting so margin stops leaking one deal at a time: audit the last 50 closed deals for realised against list price by rep, segment and closeness to quarter end before writing any rule, then set a discount ladder with a named approver per level, a give-get rule so every point of discount buys something (longer term, prepayment, volume, a logo or case study), a first-year cap with the renewal price written into the contract, and no anonymous special-pricing requests. Use for \"reps discount too much\", \"set up a discount approval process\", \"every deal closes at 30 per cent off\", \"build a deal desk\" or a renewal where last year's discount is assumed to carry over. Not for researching what list price to charge (pricing-research), raising prices for existing customers (price-change-rollout) or your own job offer (offer-negotiation)."
allowed-tools: Read, Glob, Grep
---

# Discount Discipline

Discounting is under control when every discount on a closed deal can be traced to a named requester, a named approver at the right level, and something the customer gave in return; when realised price by rep and segment is reported monthly; and when a first-year discount does not silently become next year's price.

The usual failure is writing an approval matrix before looking at the deals. The matrix then encodes the habits that caused the leak — the same reps, the same last week of the quarter, the same "competitive pressure" with no competitor named — and adds a signature to them. The second failure is a ladder so slow that reps learn to ask for the top band every time, because waiting costs them more than asking.

## Scope

Use for: deep or inconsistent discounting on new deals; designing an approval ladder or a deal desk; deciding what customers must give in exchange for a discount; renewals where a discount keeps carrying over; requests for "special pricing" that arrive without context.

Do not use for: deciding what the list price should be, which is `pricing-research`; changing prices for existing customers across the base, which is `price-change-rollout`; an executive or key customer forcing a feature onto the roadmap as a condition of the deal, which is `roadmap-disruption-triage`; negotiating your own job offer, which is `offer-negotiation`; buying from a vendor, which is `vendor-evaluation`.

## Workflow

### 1. Audit the last 50 closed deals first

Export closed-won deals from the CRM and billing system: the last 50, or the last two quarters if that is fewer. For each, record list price and net price on the same annualised basis, term, payment terms, rep, segment, close date, recorded discount reason, approver, and anything given away off the invoice (free months, extra seats, included services, extended payment terms). Off-invoice concessions belong in the number; a twelve-month deal at 10 per cent off with three of those months free is about a third off list for the first year.

Compute realised price (net divided by list) and look at its spread by rep, by segment, by days before quarter end, and by whether a reason and approver were recorded. Then check renewals: did the first-year discount carry into the second year? Read `references/deal-audit.md` for the fields, the off-invoice conversion and a script that produces the tables from a CSV.

### 2. Decide what kind of leak it is

- **Concentrated**: a few reps, one segment or the last two weeks of each quarter account for most of the depth. Rules and coaching fix this.
- **Broad and consistent**: almost every deal closes at a similar deep discount. The list price is not the real price, and approval rules will only add delay. That is a `pricing-research` question first.
- **Renewal drift**: new-deal discounts are reasonable but renewals land at or below the first-year price. The contract wording is the fix (step 5).

Write the finding in one paragraph with the numbers before designing anything.

### 3. Set a discount ladder with named approvers

Set the bands from the audit's distribution, so the rep's own band covers the ordinary case and approval is needed only for the unusual one. Name a person for each band, not a role, with a deputy, and give each an answer time, normally one working day. A ladder whose approvals take a week trains reps to over-ask, because the top band costs the same wait as the bottom one.

### 4. Make every discount buy something

For each band, list what the customer gives in exchange, priced in advance: a longer committed term, annual or multi-year prepayment, a volume or seat commitment, logo use, a published case study, reference calls. A discount with no give is a price cut, and the customer learns that asking works. Be wary of "signing by the end of the quarter" as a give: it is worth something to the seller, and paying for it teaches customers to wait for the last week.

Read `references/ladder-and-give-get.md` for the ladder template, the give-get table and the request form.

### 5. Cap the first year and write the renewal price into the contract

Treat a new-customer discount as a first-year concession with a cap, and write the renewal price, or the uplift to it, into the order form. Without that, the discounted price is the only price the customer has seen, and every renewal starts with a fight to get back to list. Have legal draft the clause for your contract template and jurisdiction; this procedure is not legal advice.

### 6. Refuse anonymous special-pricing requests

Every request names the rep, the customer, the band asked for, the give offered, and the evidence for the pressure: the competitor and their written quote, the budget figure the buyer stated, the procurement benchmark. A request that says only "the customer needs a better price" goes back to the rep, not up the ladder. The form is the cheapest control in the whole procedure, because most unjustified discounts are never written down by anyone.

### 7. Roll it out with an effective date

Announce the rules with a date. Deals already in negotiation before it close under the old terms if they close by a stated cut-off; after it, the new rules apply. Train approvers on the give-get table before reps hear about it, so the first requests get consistent answers.

### 8. Report monthly and revisit quarterly

Each month report realised price by rep and segment, approvals by band, requests returned for missing information, off-invoice concessions, and renewal price against list. Each quarter rerun the audit on that quarter's deals and adjust bands that are either never used or used on most deals.

## Output format

```markdown
## Audit
[Deals examined and period; realised price spread by rep, segment, quarter-end timing; off-invoice concessions; renewal carry-over; deals with no approver or reason.]

## Diagnosis
[Concentrated, broad or renewal drift, with the numbers.]

## Rules
[Ladder with bands, named approvers, deputies, answer time; give-get table; first-year cap and renewal clause; request form.]

## Rollout
[Effective date, in-flight cut-off, approver training, first monthly report date.]
```

## Anti-patterns

**Rules before the audit.** A matrix designed without the deal data encodes the leak it was meant to stop.

**Discount without a give.** A price cut that buys nothing teaches the customer that asking is free.

**Ignoring off-invoice concessions.** Free months and bundled services are discounts that never appear in the discount field.

**A slow ladder.** If approval takes a week at every level, reps ask for the top band every time.

**First-year price with no renewal price.** The discount becomes the baseline and next year's renewal is a renegotiation.

**Approval by role, not person.** "Sales leadership" never answers. Name someone and a deputy.

## Reference files

- `references/deal-audit.md` — read at steps 1, 2 and 8: export fields, converting off-invoice concessions, a standard-library script for realised price by rep, segment and quarter-end timing, and how to read the result.
- `references/ladder-and-give-get.md` — read at steps 3 to 6: the ladder template, the give-get table, the request form and the contract points to raise with legal.
