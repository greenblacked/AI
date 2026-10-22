---
name: services-agreement-checklist
description: "Check your own client contract for the clauses a freelancer needs, ordered by money at risk and marked present, weak or missing: payment terms, late fee, deposit, kill fee, IP transfer only on full payment, reuse of pre-existing tools, portfolio rights, confidentiality, liability cap, client-materials indemnity, termination, change procedure, jurisdiction, subcontracting. For client paper, flag the seven clauses that most often shift risk: uncapped indemnity, work-for-hire of pre-existing IP, pay-when-paid, exclusivity, net-90, unilateral scope change, unlimited revisions. Output is questions for a solicitor, not a verdict. Use when asked to review a freelance contract, what belongs in a client agreement, or when a client sends a contract to sign. Not for vendor contracts you buy under (contract-reader), suppliers (vendor-evaluation), scope (statement-of-work)."
allowed-tools: Read, Glob, Grep
---

# Services Agreement Checklist

The pass is done when every clause on the list has been marked present, weak or missing against the contract in front of you, the highest-risk gaps are at the top, and a list of specific questions is ready to take to a solicitor.

Freelancers sign what the client sends, or reuse a template from five years ago, and discover the missing clause when a client stops paying or a deliverable is disputed. The order below follows money at risk, so a limited amount of review time goes to the clauses that cost most when they fail. This is procedure, not legal advice: it finds the questions, and a qualified lawyer in your jurisdiction answers them. Contract law differs between countries and often between states; nothing here says what is enforceable.

## Scope

Use for: reviewing your own template, preparing to sign a client-supplied contract, or deciding what a freelance agreement should contain before drafting.

Do not use for: reading the vendor contracts you are buying under (`contract-reader`), choosing between suppliers (`vendor-evaluation`), or writing the project scope and acceptance criteria (`statement-of-work`). Pricing and payment schedule belong to `fixed-price-quote`.

## Workflow

### 1. Get the full document

Read the whole agreement, including schedules, order forms, referenced terms and any link to online terms that "form part of" it. Terms incorporated by reference bind you. Note the parties' exact legal names, the date, and which document wins if two conflict.

### 2. Run the clause pass in order of money at risk

For each clause below, mark it **present** (says what you need), **weak** (exists, but vague or one-sided) or **missing**, and quote the clause number. Detail on what good looks like is in `references/clause-guide.md`.

1. Payment terms and due date: amount, trigger, days to pay.
2. Late fee or statutory interest on overdue sums.
3. Deposit, and which part is non-refundable.
4. Kill fee if the client cancels or stops the project.
5. IP transfers only on full payment.
6. A licence to reuse your pre-existing tools, templates and code.
7. Portfolio rights to show the work.
8. Confidentiality, mutual and time-limited.
9. Liability capped at fees paid.
10. No indemnity for materials the client supplies.
11. Termination notice, both ways.
12. A change procedure for scope.
13. Dispute path and governing jurisdiction.
14. Permission to subcontract.

### 3. For a client-supplied contract, flag the seven

These move the most risk to the contractor. Look for each by name:

1. **Uncapped indemnity.** You pay the client's losses without limit.
2. **Work-for-hire of pre-existing IP.** Tools you already owned become theirs.
3. **Payment contingent on the client's customer paying.** You carry their credit risk.
4. **Exclusivity or non-compete.** It limits other work and may outlast the job.
5. **Net-90 or longer payment terms.** A free loan to the client.
6. **Unilateral scope change.** They can add work at the same price.
7. **Unlimited revisions.** The price has no ceiling on effort.

For each hit write the clause number, the exact words, and what the clause would cost if used against you.

### 4. Score and order the gaps

List all weak and missing items, ranked by cost if the clause fails: payment and IP first, then liability, then convenience clauses. Mark which items are reasonable to negotiate and which you would walk away over. Decide in advance; negotiating under time pressure with the client waiting gives away the most.

### 5. Turn gaps into questions for a solicitor

Write each issue as a specific question, with the clause text attached. For example: "Clause 9 says I indemnify the client for all losses arising from the services. Does this cover loss caused by the client's own instructions, and what is a reasonable cap in this jurisdiction?" A lawyer's time is expensive, and specific questions with quoted text get specific answers for far less. The question list layout is in `references/clause-guide.md`.

### 6. Propose changes in plain words

Alongside the questions, write the change you would ask the client for, in a sentence: "cap liability at fees paid in the preceding twelve months", "IP transfers when the final invoice is paid". Send changes as a marked-up list; many clients accept reasonable edits to their own paper, and a no is useful information.

### 7. Decide and record

Record what you asked for, what was agreed and what you accepted despite the risk, with the date. A known risk accepted deliberately is a business decision; an unread one is an accident.

## What to hand back

```text
Document: [title, parties, date] · Reviewed including: [schedules, linked terms]
Clause table: [clause - present | weak | missing - clause number - note]
Seven-clause flags (client paper): [flag - clause number - quoted words - cost if used]
Ranked gaps: [1..n, with walk-away items marked]
Questions for a solicitor: [numbered, each with quoted text]
Changes to request: [numbered]
```

State at the top of the output that it is a list of questions, not legal advice.

## Anti-patterns

- **Signing the contract because the client is friendly.** Relationships end; the clauses are what remain.
- **Reading only the main body.** The schedule or the linked online terms often carries the indemnity.
- **Asking a lawyer "is this OK".** The answer is vague and the bill is large. Ask about named clauses.
- **A template unchanged for years.** Law, tax and your own business move. Review it each year.
- **Treating every gap as equal.** A missing portfolio clause is minor; a missing payment clause is not.
- **Believing the checklist is a verdict.** It is not. Enforceability depends on the jurisdiction.

## Reference files

- `references/clause-guide.md` — read at steps 2 and 5: what a good version of each clause looks like, the warning signs in client paper, and the solicitor question template.
