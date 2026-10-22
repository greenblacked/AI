---
name: subcontract-client-work
description: "Pass part of a client job to a contractor safely: check the client agreement permits subcontracting, write the brief as a bounded deliverable plus acceptance check, run a paid 1-2 day trial on low-risk work for a first engagement, flag worker-classification questions for an accountant, flow confidentiality, IP, data protection, deadline terms down into the subcontract, grant least-privilege named access, price the subcontract at no more than about 60% of the client fee, review midway and before delivery, pay on acceptance. Use for 'can I subcontract part of this project', 'I am overbooked and need a helper on a client job', 'my subcontractor missed the deadline'. Not legal or tax advice. Not for employee hiring (hiring-loop), your client contract (services-agreement-checklist), delegating a coding task (agent-delegation) or employee onboarding (onboarding-plan)."
allowed-tools: Read, Glob, Grep
---

# Subcontract Client Work

A subcontract is set up well when the client agreement allows it, the contractor has a bounded deliverable with a check you can run, their terms carry everything you owe the client, their access is the minimum, and the margin on the job is still positive after your review time.

The usual failure is handing over a vague slice of work on a handshake. The contractor guesses the scope, delivers late or wrong, and you remain fully responsible to the client for it, with no contract term that lets you recover the cost. The second failure is the arrangement itself: a contractor who works your hours, on your tools, for you alone can be treated as an employee, and that liability lands on you.

## Scope

Use for: passing part of a client project to a freelancer or another agency, taking a first contractor on, recovering a subcontractor who is late or off-spec, and doing white-label work for another agency.

Do not use for: structured hiring of employees (`hiring-loop`); the clauses in your own contract with the client (`services-agreement-checklist`); delegating a coding task (`agent-delegation`); onboarding an employee (`onboarding-plan`). Contractor status, withholding and the enforceability of clauses depend on your country; put those questions to an accountant or solicitor. This is not legal or tax advice.

## Workflow

### 1. Check that you may subcontract

Read the client agreement for clauses on subcontracting, assignment, named personnel, confidentiality, data location and security. Note whether you need consent, must disclose the subcontractor, or may not use anyone outside a named set. If the agreement is silent, ask the client in writing before assigning anything; discovering it afterwards is a breach. For white-label work for another agency, confirm what you may say about who did the work.

### 2. Write the brief before approaching anyone

Define one bounded deliverable, not a number of hours: what is delivered, in what format, where, by when, and an acceptance check you can run in under an hour (a test, a checklist, a sample page, a reviewed draft). Include the source material, the style or standards, what is out of scope, and who answers questions. If you cannot write the acceptance check, the slice is not bounded enough to hand over. A template is in `references/subcontract-pack.md`.

### 3. Trial a first contractor on small paid work

For a contractor you have not worked with, run a paid trial of one to two days on real but low-risk work, scored against the acceptance check from step 2. Pay for it at the agreed rate, whatever the result. The trial tests quality, communication and reliability before the client's deadline depends on them, and it costs less than a failed delivery. Score it and keep the score; see the sheet in the reference.

### 4. Flag the classification question

Before the first day, note how the arrangement will run on four points: who controls how and when the work is done, whose tools are used, whether set hours are required, and whether the contractor is barred from other clients. The closer it looks to employment, the more likely authorities treat it as such, with tax and withholding consequences for you. Ask an accountant how your country's test applies and what documents to collect from the contractor, such as their tax number and business details. Do not decide this by the label in the contract.

### 5. Flow the terms down

The subcontract must carry at least what you owe the client, or you are exposed for more than you can recover. Cover:

- Confidentiality at least as strict as the client's.
- IP assignment to you, so you can assign onward to the client, with any pre-existing material licensed.
- Data protection duties, including limits on where data is held and what happens on completion.
- Deadlines, acceptance process and rework at no charge for defects against the brief.
- Limits on further subcontracting without your consent.
- Liability and indemnity sized to what you can recover.

Have a solicitor review your template once. The checklist is in the reference.

### 6. Grant least-privilege access

Give the contractor named accounts for each system, never a shared login, scoped to the slice they are working on, and set to expire at the end date. Prefer a staging environment or a copy of the data limited to what the task needs. Record each access in a list so you can revoke it at handover (see `client-offboarding`).

### 7. Price with margin

Set the subcontract price at no more than about 60% of what the client pays for that slice. The remainder pays for your management, review, rework risk and the chance of a late delivery; adjust the figure to your own numbers, using the real hours your review takes, and write down the figure you chose. Track the margin per project in the table used by `estimate-actuals-review`, so the next quote reflects what subcontracting really cost.

### 8. Check in at half way

Schedule an interim review when the work is about 50% done. Look at the actual output against the acceptance check, not a status message. Catching a misunderstanding at half way costs half a delivery; catching it at the deadline costs the deadline. If the review fails, decide that day: correct, replace or take it back.

### 9. Review everything before it reaches the client

You remain responsible to the client for all of it. Run the acceptance check yourself and read the work as the client will. Budget the time in step 7. Do not forward a deliverable you have not opened.

### 10. Pay on acceptance

Pay the contractor when you accept the work against the brief, within the agreed period, and not when the client pays you, unless the contractor agreed to that term in writing and understood the risk. Pay on time: a contractor you pay late stops taking your calls. If a deadline is missed, apply the terms: cure period, rework or termination, and tell the client early if it affects them.

## What to hand back

```text
Permission: [clause - allowed / consent needed / disclosure required]
Brief: [deliverable - acceptance check - deadline - out of scope]
Trial: [dates - score against check - decision]
Classification note: [control / tools / schedule / exclusivity - question for accountant]
Flow-down: [terms covered - gaps]
Access list: [system - account - scope - expiry]
Price and margin: [client fee - subcontract price - % - review hours]
Interim review: [date]
Acceptance and payment: [date accepted - pay-by date]
```

## Anti-patterns

- **Subcontracting before reading the client agreement.** A consent clause breached is a lost client.
- **Briefing by hours.** Hours cannot be accepted or rejected; a deliverable can.
- **Starting with the full job.** Run a paid trial first.
- **A shared login.** It cannot be revoked for one person and logs nothing useful.
- **Pricing at 90% of the fee.** There is no room for review or a bad week.
- **Forwarding unreviewed work.** The client holds you, not the contractor.
- **Paying only when the client pays.** Unless agreed in writing, it is a cash-flow shift the contractor never accepted.

## Reference files

- `references/subcontract-pack.md` — read at steps 2, 3, 5 and 6: the brief template, the trial scoring sheet, the flow-down checklist and the access list layout.
