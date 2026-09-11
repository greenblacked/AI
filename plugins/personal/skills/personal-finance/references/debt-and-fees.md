# Debt payoff and fee drag

Read this at steps 6 and 7: comparing payoff orders, pricing a balance transfer, and
showing what an annual charge costs over a real horizon.

## Contents

- [The arithmetic of a repayment](#the-arithmetic-of-a-repayment)
- [Avalanche against snowball, same debts](#avalanche-against-snowball-same-debts)
- [The decision rule](#the-decision-rule)
- [Balance transfer break-even](#balance-transfer-break-even)
- [Fee drag over a horizon](#fee-drag-over-a-horizon)
- [How to present a fee](#how-to-present-a-fee)

## The arithmetic of a repayment

Monthly interest is the balance multiplied by the annual rate divided by twelve. Anything
paid above that reduces the balance; anything below it increases the balance while feeling
like payment.

The minimum payment on a revolving credit card is typically set as a percentage of the
balance with a floor, which means it falls as the balance falls and the term stretches
towards decades. A 3,000 balance at 22% APR paid at a 2%-of-balance minimum takes well over
twenty years and costs more in interest than the original balance. Paying a fixed amount
rather than a percentage is, on its own, the single largest improvement available on a
card.

To compute a payoff schedule, iterate month by month rather than reaching for a closed
form — the closed form breaks as soon as the payment changes, which it does in both
methods below:

```python
def months_to_clear(balance, annual_rate, payment):
    months, paid = 0, 0.0
    while balance > 0.005:
        interest = balance * annual_rate / 12
        if payment <= interest:
            return None, None          # never clears
        balance = balance + interest - payment
        paid += interest
        months += 1
    return months, paid
```

## Avalanche against snowball, same debts

An illustrative set of consumer debts, 600 a month available in total above the minimums
plus minimums of 25 per account:

| Debt | Balance | APR |
| --- | --- | --- |
| Store card | 900 | 27% |
| Credit card A | 5,200 | 22% |
| Credit card B | 2,100 | 18% |
| Personal loan | 7,500 | 9% |

**Avalanche** targets the store card, then card A, then card B, then the loan. **Snowball**
targets the store card, then card B, then card A, then the loan — the two orders differ
only in the middle, which is typical and is why the gap is usually modest.

| Method | Total interest over the payoff | Months to debt-free | First debt cleared |
| --- | --- | --- | --- |
| Avalanche | roughly 2,900 | 28 | month 2 |
| Snowball | roughly 3,150 | 28 | month 2 |

The illustrative gap is about 250, or 8% of total interest. Two properties generalise from
this and are worth stating to the user directly: the total months to debt-free are
identical or near-identical under both methods, because the same total payment is applied
either way; and the difference is concentrated entirely in which balance the surplus
touches in the middle of the run.

The gap widens when a large balance carries the highest rate — put 12,000 at 27% at the top
of the list and avalanche pulls ahead by four figures, because the snowball leaves the
expensive balance accruing while three small ones are cleared. It narrows to near zero when
the rates are within a few points of each other.

Recompute for the user's actual debts; these figures are an illustration of shape, not a
substitute for the calculation.

## The decision rule

1. Compute both totals for the real debts.
2. Express the gap as a percentage of total repayment, not as an absolute.
3. Under about 5%: take whichever method the user will actually finish. Completion rates
   are the binding constraint, and an abandoned avalanche costs more than a completed
   snowball.
4. Above about 5%: take the avalanche, and manufacture the early win another way — chart
   the balance, or clear the smallest debt first as a single exception before reverting to
   rate order.
5. Either way, fix the total monthly payment. Both methods depend on the amount freed by a
   cleared debt rolling into the next one rather than dissolving into spending.

## Balance transfer break-even

A transfer is worth taking when the interest avoided over the promotional period exceeds
the transfer fee. Fee is typically 1-4% of the balance moved.

Break-even months = fee percentage divided by the monthly interest rate being escaped.
Escaping 22% APR (1.83% a month) with a 3% fee breaks even in under two months, so almost
any promotional period wins — provided two conditions hold.

The conditions are where transfers fail. First, the balance has to be cleared, or moved
again, before the promotional rate ends; the revert rate is usually higher than the rate
escaped. Second, new spending on the same card often does not get the promotional rate and
payments may be allocated to the cheapest balance first, so a transferred card used for
spending quietly accrues at the full rate. Treat a transferred card as closed to spending.

## Fee drag over a horizon

A portfolio growing at 5% a year before charges, with the charge deducted annually from the
whole balance. Final balance as a percentage of the zero-fee case:

| Annual charge | 10 years | 20 years | 30 years | 40 years |
| --- | --- | --- | --- | --- |
| 0.15% | 98.5% | 97.1% | 95.6% | 94.2% |
| 0.35% | 96.6% | 93.3% | 90.1% | 87.1% |
| 0.75% | 92.8% | 86.1% | 79.9% | 74.1% |
| 1.25% | 88.3% | 78.0% | 68.9% | 60.8% |
| 2.00% | 81.9% | 67.1% | 55.0% | 45.0% |

Read the difference between rows rather than a row on its own. Moving from 0.75% to 0.15%
over thirty years recovers about 16 percentage points of the final balance — on a 300,000
pot, roughly 48,000. That is a larger effect than most decisions the user is likely to
spend time on.

The mechanism worth explaining: the charge applies to the entire balance every year,
including to the growth that previous years' charges already removed, so the loss compounds
in the same way the returns do. This is also why a fee expressed as a percentage of returns
rather than of assets is a different and usually larger number.

Transaction costs, bid-offer spreads and currency conversion sit on top and are not in the
table. Where a platform charges both a percentage and a flat fee, the flat fee dominates at
small balances and the percentage dominates above roughly 20,000-50,000 — which is why the
cheapest platform changes as a pot grows, and is worth re-checking every few years.

## How to present a fee

Three numbers, together, every time:

- The percentage, as charged.
- The cash cost per year at the current balance.
- The projected cost over the remaining horizon, from the table above.

The percentage alone is what makes 1% sound like a rounding error. The cash figure is what
makes it a decision.
