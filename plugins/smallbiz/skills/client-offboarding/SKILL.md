---
name: client-offboarding
description: "Close a client engagement cleanly: acceptance confirmed in writing, final invoice issued with source files and credentials released only on payment, a handover pack (what was built, where it lives, renewals and domains in the client's name, known issues), an access audit of every account, key and repo you hold, then revoke rather than just leave, client data returned or deleted with the date recorded, a warranty window with an end date, an archive with a retention date, and a testimonial request only after payment. Ends in a one-page closure record. Use for 'project is finished, what now', 'handing over to the client', 'client is leaving, how do I wrap up', 'revoke my access after contract ends'. Not for the start of an engagement (statement-of-work), rotating production secrets (secret-rotation), employees (onboarding-plan) or an unfinished project (stalled-project-recovery)."
allowed-tools: Read, Glob, Grep
---

# Client Offboarding

An engagement is closed when the client has accepted the work in writing, the final invoice is paid, everything the client owns is in their hands, every credential you held is revoked, and one page records all of it with dates.

The usual failure is drift. The last deliverable ships, the thread goes quiet, and months later you still hold admin access to their hosting, a copy of their customer list, and an unpaid final invoice that nobody wants to raise. Each of those is a liability you carry for free: a breach in your account becomes their breach, and a dispute about a bug has no end date because nobody wrote one.

## Scope

Use for: the end of a fixed project, the end of a retainer, a client who is leaving, or a contract that has expired and needs its access wound down.

Do not use for: the start of an engagement and what it covers (`statement-of-work`); rotating production secrets as a routine or after an incident (`secret-rotation`); bringing an employee onto a team (`onboarding-plan`); a project that has stalled before finishing (`stalled-project-recovery`). A dispute over the final invoice goes to `invoice-dispute-resolution`; an overdue one goes to `late-payment-chase`. Data-return and deletion duties come from your agreement and local law; this is procedure, not legal advice.

## Workflow

### 1. Get acceptance in writing

Send the client a short message listing the deliverables against the statement of work and ask them to reply "accepted" or to list what is outstanding. Acceptance is the event that starts the warranty window and triggers the final invoice, so an email reply is enough but silence is not. If the agreement has a deemed-acceptance period, quote it in the message and the date it ends.

### 2. Issue the final invoice, and tie release to it

Invoice the final milestone on the day of acceptance (see `invoice-hygiene` for what it must contain). State in the covering note that source files, admin credentials and the handover pack are released on receipt of payment. Hold back only what the agreement lets you hold back; withholding something the client already owns outright, such as their own domain registration, turns a payment delay into a dispute.

Payment gates only the release of deliverables the agreement lets you withhold. It does not gate removing your own access or deleting client data in steps 4 and 5: those protect you and the client, and waiting on an unpaid invoice leaves you holding admin access indefinitely. If the invoice is overdue, chase it with `late-payment-chase`; if it is disputed, use `invoice-dispute-resolution`. Either way, set a date for the access audit when you send the invoice and keep to it.

### 3. Write the handover pack

Write it so a stranger could run the thing. Use the template in `references/handover-and-closure.md`. It names what was built, where each part lives, how to run, build and edit it, what is known to be broken, and every renewal, domain, licence and subscription with the account holder and renewal date. Anything recurring must be in the client's name and on the client's card; if any is in yours, move it now or list it with a cut-over date.

### 4. Audit every access you hold

Do this by the date you set in step 2, whether or not the final invoice has been paid.

List before you revoke, because the accounts you forget are the ones that stay open. Walk the checklist in `references/handover-and-closure.md`: client-owned cloud and hosting consoles, repositories and CI, DNS and registrar, analytics and ad accounts, email and chat workspaces, password-manager vaults and shared folders, API keys and tokens, SSH keys, VPN profiles, test accounts and any device or phone number used for two-factor codes.

For each line record who granted it, what it reaches and the action: hand over, remove yourself, or delete. Then act:

- Remove your own user from each account rather than only logging out, and delete personal access tokens and SSH keys you created.
- Where a credential was shared with you (a password, an API key), ask the client to rotate it after you are removed, because you cannot prove nobody else saw a copy. Tell them which ones; do not rotate their production secrets yourself unless the agreement says you operate them.
- Leave the client's data in place for now; step 5 decides what happens to it.

### 5. Transfer or delete client data, and record when

Follow the agreement: return it, delete it, or keep it for a stated period. If it is silent, ask the client which they want in writing, and record the decision before removing anything, because deleted data cannot be returned. Then remove the client's data from your own tools (ticket system, notes, cloud storage, local clones) as decided. Deleting means the working copies, scratch databases, exports and backups you control, not only the project folder. Record the date, what was deleted and where, and keep that record rather than the data. Keep your own invoices, contract and correspondence; those are your records, not theirs.

### 6. State the warranty window

Write down what is covered (defects against the accepted scope, not new requests), the length from the agreement or a default you propose, the start date (acceptance) and the end date as a calendar date. Say how to report a defect, and that work outside it is quoted separately. A window with no end date is an unpaid support contract, and a request after it is a new quote (`scope-creep-response` covers the wording).

### 7. Archive with a retention date

Archive the project folder read-only in one place: contract, accepted scope, change log, handover pack, closure record and the invoice trail. Set a delete-by date from your tax and records rules or the agreement, whichever is longer, and put it in the calendar. Check your jurisdiction's primary source for how long business records must be kept.

### 8. Ask for the testimonial after payment clears

Ask once the final payment has arrived, not before: a request while an invoice is open reads as leverage in either direction. Offer a two-line draft they can edit, ask permission to name them, and ask who else they would recommend you to. If the relationship ended badly, skip the testimonial and keep the closure record.

## What to hand back

```text
Closure record (one page)
Client / project / dates:
Acceptance: [date, where recorded]
Final invoice: [number, amount, paid on]
Handover: [pack location, released on]
Access audit: [count held, count revoked, count rotated by client, date]
Data: [returned / deleted / retained until, date, by whom]
Warranty: [scope, start, end date, how to report]
Archive: [location, delete-by date]
Open items: [owner - item - date]
Testimonial / referral: [asked on / not applicable]
```

## Anti-patterns

- **Leaving instead of revoking.** Going quiet keeps your access alive. Remove yourself and tell the client what to rotate.
- **Releasing credentials before payment.** The last invoice then becomes the one nobody chases. The opposite error is keeping your own access until it is paid: revoke on the audit date regardless.
- **Recurring costs in your name.** The client's domain or hosting renews on your card for years. Move it or date the cut-over.
- **An open-ended warranty.** Give it an end date in the acceptance message.
- **Deleting only the project folder.** Exports, database dumps and backups elsewhere are still client data.
- **Asking for a testimonial in the final invoice email.** Wait for the money.

## Reference files

- `references/handover-and-closure.md` — read at steps 3, 4 and 8: the handover pack template, the access audit checklist, the acceptance and warranty wording, and the closure record layout.
