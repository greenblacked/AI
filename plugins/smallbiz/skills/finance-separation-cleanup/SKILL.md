---
name: finance-separation-cleanup
description: "Untangle personal and business money that have been mixed. Stop the bleed first: open a business account and card, route client payments there, move recurring costs to it. Then clean history in order: export 12 months of all accounts, tag each transaction business, personal or mixed, record a business percentage with its basis for mixed items, book personal spending paid by the business as owner draws and business spending paid personally as contributions or reimbursements, and never reclassify without a source document. Ends with one fixed monthly transfer to pay yourself. Use for 'I used my personal account for business', 'mixing personal and business expenses', 'my accountant says my books are commingled'. Procedure, not tax advice. Not for the routine once separated (monthly-bookkeeping-close), household budgets (personal-finance) or personal admin (life-admin)."
allowed-tools: Read, Glob, Grep
---

# Finance Separation Cleanup

Separation is done when new business money no longer touches a personal account, twelve months of history are tagged with a source document behind every classification, the owner's balance with the business is a single dated figure, and a monthly transfer pays you a fixed amount.

The usual failure is cleaning up the past while the mixing continues. A tidy spreadsheet of last year is out of date by the end of the month if client payments still land in the personal account. Stop new mixing first, then fix history; and fix it by recording what happened, never by relabelling it so the numbers look better.

## Scope

Use for: a freelancer or small owner who has run the business through personal accounts or cards, a new business starting from a mixed history, or an accountant's complaint that books are commingled.

Do not use for: the monthly routine once money is separated (`monthly-bookkeeping-close`); household budgets (`personal-finance`); personal paperwork and admin (`life-admin`). Whether an item is deductible, how drawings and contributions are treated, and whether a legal entity changes any of this depend on your country and entity type; confirm with the accountant before filing. This is procedure, not tax advice.

## Workflow

### 1. Stop the bleed

Do these before any cleanup:

1. Open a business bank account, and a business card if you can. Use the legal or trading name you invoice under; ask the bank what it requires.
2. Change the bank details on invoice templates and tell clients with open invoices in writing, confirming the new details by a second channel, since payment-detail changes are a known fraud route.
3. Point payment processors and marketplaces at the new account.
4. Move subscriptions and recurring business costs to the business card: software, hosting, phone if you will claim it, insurance, professional fees.
5. Set a rule for the personal card: nothing for the business, and if it happens, record it that day.

### 2. Export the whole unfiled period

Export transactions from every personal and business account, card and processor from the start of the earliest tax year not yet filed or the last twelve months, whichever reaches further back. Put them in one sheet with columns: date, account, description, amount, source document, tag, business percentage, basis, treatment. Keep the original exports unedited in a separate folder.

### 3. Tag each transaction

Tag every line as business, personal or mixed. Where you cannot tell from the description, find the source document: invoice, receipt, contract or calendar entry. If none exists, tag it unsupported and list it for the accountant instead of choosing the favourable answer. Read `references/separation-workpapers.md` for the tagging rules and examples.

### 4. Set a percentage for mixed items

For a mixed cost such as a phone, internet connection, home office or vehicle, record the business share and how you arrived at it: a logged usage period, a floor-area measurement, a mileage log. Apply the same percentage consistently. A percentage with no basis is a guess, and a guess that favours you is the one an inspector reverses.

### 5. Book the owner flows

Record the direction of each mismatch:

- Personal spending paid from business money is an owner draw.
- Business spending paid from personal money is an owner contribution, or a reimbursement owed to you.

Sum each, and net them into one running owner balance with the business. When the business owes you, settle it with a single dated reimbursement from the business to you. When you owe the business, repayment applies only where the entity treats the amount as owed (for example a company); for a sole trader, draws are recorded and not repaid. Send the decision to the accountant before any transfer, then keep the transfer record. Treatment of draws and contributions depends on the entity.

### 6. Never reclassify without a source document

A reclassification needs a document that shows what the item was, not a memory of it. Change the treatment column, not the original line, and note the document. Do not delete transactions or edit the exports. The audit trail is the value of the exercise.

### 7. Set the standing rule

Pay yourself with one transfer a month, of a fixed amount, from the business account to the personal one, on the same day. Size it from average profit less tax set aside (`tax-set-aside`), then review it quarterly. Any other movement between the accounts is a recorded draw, contribution or reimbursement, not an informal transfer.

### 8. Review with the accountant

Send the tagged sheet, the percentages with their bases, the owner balance and the unsupported list, and ask how each flow should be treated for your entity. Then begin the monthly routine.

## What to hand back

```text
Stop-the-bleed checklist: [done / outstanding with date]
Tagged sheet: [count business / personal / mixed / unsupported]
Mixed items: [item - percentage - basis]
Owner balance: [draws total - contributions total - net owed, direction]
Settlement transfer: [date - amount - direction - label]
Standing rule: [amount - day of month]
Questions for the accountant: [list]
```

## Anti-patterns

- **Cleaning the past first.** New mixing continues and the work is stale by month end.
- **Reclassifying from memory.** Without a document it is an opinion.
- **Editing or deleting bank lines.** Add a treatment column and leave the record intact.
- **Guessing a business percentage.** Log a period or measure, then apply it consistently.
- **Informal top-ups and withdrawals.** Each one is an owner flow; record it the day it happens.
- **Telling clients the new bank details by one email only.** Confirm by a second channel.

## Reference files

- `references/separation-workpapers.md` — read at steps 3, 4 and 5: tagging rules with examples, how to document a mixed percentage, and the owner balance worksheet.
