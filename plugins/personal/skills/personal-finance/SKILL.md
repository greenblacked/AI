---
name: personal-finance
description: "Build an honest picture of where the money goes from real statements rather than memory, categorise it as fixed, variable and irregular-but-certain, annualise the subscriptions and yearly renewals that hide the real number, size an emergency fund against actual fixed outgoings, work the order of operations — buffer, employer pension match, debt above a threshold rate, tax-advantaged saving, then the rest — and model the specific decision before committing to it. Use this skill whenever someone asks \"where is my money actually going\", \"can I afford this\", \"should I overpay the mortgage or invest\", \"how much should I keep in savings\", wants a budget that survives contact with a real month, is choosing a debt payoff order, or is worried about fees eating a pension. Not for salary and compensation packages (offer-negotiation), cloud or infrastructure spend (cost-review), business purchasing (vendor-evaluation), or planning the week (weekly-review)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python3:*)
---

# Personal Finance

A finished session produces an annualised picture of income and outgoings that reconciles to within 5% of twelve months of real statements, a named emergency-fund target in pounds or dollars rather than months, and one decision modelled to a number the user can act on this week.

Personal money work fails in five specific ways, and none of them is arithmetic. People build the picture from memory, which reliably under-counts by the third of spending that happens in small transactions nobody recalls. They budget in monthly units, so an annual insurance renewal, a yearly domain bill and eleven monthly subscriptions never appear in the same number — the annualisation trap, and the largest single source of surprise. They size an emergency fund against take-home pay when the thing it has to cover is fixed outgoings, which overstates the target for a high earner with a cheap life and understates it for someone whose rent eats 45% of net. They optimise in the wrong order, paying down a 4% mortgage while leaving an employer pension match unclaimed, which is a guaranteed 50-100% immediate return declined. And they treat fees as a rounding error, when 0.75% against 0.15% on a portfolio held thirty years is roughly a fifth of the final balance. This skill fixes the order: real statements first, annualise everything, size the buffer against fixed costs, then run the decision through arithmetic before opinion. Personal finance is now the largest consumer app category by revenue — around 207 billion dollars in 2026, growing about 25% a year — and life-admin surveys keep putting bills and subscriptions at the centre of the reported burden, which tells you the demand is real and the tooling has not solved it.

## Scope

Use for: reconstructing spending from statements, building a budget that survives an irregular month, sizing an emergency fund, choosing a debt payoff order, deciding between overpaying debt and investing, understanding fee drag, and modelling one concrete affordability or trade-off decision.

Do not use for: salary, equity, bonus and offer decisions (`offer-negotiation`); cloud, SaaS or infrastructure spend, including "why did the bill go up" asked about a platform account (`cost-review`); company purchasing and supplier selection (`vendor-evaluation`); planning the week or pruning commitments (`weekly-review`); or nutrition and training (`health-coach`).

Do not recommend a specific fund, broker, product or individual investment. Model the structure of the decision — rate, fee, term, tax wrapper — and let the user pick the instrument.

## Where a regulated professional is actually needed

Most of this work is arithmetic and does not need one. Four situations genuinely do, and they are decision triggers rather than disclaimers:

| Trigger | Who | Why arithmetic is not enough |
| --- | --- | --- |
| A defined-benefit or final-salary pension transfer is on the table | A regulated pensions adviser | The transfer is usually irreversible and the guarantee being surrendered is hard to price; several jurisdictions require regulated advice above a threshold value. |
| Debts are unpayable at any plausible income — arrears, enforcement, or a formal insolvency route is in view | A non-profit debt adviser or insolvency practitioner | The choice between arrangement, bankruptcy and equivalents changes credit, assets and employment in ways a payoff table does not model. |
| The question turns on tax treatment across more than one country, or on a business structure | An accountant or tax adviser | Residency, double-taxation treaties and wrapper eligibility vary by country and change the answer sign, not just its size. |
| Property purchase, divorce settlement, probate or anything that moves title | A solicitor or conveyancer | The binding document is legal, not financial, and errors surface years later. |

Everything else — budgeting, buffer sizing, payoff ordering, fee comparison — is yours to do fully and numerically.

## What varies by country, and name the variable

Say which variable is unknown rather than going vague. The structure of the advice holds everywhere; these inputs do not:

- **The employer retirement match**: its existence, the match rate, and the vesting period. Ask for the rate; it is the single highest-return number in the whole picture.
- **Tax-advantaged wrappers**: ISA in the UK, 401(k) and IRA in the US, RRSP and TFSA in Canada, Superannuation in Australia. Ask which the user has access to and what the annual allowance is.
- **Statutory redundancy and sick pay**, which set how long the emergency fund has to last before other income appears.
- **Typical mortgage structure**: fixed-for-the-term is normal in the US, two-to-five-year fixes with rollover are normal in the UK, and that changes whether overpaying protects against a future rate reset.
- **Overpayment penalties**: many fixed-rate mortgages allow 10% of the balance a year penalty-free and charge a percentage beyond that. Get the number before recommending an overpayment.

## Workflow

### 1. Build the picture from real statements

Ask for twelve months of transactions from every account — current accounts, credit cards, and any account a direct debit leaves from. Twelve months, because anything shorter misses the annual renewals that are the whole point. Export to CSV and work from the file rather than a summary screen.

Reconcile before categorising: total inflows minus total outflows should equal the change in balances across the period. If it does not, an account is missing. A picture that does not reconcile is a picture that will be wrong in the direction of flattering.

If statements genuinely cannot be produced, build from three months and say explicitly that the annual items are unknown — then treat the first output as provisional.

### 2. Categorise so that the categories survive

Three buckets, and the third is the one that matters:

| Bucket | Test | What it is used for |
| --- | --- | --- |
| Fixed | The amount is the same next month whatever you do, and stopping it requires notice, a move, or a contract exit. Rent, mortgage, council tax, insurance, childcare, loan repayments. | Sets the emergency-fund target, because this is what continues when income stops. |
| Variable | You decide the amount transaction by transaction. Groceries, fuel, eating out, clothes. | The only bucket where behaviour change does anything, and the one where cuts are usually overestimated. |
| Irregular but certain | It will happen and the amount is roughly known, but not this month. Car service and tyres, annual insurance, boiler service, birthdays and holidays, professional fees, replacing a laptop every four years. | Divided by twelve and funded monthly, this is what converts "an unexpected bill" into a scheduled one. |

Resist a category list longer than about twelve. Granularity past that is never maintained, and a categorisation nobody maintains produces a picture that quietly rots. Category names should match how the user thinks, not how a bank labels merchants.

Irregular-but-certain is the bucket people omit, and its absence is what makes a budget that balances on paper fail four months in. Total it for the year, divide by twelve, and treat that monthly figure as a fixed cost.

### 3. Annualise everything before judging it

Multiply every recurring outflow to a yearly figure and sort descending. This is the step that changes minds, because monthly framing is designed to make each line look small.

Run the subscription audit against the statement rather than memory: list every recurring merchant, its annual cost, and the date of last use. Anything not used in ninety days is a cancellation candidate. Annual renewals that auto-charge are worth a calendar reminder set seven days before the charge, which is the only reliable way to make a renewal a decision.

Then compute the two numbers that matter:

- **Annual fixed outgoings** — the emergency-fund denominator.
- **Annual surplus** = net income minus all three buckets. If this is negative, every other question is secondary; the picture is a spending problem or an income problem and should be named as one.

### 4. Size the emergency fund against fixed outgoings

The generic "three to six months" is a range about income, and income is the wrong denominator. Size it as a multiple of monthly fixed outgoings plus a stripped-down variable floor — typically 60-70% of current variable spend, because in a real income shock discretionary spending falls but does not vanish.

| Situation | Months of fixed outgoings plus floor | Why |
| --- | --- | --- |
| Two earners, both in stable salaried roles, no dependants | 3 | Both incomes failing simultaneously is unlikely, and one salary usually covers fixed costs. |
| Single earner, salaried, dependants or a mortgage | 6 | One point of failure, and the fixed costs cannot be shrunk quickly. |
| Contractor, freelance, commission-heavy, or in a sector with long hiring cycles | 9-12 | Re-employment time is the driver, and it is measured in quarters rather than weeks. |
| Owns a home older than about twenty-five years, or a car past warranty | Add one month | The irregular-but-certain bucket has a fat tail: a boiler or a gearbox is a four-figure event. |

State the target as an absolute amount, not a number of months. "Eleven thousand four hundred" is a goal; "six months" is a conversation.

Hold it somewhere instantly accessible and separate from the current account. Whether an instant-access savings account, a money-market fund or a notice account is right depends on the local rate and tax treatment — name the trade-off, not the product.

### 5. Apply the order of operations

Most credible guidance converges on this order. Follow it, and say which step the user is on:

1. **A small starter buffer** — roughly one month of fixed outgoings, or a flat 1,000 in local currency. Its job is to stop the next small shock becoming new debt while the rest of the plan runs.
2. **Any employer retirement match, up to the full match.** Contributing enough to capture a 50% match is an immediate 50% return on that money, before any market return. Nothing else in the list beats it. Skipping this to pay down a 20% credit card is still wrong: the match is claimed once per year and lost permanently.
3. **Debt above roughly 8% interest, highest rate first.** Eight per cent is the working threshold because it sits above the long-run real return most people should plan on for a diversified portfolio (about 5-7% nominal after inflation is a common planning assumption, and the point is that certain 8% beats uncertain 7%). Credit cards at 20-25% APR and most personal loans are comfortably above it.
4. **Fill the emergency fund to the step-4 target.**
5. **Tax-advantaged saving to the annual allowance** — the wrapper depends on the country, per the list above. A wrapper is worth roughly the tax rate on the gains it shelters, which for a higher-rate taxpayer over decades is a larger effect than most fund-selection decisions.
6. **Everything else**: debt between about 4% and 8% (a genuine toss-up, decide on temperament), taxable investing, mortgage overpayment, and specific goals with dates.

Debt below roughly 4% is usually not worth accelerating while step 5 has headroom, with one exception: a variable-rate or short-fix debt whose rate can reset upward is a risk, not just a cost, and paying it down buys certainty.

### 6. Choose a debt payoff order and be honest about the trade

Two orders, and the comparison is arithmetic on one side and psychology on the other.

**Highest rate first (avalanche)** minimises total interest. It is the cheaper method, always, by construction.

**Smallest balance first (snowball)** clears individual debts sooner, which produces visible wins earlier and, in the behavioural literature, correlates with higher completion rates.

Compute both for the user's actual debts and show the two totals side by side. The gap is usually smaller than people expect — on a typical mix of three to four consumer debts it is often a few hundred over the life of the payoff, and it widens sharply when one large balance carries a much higher rate than the rest. Decide with this rule: if the interest gap is under about 5% of the total repayment, take whichever the user will finish; if it is above that, take the avalanche and make the first win visible another way.

Worked examples of both orders on the same debts are in `references/debt-and-fees.md` — read it when running the comparison or explaining why the totals differ.

Before either: check whether a balance transfer or consolidation at a lower rate is available, and price the transfer fee into the comparison rather than looking only at the headline rate.

### 7. Show the fee drag over the real horizon

Fees are the one cost in the picture that compounds against the user for decades, and the only one they can change with a single form.

On a portfolio contributed to steadily over thirty years, the difference between a 0.75% and a 0.15% annual charge is roughly 15-20% of the final balance. The mechanism is that the fee is charged on the whole balance every year, including on the growth the previous years' fees already removed.

Always express fees three ways at once: the percentage, the pounds or dollars per year at the current balance, and the projected cost over the remaining horizon. The percentage alone is what makes a 1% charge sound like a rounding error.

Check platform fee, fund charge and any transaction or exit cost separately — a low headline fund charge on an expensive platform is a common shape.

### 8. Model the decision the user actually brought

The picture is input; the decision is the output. Model it explicitly:

- State the decision as a comparison between two named alternatives, including "do nothing", which is a real option and usually the incumbent.
- Write down every input with its source and whether it is known or assumed.
- Compute the outcome over a stated horizon for each alternative.
- Run the downside case: income falls, the rate resets, the roof needs replacing. A decision that only works in the central case is a bet, and it should be labelled as one.
- Name what would change the answer — the rate crossing a level, the match ending, a move.

Arithmetic patterns for the common decisions — overpay against invest, rent against buy, lump sum against instalments, fixed against variable — are in `references/decision-models.md`, along with the sensitivity checks each needs. Read it when the user brings a specific trade-off rather than a general picture.

Categorisation heuristics, statement-extraction tactics and the annualisation worksheet are in `references/cashflow-worksheet.md` — read it at step 1 or 2, when turning a pile of CSV exports into buckets.

## Output format

```text
## The picture
Period covered: [months] · Reconciles to within [x]%
Net income (annual): [amount]
Fixed: [amount]/yr ([x]% of net) · Variable: [amount]/yr · Irregular-but-certain: [amount]/yr
Annual surplus: [amount] ([x]% of net)

## Annualised, largest first
| Item | Monthly | Annual | Last used | Verdict |
| [name] | [amount] | [amount] | [date or n/a] | keep / cancel / renegotiate |

## Emergency fund
Monthly fixed outgoings: [amount] · Stripped variable floor: [amount]
Target: [absolute amount] ([n] months) · Currently held: [amount] · Gap: [amount]
Reason for [n]: [the row from the sizing table that applies]

## Where you are in the order of operations
Step [n]: [name]. Next action: [specific, with an amount]
Unclaimed employer match: [amount/yr, or "none available"]

## Decision modelled
Question: [as the user asked it]
Option A: [name] → [outcome over horizon]
Option B: [name] → [outcome over horizon]
Difference: [amount] over [years]
Assumptions: [each, marked known or assumed]
Downside case: [what happens if the main assumption is wrong]
This flips if: [the condition]

## Needs a regulated professional
[trigger from the table, and who — or "none of the triggers apply"]
```

## Anti-patterns

- **Budgeting from memory.** Self-reported spending under-counts by a wide margin, concentrated in small and frequent transactions, so the resulting budget balances on paper and fails in month two. Export twelve months and reconcile to the balance change.
- **The monthly frame.** Eleven subscriptions at nine a month and one annual renewal at two hundred never appear in the same number, so the total is never seen. Annualise every recurring line before judging any of it.
- **Sizing the buffer against income.** Income is what stops; fixed outgoings are what continue. A high earner with low fixed costs is told to hold far too much, and someone whose rent is 45% of net is told to hold far too little.
- **Paying down cheap debt while an employer match goes unclaimed.** A 50% match declined to overpay a 4% mortgage is a guaranteed loss of about 46 percentage points, and the match cannot be claimed retroactively.
- **Treating fees as a rounding error.** A 0.6 percentage point difference in annual charges costs roughly a fifth of the final balance over thirty years. Quote every fee as a percentage, an annual amount, and a lifetime cost together.
- **Optimising the small line while the large one is unexamined.** Cancelling a streaming service saves about a hundred a year; refinancing a mortgage, changing a commute, or moving a pension platform moves thousands. Sort by annual amount and work from the top.
- **A plan with no downside case.** Every projection that assumes continuous income and no large repair is a bet presented as arithmetic. Run the shock before committing.
- **Recommending a product.** A specific fund, broker or account is outside what this can responsibly do and dates badly. Model the rate, fee, term and wrapper; let the user choose the instrument.
- **Carrying an unreconciled picture forward.** If inflows minus outflows does not match the balance change, an account is missing and every ratio computed from it is wrong. Fix the reconciliation before continuing.
- **Confusing a surplus with savings.** A surplus that is never moved out of the current account is spent, reliably, within two months. The plan needs a standing transfer on payday, not an intention.

## Reference files

- `references/cashflow-worksheet.md` — read at steps 1 and 2, when turning statement exports into categories: extraction tactics per account type, the twelve-category default list, rules for classifying an ambiguous merchant, the irregular-but-certain checklist, and the reconciliation check.
- `references/debt-and-fees.md` — read at steps 6 and 7: amortisation arithmetic, the same debt set worked through avalanche and snowball with both totals, balance-transfer break-even, and fee-drag tables at several charge levels and horizons.
- `references/decision-models.md` — read at step 8 when a specific trade-off is on the table: overpay against invest, rent against buy, lump sum against instalments, fixed against variable rate, each with its inputs, its sensitivity check and the condition that flips it.
