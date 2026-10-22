---
name: invoice-hygiene
description: "Issue invoices that get paid quickly and survive an audit: send on the day of the trigger event, not at month end, after checking a gapless sequential number, the client's legal name and billing address, PO number, an itemised description matching the SoW milestone, tax line and registration numbers where required (verified from your tax authority), currency, a due date written as a date not 'net 30', bank details with a payee-name match, and the late-payment rule. Send to accounts payable, check portal or e-invoicing rules, and fix a sent invoice with a credit note and a new one. Use for 'what must an invoice include', 'client says they never got the invoice', 'invoice rejected by accounts payable'. Not for deposits and milestones (fixed-price-quote), chasing after the due date (late-payment-chase) or recording it (monthly-bookkeeping-close)."
allowed-tools: Read, Glob, Grep
---

# Invoice Hygiene

An invoice is done when it reaches the person who pays it, matches what the client's finance team needs to book it, and can be explained to an auditor line by line years later.

Most slow payment is not refusal but friction. The invoice went to the project contact who forwarded it nowhere, the legal name was a trading name, the PO number was missing, or the due date said "net 30" and nobody knew from when. Each defect restarts the client's approval clock, and the freelancer finds out three weeks later. Fix the invoice before it leaves and the chase never starts.

## Scope

Use for: building, checking, sending and correcting an invoice; setting a numbering scheme and a sending routine; working out why an invoice was rejected or never arrived.

Do not use for: choosing deposits, milestones and when work becomes billable (`fixed-price-quote`); chasing once the due date has passed (`late-payment-chase`); recording the invoice in the books (`monthly-bookkeeping-close`). A dispute over the amount belongs to `invoice-dispute-resolution`. What an invoice must legally contain differs by country and sometimes by client type, so verify it on your tax authority's page. This is procedure, not tax or legal advice.

## Workflow

### 1. Send on the trigger event

Invoice on the day the event in the statement of work occurs: milestone accepted, month of retainer ended, deposit date reached. A month-end batch delays cash by weeks and loses the link between the invoice and the work, which is the first thing an approver checks. Put the triggers in your calendar when the SoW is signed.

### 2. Run the pre-send checklist

Do not send until every line holds. The longer version with the reason for each is in `references/invoice-checklist.md`.

- Number: unique, sequential and without gaps, from one series. A gap invites the question of what happened to the missing invoice.
- Client: the legal entity name and billing address exactly as their finance team holds them, taken from the contract or a supplier form, not from an email signature.
- Reference: the PO number, cost centre or contract reference if the client uses one. Ask for it before the work starts.
- Description: itemised, naming the SoW milestone or period, so an approver can match it to what they ordered.
- Tax: the tax line and both registration numbers where your jurisdiction requires them. Look up the mandatory invoice content on the tax authority's website; do not copy it from a template of unknown origin.
- Currency: stated, with the rate source and date if you convert.
- Due date: a calendar date, such as "due 14 November 2026", never only "net 30". State the payment terms from the agreement as well.
- Bank details: account name that matches your registered payee name, plus the identifiers your bank and the client's country need. A mismatch between payee name and account name is a common reason a payment is held.
- Late-payment rule: the fee or interest agreed in the contract, or the statutory one, with its source. Leave it out if neither exists.

### 3. Send it to the people who pay

Email the invoice as a PDF to the accounts-payable address the client gave you, copying the project contact. If you were not given one, ask for it in writing. Put the invoice number and amount in the subject. Ask for a reply confirming receipt and the expected payment date. A project contact is not accounts payable, and an invoice that only reached them has not been submitted.

### 4. Check portal and e-invoicing requirements

Larger clients and public bodies often require submission through a supplier portal or in a structured e-invoice format, and will ignore an emailed PDF. Ask at onboarding: portal or email, format, required fields, and who approves. If your jurisdiction mandates e-invoicing for your sale, confirm it from the tax authority. Register on the portal before the first invoice is due, not after.

### 5. Never edit a sent invoice

Once sent, an invoice is a record. To correct an error, issue a credit note that references and cancels the original in full, then issue a new invoice with a new number. Overwriting the original breaks the numbering, confuses the client's books and fails an audit. Credit notes take numbers from their own series or the same one, but consistently, and each states the invoice it reverses.

### 6. Keep the trail

File each invoice, its send email, the receipt confirmation and any credit note together under the client. Record the date sent, the date acknowledged and the date paid, so an ageing view starts from facts. Hand the list to the bookkeeping routine each month.

## What to hand back

```text
Invoice check: [number - pass/fail per line, with the fix for each fail]
Send details: [recipient, copied contacts, subject, date, receipt requested]
Portal / e-invoice: [required / not required, source checked on date]
Numbering scheme: [format, next number, credit-note series]
Correction needed: [credit note + replacement, or none]
Sending routine: [trigger events and calendar dates]
```

## Anti-patterns

- **Month-end batching.** The invoice arrives after the approver has forgotten the work.
- **Net 30 with no date.** Thirty days from sending, receipt, or approval is a negotiation. Write the date.
- **Trading name instead of legal name.** The client's system cannot match it to a vendor record.
- **Sending only to the project lead.** They are not the payer. Use the accounts-payable address.
- **Overwriting a sent invoice.** Credit it and issue a new one.
- **Copying tax wording from an old invoice.** Rules change and differ by country. Check the authority.

## Reference files

- `references/invoice-checklist.md` — read at steps 2, 4 and 5: the full pre-send checklist with reasons, a supplier-details form to send the client, and the credit note procedure.
