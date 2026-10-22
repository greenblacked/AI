# Cohort model

Contents: choosing cohorts, the table, break-even with downgrades, a worked example, and setting the tripwire.

## Choosing cohorts

Split where reactions will differ, and stop when a cohort becomes too small to read:

- Plan and billing period (monthly and annual customers decide at different moments).
- Discount depth against the new list price (a 10 per cent increase on list can be a 60 per cent increase for an account on a deep legacy discount).
- Tenure (first-year accounts have not yet built the product into their work).
- Size or revenue band (the largest accounts get individual handling regardless of cohort).
- Purchase channel (sales contract, self-serve, app store, reseller), because notice and billing mechanics differ.

## The table

| Cohort | Accounts | Revenue now (annual) | Price change for them | Revenue if nobody reacts | Break-even extra loss | Baseline annual churn and downgrade | Expected reaction | Policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

"Price change for them" is per cohort, not the headline figure: compute it from what they actually pay today to what they will pay.

## Break-even with downgrades

Let x be the cohort's price increase as a fraction, and R its current revenue after the losses it would have anyway. If the change causes an extra share L of that revenue to leave (accounts that cancel, plus the revenue lost by accounts that downgrade), revenue after is R × (1 − L) × (1 + x). It equals R when:

```text
L = x / (1 + x)

x = 0.10  ->  L ≈ 0.091
x = 0.20  ->  L ≈ 0.167
x = 0.50  ->  L ≈ 0.333
```

A downgrading account counts as a partial loss: the difference between what it would have paid on its old plan at the new price and what it pays on the lower plan.

## Worked example

A cohort of 200 annual accounts on a legacy plan at 1,000 a year each, moving to 1,200 (x = 0.2). Revenue now: 200,000.

- If nobody reacts: 240,000.
- Break-even extra loss: about 16.7 per cent of revenue, roughly 33 accounts' worth.
- Scenario: 20 accounts cancel because of the change and 10 downgrade to a plan at 600. Revenue after: 170 × 1,200 + 10 × 600 = 210,000. The change still earns 10,000, about 5 per cent, despite 15 per cent of accounts reacting.
- The cohort's normal annual churn and downgrade over the last two years was 8 per cent. The tripwire for this cohort could be set at an extra 12 per cent of revenue lost within the first renewal quarter, comfortably inside break-even, leaving time to act before the loss turns negative.

## Setting the tripwire

1. Baseline: the cohort's churn and downgrade rate for the same months in previous years, so a seasonal renewal peak is not read as a reaction.
2. Threshold: an extra loss below the break-even, chosen so that crossing it still leaves time to soften the change for the rest of the cohort.
3. Window: long enough to include renewals, since annual customers can only react at renewal. Leading signals fill the gap: cancellation-page visits, downgrade requests, pricing-tagged support tickets, accounts flagged at risk.
4. Review date and decider written down before notice goes out.
5. Rollback per cohort written down too: extend the sunset, offer a multi-year lock-in at the old price, stop at the first step of a stepped increase, or revert.
