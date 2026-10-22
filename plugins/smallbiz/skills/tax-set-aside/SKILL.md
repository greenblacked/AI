---
name: tax-set-aside
description: "Put aside the right share of every payment for tax: derive the rate from last year's return (tax plus social contributions over profit) plus 3 to 5 points, or a conservative provisional rate checked after the first quarter; sweep it to a separate account within 48 hours of each receipt, on the income-taxable amount only, with VAT or sales tax in its own bucket; list payment dates from the tax authority's pages with URL and date checked, a reminder 3 weeks ahead and an internal deadline 5 working days ahead; re-set the rate when the profit forecast moves over 15%. Use when asking how much to save for tax, about a freelancer tax account or estimated payments, or after a bill you could not pay. Procedure, not tax advice. Not for household budgets (personal-finance), cash forecasts (cashflow-forecast-13-week), monthly books (monthly-bookkeeping-close)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Tax Set-Aside

The routine is working when every receipt triggers a transfer to a tax account within 48 hours, the balance on each payment date is at least what is due, and the rate is checked against how the year is actually going.

Self-employed people get a tax bill because they spent money that was never theirs. Income arrives whole, tax arrives months later, and the gap feels like spare cash. The fix is mechanical: decide a rate once, move the money at receipt, and keep the account out of sight and out of reach. This skill is procedure only; the rules and rates are your jurisdiction's, and an adviser or the authority's own guidance decides edge cases.

## Scope

Use for: a freelancer, sole trader or small-company owner with irregular income who needs a sweep rate, an account structure and a payment calendar.

Do not use for: household budgeting and investing (`personal-finance`), the weekly cash picture the sweeps feed (`cashflow-forecast-13-week`), or the monthly routine that produces the profit figure (`monthly-bookkeeping-close`). This is procedure, not tax advice.

## Workflow

### 1. Establish the rate

With a previous year's return, compute the effective rate on profit:

```text
rate = (income tax + social contributions or national insurance + any other tax on the profit) / profit before tax
```

Take the figures from the filed return or the authority's calculation, using the same year for every part. Add 3 to 5 percentage points as margin, since profit usually rises and brackets bite harder at the top. With no history, use a conservative provisional rate, higher than you hope to pay, and check it against real numbers at the end of the first quarter. Round up. A rate that is a little high produces a refund or a spare pot; a rate that is low produces a bill. See `references/rate-and-calendar.md` for the working.

### 2. Open a separate account

Open a savings account used only for tax, ideally at a different bank from the one you spend from, so the transfer is a deliberate act and the balance is not visible every day. Name it for its purpose. If you hold VAT or sales tax, open a second pot beside it, because that money is collected on behalf of the authority and is never part of your income.

### 3. Sweep on every receipt

Within 48 hours of each payment landing, transfer two amounts:

- The VAT or sales tax included in the payment goes to the tax-collected bucket in full.
- The rate applied to the amount excluding that tax goes to the income-tax bucket.

Sweep on the money received, not on the invoice sent, unless your regime taxes invoiced income; check which basis you are on. Use a standing rule or a bank feature where one exists, but still check weekly that it ran. Expenses do not reduce the sweep at the moment of receipt: the rate is tax divided by profit, so applying it to receipts deliberately over-saves by the share of receipts that goes on costs. Treat that excess as a cushion and release it at the quarterly check in step 5, when actual profit is known.

### 4. Build the payment calendar

List every date in the year when you owe tax: balancing payments, payments on account, quarterly estimates, and VAT or sales-tax returns. Take dates only from the tax authority's own pages and record the URL and the date you read it beside each. For each date set two internal dates: a preparation reminder 3 weeks before (gather figures, check the balance) and an internal deadline 5 working days before the real one (money moved, return or payment submitted), so a bank delay or a login failure does not become a penalty.

### 5. Compare balance with obligations and adjust

At each reminder, compare the tax account with what is due on the coming date and on the date after. Re-estimate the year's profit; when the forecast has moved by more than 15% from the figure the rate was based on, recompute the rate, remembering that a rise in profit pushes the effective rate up. Top up the account for any shortfall from the next several receipts rather than all at once, and write down the new rate and the reason.

### 6. Check the payment-on-account rule for your jurisdiction

Many regimes require advance payments or penalise underpayment unless you pay a minimum, called a safe harbour or a payment on account. Look up the rule on the authority's page, note the rule and the date checked, and decide whether your calendar needs to follow it. For illustration, some systems set advance payments from the prior year's liability and some set safe-harbour percentages of last year's or this year's tax; the figures differ and change, so do not rely on a number remembered from elsewhere.

### 7. Review at year end

After filing, compare the actual liability with the money set aside. Record the real effective rate for next year's step 1, and decide what to do with a surplus: usually keep it as the start of next year's balance, since a rise in profit would use it.

## What to hand back

```text
Rate: [x]% = last year's [y]% + margin [z] points (or provisional, review date [date])
Accounts: income-tax account [where] · tax-collected account [where]
Sweep rule: within 48 hours of receipt, on the amount excluding VAT or sales tax
Calendar: [date - what is due - URL - date checked - prep reminder - internal deadline] ...
Safe-harbour or payment-on-account rule: [summary, URL, date checked]
Balance vs next due: [amount held vs amount due] · Profit forecast change: [%]
```

## Anti-patterns

- **Saving what is left.** Tax is a cost of the receipt, not a leftover. Move it first.
- **VAT or sales tax mixed into income.** It makes the rate look right while the real liability is never funded. Use a separate bucket.
- **A rate from memory or a forum.** Compute from your own return, then add margin.
- **Dates from an article.** Dates move. Read the authority's page and record when.
- **No buffer on the deadline.** A payment sent on the due day depends on every system working. Set the internal deadline earlier.
- **Rate never revisited.** A strong year changes the bracket; re-check when the forecast moves.

## Reference files

- `references/rate-and-calendar.md` — read at steps 1 and 4: a worked rate calculation, the calendar template and a quarterly check table.
