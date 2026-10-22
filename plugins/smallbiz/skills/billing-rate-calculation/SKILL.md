---
name: billing-rate-calculation
description: "Work out the hourly or day rate you must charge for a target income by working backwards: take-home plus tax set-aside plus business costs (software, insurance, accountant, equipment, pension, health cover) and unpaid leave gives required revenue, divided by billable hours tracked for four weeks rather than guessed. Produces a floor, a target and a walk-away rate, plus the minimum project size below which overhead makes the rate wrong. Market rates are a sanity check, not the method. Use whenever someone asks 'what should I charge per hour', 'is my day rate too low', 'I am moving from employee to freelance, what rate', 'how much do I need to bill'. Not for employee pay bands (compensation-benchmarking), negotiating a job offer (offer-negotiation), household budgeting (personal-finance), or pricing one job with this rate (fixed-price-quote)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Billing Rate Calculation

A finished calculation gives three numbers: a floor rate below which each hour loses money against the life you need to fund, a target rate you quote, and a walk-away rate you refuse to go under, each with the arithmetic shown so it can be rechecked when a cost changes.

The usual failure is starting from the market. "Developers like me charge 60 an hour" ignores that a salaried colleague works about 1,800 of the 2,080 hours they are paid for and a freelancer is paid for the 900 that remain once sales, admin, gaps between clients and unpaid leave are taken out. A rate copied from chatter is also anchored on other people's costs and tax position. The second failure is dividing by a 40-hour week. This skill works backwards from what you need to a rate, then uses the market only to check it.

## Scope

Use for: setting or checking an hourly or day rate for freelance or small-business work, converting an employee salary to a freelance equivalent, and deciding the smallest job worth taking.

Do not use for: pay bands for employees (`compensation-benchmarking`), negotiating a job offer (`offer-negotiation`), household budgeting (`personal-finance`), or pricing one specific job with the rate you have (`fixed-price-quote`). Tax rules, pension limits and insurance requirements differ by country, so name the variable you are unsure of and send the question to an accountant. This is procedure, not tax advice.

## Workflow

### 1. Fix the target take-home

Ask what the person needs to live on per year after tax, and whether that includes saving beyond the pension. Use the number they need, not the number they hope for. If they are converting from a salary, start from take-home pay, not gross: the tax position of a sole trader differs and a gross-to-gross comparison hides it.

### 2. Add every cost the employer used to carry

Build the list item by item, annual amounts:

- Tax set-aside: the share of profit that goes to income tax and social contributions, from the accountant's estimate or the prior year's return. Where the rule is uncertain, take the higher plausible rate; an over-estimate becomes a refund, an under-estimate becomes a debt.
- Software, subscriptions and tools.
- Insurance: professional indemnity, liability, any cover required by clients.
- Accountant and bookkeeping.
- Equipment, divided by its replacement interval: a laptop at 1,800 replaced every three years is 600 a year.
- Pension saving the employer used to match, and health or income-protection cover the employer used to provide.
- Workspace, travel, training, and any membership you need.
- A buffer for the quiet months, if not covered elsewhere.

Required revenue = take-home + tax set-aside + business costs. Because tax is a share of profit rather than a flat sum, work out the tax on the pre-tax figure (take-home divided by one minus the tax rate) rather than adding a fixed number. The worked version is in `references/rate-worksheet.md`.

### 3. Count the hours you can honestly bill

Start from weeks, not days: 52 weeks, minus public holidays, minus the weeks of paid leave you want, minus a sick-day allowance (five to ten days is a defensible planning figure). These are unpaid when you are freelance, which is why they belong in the divisor and not as a hope.

Then take billable hours per working week. Track every hour for four weeks in a plain log, split into billable work, sales and proposals, admin and invoicing, learning and gaps. Expect billable time to be 50-65% of a working week once those are removed; a person who has not tracked usually guesses 80% or more, and the resulting rate is too low by a quarter. If tracking is not possible yet, use 50% and say it is a planning figure.

Billable hours per year = working weeks x hours per week x billable share.

### 4. Compute the three rates

- Floor = required revenue / billable hours per year. At this rate you break even on the life you planned. Anything below it means taking work at a personal loss.
- Target = floor plus a premium for risk. Add for late payers, short or uncertain contracts, a single dominant client, and a specialised skill that is hard to replace; 15-30% is a common range and the number should be justified, not picked. The target is what you quote.
- Walk-away = the lowest rate you accept, set above the floor so that a discounted client still leaves room, and written down before any negotiation so a conversation does not set it.

If a client's hours are zero in a period, as with a reserved-capacity retainer where nothing was asked for, revenue per hour is not defined: report it as not defined and judge that client on margin against the reserved capacity.

For day rates, multiply the target hourly rate by the hours of client work a billed day contracts to deliver, and define that in the agreement (for example eight). The hourly rate already carries the unbillable share, so shortening the day would count it twice and can push the day rate below the floor.

### 5. Find the minimum project size

Each engagement carries fixed overhead: finding it, quoting, onboarding, invoicing, chasing. Estimate those hours (a small job can easily take six to ten), price them at the floor, and divide by the share of the job you are willing to lose to overhead, for example 20%. A project below that size is under-priced even at the right hourly rate. State it as an amount, and decide whether smaller jobs get a flat setup fee or a minimum charge.

### 6. Sanity-check against the market

Only now compare with what comparable freelancers charge. If the target is far above, you may be pricing a life the market will not fund, so reconsider the target income, costs or specialisation rather than quietly cutting the rate. If it is far below, you are leaving money on the table. Market rate informs the premium; it never replaces the floor.

### 7. Re-run it when an input moves

Recalculate when costs change materially, after a quarter of tracked actuals, and at each rate increase conversation. The tracked billable share is the input most likely to differ from the plan.

## What to hand back

```text
Target take-home: [amount] · Tax set-aside rate: [x%] (source)
Business costs: [amount/yr] (itemised)
Required revenue: [amount]
Working weeks: [n] · Hours per week: [n] · Billable share: [x%] (tracked / planning figure)
Billable hours per year: [n]
Floor: [rate] · Target: [rate] (premium [x%] because [reasons]) · Walk-away: [rate]
Day rate: [rate] at [n] contracted client hours per day
Minimum project size: [amount]
Market check: [range and source] · Unknowns for the accountant: [list]
```

## Anti-patterns

- **Starting from the market.** It tells you what others charge, not what you need. Start from required revenue and use the market as a check.
- **Dividing by 2,080 hours.** That is a salaried employee's paid hours. The freelancer's divisor is billable hours after leave, sickness and sales.
- **Guessing the billable share.** An untracked guess runs high. Track four weeks.
- **Forgetting employer-carried costs.** Pension, cover and equipment replacement vanish from view until they arrive as bills.
- **A day rate that undercuts the hourly rate.** Discounting the day below target hourly x contracted hours puts it under the floor.
- **Cutting the rate when the target feels high.** If the market will not pay it, change the target income, the costs or the offer, not the arithmetic.
- **Accepting a job below the minimum size.** Overhead is fixed, so the effective rate falls with the project.

## Reference files

- `references/rate-worksheet.md` — read at steps 2 to 5: a worked calculation from take-home to the three rates, the four-week tracking log layout, and the minimum-project-size formula with an example.
