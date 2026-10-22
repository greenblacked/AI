---
name: client-profitability-review
description: "Decide which clients to keep, reprice or drop from a quarterly table per client: revenue, tracked hours including email and calls, effective hourly rate, days paid late, revision and scope-change count, share of revenue. Flag one client above about 40% as a risk to schedule action against, rank by effective rate and pain, then give each client one action: keep, raise (60 to 90 days notice, oldest and lowest-rate first, grandfathered date), restructure (retainer, deposits, shorter terms) or exit (notice per agreement, transition, referral), and draft each notice in the same sitting. Use when asking which clients are profitable, 'overworked and underpaid', time to raise rates, 'one client is 60% of my income', or whether to fire a client. Not for hard talks (difficult-conversation), staff retention (retention-review), the rate itself (billing-rate-calculation)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Client Profitability Review

A review is finished when each client has one action and a drafted message, the table behind the decision is saved, and any single client above about 40% of revenue has a dated plan to reduce the dependency.

Freelancers judge clients by invoice size and by how pleasant they are. Neither measures profit. A large client who sends daily emails, asks for rounds of revisions and pays at 60 days can earn less per hour than a small one who pays on the day. The review replaces impression with a table, and then forces a decision for each row, because a table that leads to no action is a spreadsheet hobby.

## Scope

Use for: a freelancer or small studio with at least a handful of clients deciding whom to raise, restructure or leave, once a quarter or when overwork shows up.

Do not use for: judging whether estimates for single projects were accurate (for example by comparing estimates with tracked hours), preparing for a hard talk with a person (`difficult-conversation`), staff retention (`retention-review`), or calculating the target rate (`billing-rate-calculation`). This is procedure, not legal advice; read your agreement for notice terms before sending any notice.

## Workflow

### 1. Gather a quarter of data per client

For each client over the last quarter (or twelve months if the quarter is thin) collect:

- **Revenue** received, excluding sales tax and pass-through costs.
- **Hours**, tracked, including email, calls, meetings, project management and unbilled revisions. Time not tracked is the most common error, and it flatters the worst clients. If you did not track, estimate from the calendar and the sent-mail folder and mark the figure as an estimate.
- **Payment days late**: average days past due on paid invoices, plus any currently overdue.
- **Revision and scope-change count**: from your change log (`scope-creep-response`).
- **Share of total revenue.**

### 2. Compute the table

```text
effective hourly rate = revenue / total hours worked
share of revenue      = client revenue / total revenue
```

If a client has zero hours in the period, as a reserved-capacity retainer can when nothing was asked for, revenue per hour is not defined: report it as not defined, and judge that client on margin against the capacity you reserved for them.

Put every client in one table, sorted by effective rate. Place your target rate from `billing-rate-calculation` beside it. A column for cost of lateness is optional: days late multiplied by the invoice value is a free loan, and it can be converted into an annual percentage to show its price. Layout and a worked example are in `references/review-table.md`.

### 3. Flag concentration

Mark any client above about 40% of revenue. This is a risk, not a verdict: the loss of that client would stop the business within a quarter. It does not mean ignoring them; it means scheduling action, such as a target date by which no client exceeds a share you can survive, and an ordered list of ways to get there (new leads, upsell elsewhere, a retainer that makes the revenue contractual). Concentration also reduces your negotiating position, so raise the issue before you need it.

### 4. Rank by effective rate and by pain

Pain is the qualitative remainder: unreasonable hours, disrespect, late decisions, work you would not show anyone. Rate each client on a simple scale. Combine the two: a high-rate, low-pain client is protected; low-rate, high-pain is the first candidate to exit; low-rate, low-pain is a candidate to raise; high-rate, high-pain is a candidate to restructure. Do not decide on rate alone, because a good-rate client who threatens your health still costs you.

### 5. Assign one action per client

- **Keep.** Nothing changes. Thank them and consider a referral request.
- **Raise.** Announce a new rate with 60 to 90 days notice. Start with the oldest and lowest-rate clients, since their price is furthest from current. Offer a grandfathered date: the old rate holds until that date, which makes the rise feel like a notice rather than an ambush. Size the raise from the gap between the effective rate and the target, and say what has changed.
- **Restructure.** Change the shape of the work rather than the price: a retainer with a defined monthly scope, a deposit before each piece of work, shorter payment terms or a late fee, a cap on included revisions, a single named contact.
- **Exit.** Give notice as the agreement requires, offer a transition period (for example, thirty days of handover), and refer them to a peer you trust. A well-run exit leaves a client who recommends you.

One action each. A client given two actions gets neither done.

### 6. Draft the notices now

In the same sitting, draft the message for each non-keep action: the rate notice, the restructure proposal, the exit email. Drafts written later are not written. Keep each short, factual and free of apology. Templates are in `references/review-table.md`. Check each against the contract's notice period before sending; if the agreement has none, state a reasonable one. Send on a schedule: no more than one or two difficult notices a week, so you can handle the replies.

### 7. Set the next review

Put the next review in the calendar one quarter ahead. Record the decisions and their dates in the file with the table, and at the next review compare actual results to what each action was expected to do.

## What to hand back

```text
Quarter: [period] · Target rate: [x]
Table: [client - revenue - hours - effective rate - days late - changes - share]
Concentration: [client, share] · Plan and date: [text]
Actions: [client - keep | raise to x on date, grandfathered until date | restructure: how | exit: notice per agreement, transition, referral]
Notices drafted: [list] · Send dates: [list]
Next review: [date]
```

## Anti-patterns

- **Untracked time.** The hardest clients are the ones whose time goes uncounted. Estimate if you must, and say so.
- **Deciding on revenue.** The biggest invoice may be the lowest rate. Use the effective rate.
- **Raising rates on new clients only.** The oldest clients are the furthest below market. Start there.
- **Ignoring concentration because the client is good.** The risk is the dependency, not the behaviour.
- **A table with no actions.** The review exists to produce decisions and sent messages.
- **Short notice for a rise.** Less than 60 days feels like a trap and gets refused; give 60 to 90.

## Reference files

- `references/review-table.md` — read at steps 2 and 6: the table layout with a worked example, a pain scale, and drafts for a rate notice, a restructure proposal and an exit.
