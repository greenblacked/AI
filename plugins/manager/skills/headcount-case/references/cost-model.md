# Cost model

Read this when pricing the ask: the cost layout over 12 and 24 months, the ramp
arithmetic and a worked example. All figures in the example are illustrative; replace
them with the company's own and ask the finance partner for the loading factor.

## In this file

- Cost lines
- Ramp arithmetic
- A worked example
- Backfill adjustments

## Cost lines

| Line | Source | Label |
| --- | --- | --- |
| Base pay | Band midpoint for the level, from the compensation team | Measured |
| Bonus and equity | The company's usual accrual for the level | Estimated |
| Taxes and benefits | Finance loading factor, applied to base | Measured |
| Recruiting | Agency fee (a percentage of first-year base) or internal recruiter cost per hire | Measured or estimated |
| Equipment and seats | IT price list, licences per head | Measured |
| Onboarding time | Mentor hours multiplied by the mentors' loaded hourly cost | Estimated |
| Vacancy | Months from approval to start, valued as the cost in step 2 of the case | Estimated |

Show year one and year two separately. Recruiting and equipment fall wholly in year one,
so year two is the better guide to the steady cost, and a reader who sees only year one
will overstate the long-run figure.

## Ramp arithmetic

Express productivity as a share of a fully ramped engineer in the same role.

| Month after start | Hire's productivity | Mentor time consumed |
| --- | --- | --- |
| 1 | 10 to 20 percent | 20 to 30 percent of one engineer |
| 2 to 3 | 30 to 50 percent | 10 to 20 percent of one engineer |
| 4 to 6 | 60 to 90 percent | up to 10 percent of one engineer |
| 7 onward | 100 percent | none |

These shares are assumptions; replace them with the team's own history (time to first
merged change, time to first on-call shift) where it exists, and say so. Net capacity in
a month is the hire's productivity minus the mentor time. The benefit date is the first
month where cumulative net capacity, valued at the loaded cost per engineer-month,
exceeds cumulative spend.

## A worked example

One engineer, base 120,000, loading factor 1.30, recruiting at 20 percent of base,
equipment 4,000, starts three months after approval (month 4).

- Year one cost: 120,000 x 1.30 = 156,000 per year, so nine working months of year one
  after the vacancy gap are 117,000, plus recruiting 24,000 plus equipment 4,000 = 145,000.
- Year two cost: 156,000.
- Cumulative 24 months from approval: about 301,000.
- Under the ramp table, the hire's net capacity is below zero in month 1, since the
  mentor time exceeds the hire's output, and turns positive from about month 2 to 3. The
  cumulative benefit passes cumulative spend much later, so compute that date rather than
  quoting the month net capacity turns positive.

State the arithmetic in the document so a reader can change an input and see the result.

## Backfill adjustments

A backfill changes the baseline, not the arithmetic. The salary line is often lower than
the departing person's, but the vacancy cost is real: months of the role unfilled, the
overtime or contractor cover paid meanwhile and the knowledge lost on departure. Ask
whether the role is still the right shape before re-opening it unchanged. If the answer
is that the work has changed, the case is a new role.
