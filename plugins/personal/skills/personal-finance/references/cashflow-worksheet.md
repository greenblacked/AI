# Cashflow worksheet

Read this when turning statement exports into a categorised, annualised picture — steps 1
and 2 of the workflow.

## Contents

- [Getting the data out](#getting-the-data-out)
- [The reconciliation check](#the-reconciliation-check)
- [The twelve-category default](#the-twelve-category-default)
- [Classifying an ambiguous merchant](#classifying-an-ambiguous-merchant)
- [The irregular-but-certain checklist](#the-irregular-but-certain-checklist)
- [The annualisation sheet](#the-annualisation-sheet)
- [When only three months exist](#when-only-three-months-exist)

## Getting the data out

Twelve months, every account money leaves from. Three months misses every annual renewal,
which is the item the exercise exists to find.

| Source | How to export | The trap |
| --- | --- | --- |
| Current account | CSV from online banking, usually capped at 12-24 months per download. | Date format varies by locale; check whether the first row is 01/02 meaning January or February before summing anything. |
| Credit card | CSV per card. Statement periods do not align with calendar months. | Paying the card from the current account appears as an outflow in both files. Count the card transactions and exclude the payment, or you double-count every purchase. |
| Digital wallet or payment app | Export separately; many transactions show only as a wallet top-up on the bank statement. | A single "top-up" line hides a dozen purchases, which is exactly the spending memory already under-counts. |
| Joint account | Export in full, then apportion by whatever split the household actually uses. | Apportioning by an assumed 50/50 when the real split is 70/30 breaks every per-person ratio downstream. |
| Cash withdrawals | Cannot be itemised. Treat the total as one variable line called "cash". | Treating cash as unknown rather than as spending flatters the surplus. |

Normalise to one file with four columns: date, description, amount signed, account. Do the
categorisation on that file, not on six separate ones.

## The reconciliation check

For each account: opening balance plus inflows minus outflows should equal the closing
balance. Across all accounts the same identity holds for total net worth change in cash.

If it does not close to within about 1%, one of four things is true, in descending order of
likelihood: an account is missing, the credit card payment is double-counted, a transfer
between own accounts is being counted as spending, or the export is truncated. Fix it
before categorising. A picture that does not reconcile is wrong in the flattering
direction, because the missing account is usually the one the awkward spending is on.

Internal transfers between the user's own accounts are neither income nor spending. Tag
them and exclude them; they are the second most common source of a picture that does not
close.

## The twelve-category default

More than about twelve categories is never maintained. Start here and rename to match how
the user thinks:

Housing · Utilities and communications · Insurance · Transport · Groceries · Eating out and
drinks · Health · Childcare and education · Subscriptions and memberships · Shopping and
clothes · Gifts, holidays and occasions · Debt repayments.

Each category is tagged fixed, variable or irregular-but-certain. Some split: car insurance
is irregular-but-certain, fuel is variable, a car loan is fixed — all three sit under
Transport, and the bucket tag rather than the category is what the emergency fund uses.

## Classifying an ambiguous merchant

| Question | If yes | If no |
| --- | --- | --- |
| Would it still be charged next month if the user changed nothing and also did nothing? | Fixed. | Ask the next question. |
| Does it happen at least once a year with a roughly predictable amount? | Irregular but certain. | Variable. |
| Is it a single supermarket line covering food, cleaning products and a bottle of wine? | Do not split it. Put the whole line in Groceries and accept the noise; splitting supermarket receipts is the single fastest way to abandon the exercise. | — |
| Is it a merchant name that means nothing (a payment processor, a parent company)? | Look up one instance, then apply the mapping to every matching line at once. | — |

Build the mapping as rules on the description field rather than transaction by
transaction. Twelve months is typically 1,500-3,000 lines; roughly forty rules will cover
90% of them.

## The irregular-but-certain checklist

Walk this list explicitly. Anything the user answers yes to gets an annual amount and a
month, divided by twelve into the monthly picture.

Car: service, tyres, roadworthiness test, tax, insurance renewal. Home: insurance renewal,
boiler or heating service, chimney, gutter, appliance replacement, a decorating cycle.
Personal: professional membership and registration, licences, passport and visa renewals,
optician and dentist, prescription costs. People: birthdays, an annual religious or
seasonal occasion, weddings in a year where several are known, school uniform and trips.
Technology: phone replacement cycle, laptop replacement cycle, domain and storage renewals.
Money: annual platform fees, accountant's fee, a tax payment on account.

The replacement cycles are the ones people leave out. A laptop at 1,400 replaced every four
years is 350 a year whether or not it is set aside, and pretending otherwise converts a
scheduled cost into an emergency.

## The annualisation sheet

One row per recurring item, sorted by the annual column descending:

| Column | Notes |
| --- | --- |
| Item | Merchant as it appears on the statement, plus what it actually is. |
| Frequency | Monthly, quarterly, annual, per-use-with-a-count. |
| Unit amount | As charged. |
| Annual | Unit multiplied out. This is the only column to sort or argue about. |
| Last used | From the user, or from usage evidence. Blank means unknown, which is itself a finding. |
| Renews on | The date the next charge lands. Needed for a cancellation reminder. |
| Verdict | Keep, cancel, downgrade, renegotiate. |

Rules that make the sheet decide things rather than describe them: nothing used in ninety
days is a cancellation candidate by default; anything above about 2% of net income gets a
renegotiation attempt before a cancellation; every annual renewal gets a calendar reminder
seven days before the charge date, because a renewal without a reminder is not a decision.

## When only three months exist

Say so in the output. Then: multiply the three months of fixed and variable by four, and
build the irregular-but-certain bucket from the checklist above by asking rather than from
data. Mark the resulting annual figure as provisional with an expected error of 10-20% on
the low side, and schedule a rebuild once twelve months of history is available. A
provisional picture stated as provisional is useful; the same picture stated as fact
produces a plan that fails at the first annual renewal.
