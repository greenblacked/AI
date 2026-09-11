# Decision models

Read this at step 8, when the user brings a specific trade-off rather than a general
picture. Each model names its inputs, the arithmetic, the sensitivity check, and the
condition that flips the answer.

## Contents

- [How to run any of these](#how-to-run-any-of-these)
- [Overpay debt against invest](#overpay-debt-against-invest)
- [Rent against buy](#rent-against-buy)
- [Lump sum against instalments](#lump-sum-against-instalments)
- [Fixed against variable rate](#fixed-against-variable-rate)
- [Can I afford this](#can-i-afford-this)
- [The downside case](#the-downside-case)

## How to run any of these

State the two alternatives by name, including "change nothing" where that is the
incumbent. List every input with its source, marked known or assumed. Compute over a stated
horizon. Then run the downside case and name the condition that flips the answer. A model
with no flip condition has not been understood, only calculated.

Work in nominal terms and state the inflation assumption separately, or work in real terms
throughout — mixing the two is the most common arithmetic error in this whole area.

## Overpay debt against invest

**Inputs**: debt rate and whether it is fixed or resettable; overpayment allowance and the
penalty beyond it; the tax wrapper available for the alternative and its remaining
allowance; marginal tax rate; whether an employer match is unclaimed; horizon.

**Arithmetic**: overpaying returns the debt rate, certain and tax-free. Investing returns an
uncertain rate, taxed outside a wrapper. The comparison is therefore debt rate against
expected after-tax return, with a risk adjustment in favour of the certain side.

**The rule that decides most cases**: an unclaimed employer match beats both, always, and is
handled before the question is asked. Above roughly 8% debt, overpay. Below roughly 4%,
invest inside a wrapper. Between the two, it is genuinely close and temperament decides —
say so rather than manufacturing precision.

**Sensitivity**: the answer moves with the assumed return more than with anything else. Run
it at a pessimistic return as well as a central one; if the answer changes sign, the
decision is a bet on returns and should be labelled as one.

**Flips if**: the debt is on a fix that expires inside the horizon and could reset upward,
which converts the overpayment from a return into insurance; the overpayment exceeds the
penalty-free allowance, which can cost more than the interest saved; or the wrapper
allowance is about to expire unused — confirm that it expires before treating the deadline
as real. A UK ISA allowance and the US 401(k) and IRA contribution limits are lost at the
end of the year, but unused Canadian RRSP and TFSA room carries forward indefinitely, and
the UK pension annual allowance can be carried forward three years.

## Rent against buy

**Inputs**: purchase price, deposit, mortgage rate and term, purchase costs (tax on the
transaction, legal, survey, moving), annual ownership costs (maintenance at roughly 1% of
property value a year, insurance, service charge and ground rent where they apply),
expected sale costs, comparable rent, the return available on the deposit if not spent, and
expected years in the property.

**Arithmetic**: compare total cost of occupation, not mortgage payment against rent. Cost of
occupation when owning is interest plus maintenance plus insurance plus transaction costs
amortised over the years held plus the forgone return on the deposit, minus any capital
appreciation. Capital repayment is not a cost; it is saving, and counting it as a cost is
the standard error in the other direction.

**The number that decides it**: years to break even on transaction costs. Buying and selling
commonly costs 5-10% of value in total across both transactions, which is several years of
the difference between renting and owning. Below roughly five years in the property, the
transaction costs usually dominate every other term.

**Sensitivity**: to the years held first, the mortgage rate second, house price growth third.
House price growth is the input people vary most and should trust least.

**Flips if**: the stay is shorter than the break-even; the deposit would otherwise capture an
unclaimed match or fill an empty wrapper allowance; or the maintenance assumption is wrong,
which it usually is on an older property.

**Country variables**: transaction tax varies enormously, mortgage interest may or may not be
deductible, and a fixed-for-the-term mortgage removes the rate-reset risk that dominates a
short-fix market. Ask which applies before computing.

## Lump sum against instalments

**Inputs**: cash price, instalment amount and count, any fee, the stated APR, and the return
available on cash not spent.

**Arithmetic**: a genuine 0% instalment plan with no fee is free credit, and taking it while
holding the cash in an interest-bearing account is worth the interest earned over the term.
Anything with an APR is a loan; compute the total repaid and compare to the cash price. The
total repaid is the number the advertising omits.

**The trap**: instalments are quoted monthly to make the total invisible, and they raise the
price ceiling of what feels affordable. Compute the total before comparing options at all,
and compare options on cash price even when buying on instalments.

**Flips if**: missing a payment triggers a retroactive interest charge on the whole balance,
which some deferred-interest plans do and which reprices the deal entirely; or the cash
would otherwise sit below the emergency-fund target, in which case keeping the cash and
taking free credit is the safer side.

## Fixed against variable rate

**Inputs**: current fixed rate and term available, current variable rate, the size of the
balance, the user's capacity to absorb a payment increase, and the exit fee on the fix.

**Arithmetic**: compute the payment at the fixed rate, at the current variable rate, and at
the variable rate plus two and four percentage points. The question is not which rate is
lower today — it is whether the higher scenario is survivable given the budget picture
built at step 3.

**The framing that gets this right**: a fix is insurance with a known premium, which is the
gap between the fixed rate and today's variable rate. Decide whether the premium is worth
paying, not whether rates will rise; forecasting rates is not the user's job and nobody
reliably does it.

**Flips if**: the fixed term ends well before the debt does and the reset lands at an
unknown rate, which shifts rather than removes the risk; or the exit fee makes an early
move prohibitive, which matters when a house move is likely inside the term.

## Can I afford this

The most common question, and it needs three tests rather than one:

| Test | Passes when | Fails because |
| --- | --- | --- |
| Cash test | The purchase can be paid from surplus or from savings above the emergency-fund target. | Paying from the emergency fund converts a planned purchase into an uninsured risk. |
| Run-rate test | The ongoing cost fits in the annual surplus with the surplus still positive. | A one-off price hides a recurring cost — insurance, maintenance, a subscription tail. |
| Displacement test | Naming what this purchase displaces, and the user accepting the trade. | Nothing named means the money is coming from a goal that has not been told. |

All three, or the answer is not yes. Report which one failed rather than reporting "no".

## The downside case

Run every model a second time under one of these, chosen for the user's situation: income
falls to statutory levels for six months; the rate resets three points higher; a four-figure
irregular cost lands in the same quarter; or the asset is worth 20% less when it has to be
sold.

The output is one sentence: what happens, and whether the plan survives it. A decision that
works only in the central case is a bet, and the user is entitled to know they are taking
one.
