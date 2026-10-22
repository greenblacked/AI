---
name: price-change-rollout
description: "Raise prices or move existing customers onto a new price or plan without a churn spike: model revenue by cohort first (plan, tenure, size, discount, renewal date), choose grandfather-with-sunset or migrate-at-renewal per cohort, give notice of at least the renewal window (60 to 90 days for annual B2B contracts) and whatever contracts, consumer law and app stores require, have account owners tell top accounts before any email goes out, and set a rollback tripwire on churn and downgrade rate against baseline with a dated review. Use for \"raise prices\", \"grandfather existing customers\", \"move legacy plans to the new pricing\" or \"how much notice for a price increase\". Not for deciding what the new price should be (pricing-research), per-deal discount approval (discount-discipline), retiring a plan outright (feature-sunset) or the changelog (release-notes)."
allowed-tools: Read, Glob, Grep
---

# Price Change Rollout

A price change is rolled out well when every paying account is in a cohort with a written policy and an effective date, the revenue model per cohort shows how much churn the change can absorb before it loses money, every customer received notice at least as early as their contract and the law require, top accounts heard it from a person first, and a tripwire with a review date says when to stop or soften.

The usual failure is one email to everyone on one date. Annual customers mid-term, monthly customers, heavily discounted legacy accounts and the five largest customers all get the same message, and the change is judged by the cohort that reacts worst. The second failure is grandfathering forever: it avoids the churn and leaves a growing set of legacy prices nobody can ever touch.

## Scope

Use for: a list-price increase on existing customers; moving customers from legacy plans to current ones; changing the value metric for existing accounts (per seat to per usage); ending a grandfathered price; announcing new pricing that affects the installed base.

Do not use for: deciding the new price, which is `pricing-research`; how far sales may discount individual deals, which is `discount-discipline`; retiring a plan, feature or product outright, which is `feature-sunset`; the release notes or changelog entry, which is `release-notes`.

## Workflow

### 1. Inventory every paying account and its contract terms

For each account: plan, price paid, list price, current discount and its expiry, billing period, next renewal or bill date, tenure, size, usage against the plan, region, and how it was bought (sales contract, self-serve, app store, reseller). Read the contract terms that govern price changes first: notice clauses, caps on renewal uplift, price-protection or most-favoured-customer clauses. A contract term overrides the plan; this procedure is not legal advice, so have legal confirm what each template allows.

### 2. Model revenue by cohort

Group accounts into cohorts that will react differently: by plan, discount depth, tenure, size and billing period. For each, compute current revenue, revenue after the change, and the break-even loss: the extra share of the cohort's revenue, beyond what it would lose anyway, that can leave because of the change before the change loses money. For an increase of x (as a fraction), revenue is unchanged when the retained share is 1 / (1 + x), so break-even loss is x / (1 + x); a 20 per cent increase breaks even at about 17 per cent of the cohort's revenue lost. Count downgrades as lost revenue too, since they reduce revenue without showing up as churn.

Set each cohort's break-even beside the extra loss you expect from it. Cohorts paying far below list, on short tenure, on monthly billing or with low usage tend to react most, and a cohort whose break-even is small next to its likely reaction is where a gentler policy pays. Read `references/cohort-model.md` for the table, the formula with downgrades and a worked example.

### 3. Choose a policy per cohort

- **Migrate at renewal**: the new price applies from each account's next renewal after notice. The default for annual contracts.
- **Grandfather with sunset**: the old price holds until a stated date, then the new price applies. For long-tenure or strategic cohorts where an abrupt change would cost more than it earns. The sunset date is written in the first notice.
- **Stepped**: deeply discounted accounts move to list in two or more steps rather than one large jump.
- **Immediate after notice**: monthly self-serve plans, once the notice period has run.

Do not grandfather without a sunset date. A price with no end date is a permanent second price list.

### 4. Set notice from the renewal window and the rules

Give at least the renewal window: annual B2B customers need notice before the point at which they can still decide not to renew, which in practice means 60 to 90 days before renewal, longer if the contract says so. Monthly and consumer subscriptions follow the notice and consent rules of the customer's jurisdiction. App stores run their own notice and consent flows for subscription price increases, so read the current store rules rather than assuming your own email is enough. Set each cohort's notice date backwards from its effective date.

### 5. Tell people in order

1. Internal first: support macros, a sales and success FAQ, the exceptions policy and who may grant one.
2. Top accounts by revenue or strategic weight hear from their account owner by call, followed by the written notice, before any bulk email.
3. Written notice to every affected account: what changes, the effective date for them, why, and their options (lock in an annual term at the current price, move to a different plan, contact a person).
4. In-product notice to admins and billing contacts, repeated before the effective date.
5. The billing change on the effective date, checked on a sample of real invoices in the first cycle.

Read `references/notice-and-comms.md` for the timeline, the notice template, the FAQ and the exceptions log.

### 6. Set a rollback tripwire before notice goes out

Measure the baseline churn and downgrade rate per cohort over comparable past periods, allowing for seasonality. Set the tripwire as a rate above baseline that the cohort model says would cost more than the change earns, with a review date. Because churn shows up at renewal, watch the leading signals in between: cancellation-page visits, downgrade requests, support tickets tagged to pricing, and accounts flagged at risk by their owners. Write down in advance what rollback means for each cohort (extend the sunset, offer an annual lock-in, revert the cohort) and who can call it.

### 7. Run the review and close out

On the review date, compare each cohort's churn and downgrades with the baseline and the tripwire, and record the decision. When every cohort has reached the new price or its sunset date has passed, remove the old prices from billing, the price list and the sales tooling, so they cannot be sold again by accident.

## Output format

```markdown
## Inventory
[Accounts, cohorts, contract terms that constrain the change.]

## Cohort model
[Per cohort: revenue now, revenue after, break-even loss, normal churn, risk.]

## Policy
[Per cohort: migrate at renewal, grandfather with sunset, stepped, or immediate; effective dates.]

## Notice and comms
[Notice dates per cohort, top-account calls and owners, message, FAQ, exceptions policy.]

## Tripwire
[Baseline, threshold, leading signals, rollback per cohort, who decides, review date.]
```

## Anti-patterns

**One email, one date.** Cohorts with different contracts and price histories react differently. Plan per cohort.

**Grandfathering forever.** It turns a price change into a permanent second price list. Every grandfathered price gets a sunset date.

**Notice shorter than the renewal window.** A customer who learns of an increase after their chance to leave has passed feels trapped, and says so publicly.

**Top accounts finding out from a bulk email.** The largest customers should hear it from a person first.

**No baseline.** Without last year's churn for the same cohort and season, every cancellation looks like a reaction to the price.

**Old prices left in billing.** A retired price that can still be selected will be sold again.

## Reference files

- `references/cohort-model.md` — read at steps 2 and 6: the cohort table, break-even with downgrades, a worked example, and setting the tripwire from the model.
- `references/notice-and-comms.md` — read at steps 4 and 5: the notice timeline, the customer notice template, the internal FAQ, the exceptions log and the close-out checklist.
