---
name: year-end-tax-pack
description: "Assemble everything an accountant or tax return needs, in dependency order: reconcile every bank, card and payment-processor account to statements, reconcile total invoiced income to deposits and explain each difference, clear uncategorised and personal items, check receipts above your tax authority's substantiation threshold, then compile asset purchases and disposals, mileage and home-office logs, loans, owner contributions and draws, receivables and payables and the prior-year return. Ends in a one-page index plus a gap list naming who fixes each item. Use for 'getting ready for my tax return', 'what do I send my accountant', 'year-end paperwork for a small business', 'I have a shoebox of receipts'. Procedure, not tax advice. Not for the monthly routine (monthly-bookkeeping-close), how much to save (tax-set-aside) or personal planning (personal-finance)."
allowed-tools: Read, Glob, Grep
---

# Year-End Tax Pack

A pack is done when an accountant can prepare the return without asking you a question: every account reconciled, income explained, expenses supported, and a one-page index that says where each document is and what is still missing.

The usual failure is order. People start by sorting receipts, then discover the bank balance does not match the books, then discover that income in the books is not what hit the bank. Each later step sits on the earlier ones, so a receipt hunt done before reconciliation is redone. Work down the dependency chain and the gaps surface once.

## Scope

Use for: closing a tax year for a sole trader, freelancer or small company; preparing the handover to an accountant; catching up several years of unsorted records.

Do not use for: the monthly close this builds on (`monthly-bookkeeping-close`); how much to set aside and when payments fall due (`tax-set-aside`); household or personal financial planning (`personal-finance`). Thresholds, deadlines, what is deductible and what a return contains depend on your country and entity type; take each from your tax authority's own pages or your accountant. This is procedure, not tax advice.

## Workflow

### 1. Fix the period and list the accounts

Confirm the tax year start and end dates with the accountant or the authority. List every account that touched business money in that period: bank, credit and debit cards, payment processors and marketplaces, cash, loan and director or owner accounts, and any closed during the year. A forgotten processor account is a forgotten slice of income.

### 2. Reconcile every account to its statement

For each account, match the closing balance in the books to the statement balance at year end, and the opening balance to last year's close. Investigate any difference before moving on. Request statements for any month you lack; most banks and processors export a full year. Detail is in `references/pack-workpapers.md`.

### 3. Reconcile income to deposits

Total invoiced income for the year, plus income taken outside invoices, should equal deposits received plus the change in unpaid receivables, after explained differences. Walk the gap line by line and name each cause: processor fees netted off, refunds, sales tax or VAT collected and held, foreign-currency movement, deposits for next year, owner money paid in. An unexplained remainder is the first item on the gap list, because it is what an inspector finds first.

### 4. Clear the uncategorised and the personal

Empty the uncategorised bucket. Split anything personal that went through the business accounts into owner draws or reimbursements (see `finance-separation-cleanup` if it is widespread). Do not guess a category for an item you cannot explain; list it for the owner.

### 5. Check receipts against the threshold

Look up your tax authority's substantiation rule: the amount above which an expense needs a receipt or invoice, and what that document must show. Test every expense above it, plus every unusual category, and mark each as supported, replaceable (ask the supplier for a copy) or unsupported. Do not recreate a receipt after the fact.

### 6. Compile the schedules

Gather these, each as a short list or log with source documents:

- Asset purchases and disposals: date, cost, description, proceeds.
- Vehicle mileage log or actual-cost records, and home-office measurements and bills, if you claim either.
- Loans: lender, opening and closing balance, interest paid.
- Owner contributions and draws, by date.
- Receivables and payables at year end, each with a name, an amount and an age.
- Stock or work in progress at year end, if relevant to your entity.

### 7. Add the context documents

Include the prior-year return and its notice of assessment or equivalent, letters from the tax authority, registration numbers, payments already made towards this year's tax, and any pension, grant or insurance statements. Add a note of anything unusual: new entity, a sale of an asset, a move, a change of accountant.

### 8. Build the index and gap list

Write the one-page index and the gap list from the layout below, then send the pack with the gap list on the first page. Each gap names the item, why it matters, who must fix it and by when. Nothing is "to do"; every line has an owner.

## What to hand back

```text
Tax year: [start - end]
Index (one page): [section - document - location - status]
Accounts reconciled: [account - statement balance - books balance - difference - explained]
Income reconciliation: [invoiced - deposits - receivables change - explained items - unexplained]
Receipts: [count over threshold - supported - replaceable - unsupported]
Schedules: [assets, mileage, home office, loans, owner flows, receivables, payables]
Gap list: [item - why it matters - owner - due date]
```

## Anti-patterns

- **Sorting receipts first.** If the accounts do not reconcile, the receipts are the wrong problem.
- **Plugging a difference.** An unexplained amount booked to "miscellaneous" hides the question the accountant will ask.
- **Recreating missing receipts.** Ask the supplier for a copy or list it as unsupported.
- **Sending a folder with no index.** The accountant spends the first hours working out what is in it.
- **Adding a deduction you cannot defend.** Ask the accountant; they own the treatment.

## Reference files

- `references/pack-workpapers.md` — read at steps 2, 3, 5 and 8: the reconciliation worksheet, the income walk with common causes, the receipt test, and the index and gap list layouts.
