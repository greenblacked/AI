---
name: request-triage
description: "Handle feature requests from sales and customers so real deal-blockers surface and every requester hears back. Record the job and the customer, never the feature wording; ask \"what will you do if we never build it, and would you sign without it?\" and count a blocker only with the customer's contingency in writing; merge duplicates into one record with customer count and ARR; give one of five dispositions (now, planned, exploring, declined, redirected-to-existing) within five working days with a reason the requester can repeat. Use when sales keeps asking for features, the request backlog sits unread, someone claims a deal is blocked on a missing feature, or customers ask what happened to their request. Not for a demand that bumps committed roadmap work (roadmap-disruption-triage), retiring a feature (feature-sunset), or team delivery health (delivery-review)."
allowed-tools: Read, Glob, Grep
---

# Request Triage

Done means every request in the queue is a record of a job and the customers who have it, duplicates are merged with a distinct-customer count and ARR, each record carries one of five dispositions given within five working days, every requester has been told the reason in words they can repeat, and the word "blocker" appears only where a customer has put a contingency in writing.

The usual failure is a backlog titled in feature wording: "Add SSO", "Export to Excel", "Custom fields". Each looks like a different ask, so the same underlying job is spread across forty tickets and never adds up, while the one rep who escalates loudest gets a roadmap slot. The second failure is silence: requests go in and nothing comes out, so sales stops filing them and starts escalating to executives instead, which is how a request queue becomes a roadmap fight.

## Scope

Use for: setting up or running intake for feature requests; deciding which requests are genuine deal-blockers; merging and sizing a backlog of asks; replying to requesters; the monthly summary to product leadership.

Do not use for: a demand from an executive or key account that forces committed roadmap work to slip, which is `roadmap-disruption-triage`; customers asking to keep a feature you are retiring, which is `feature-sunset`; ranking the whole roadmap or judging how a team delivers, which is `delivery-review`; learning why customers bought, which is `jobs-timeline-interview`.

## Workflow

### 1. One intake, with the job as the required field

Accept requests through one channel (a form or a ticket type), not chat messages to product managers. Required fields:

- The customer account, and the requester inside your company.
- The job: what the customer is trying to get done, when it comes up, and what they do today instead.
- The cost of the workaround: hours, money, risk or a lost user, in the customer's terms.
- The customer's own words, quoted, kept apart from the job statement.
- Commercial context: open deal and its stage, or existing contract and renewal date, and the ARR involved.

The triager rewrites the record's title into the job, for example "Finance needs an audit trail of who changed an invoice" rather than "Add change history". Keep the original feature wording as a quote. Titling by feature wording is what stops duplicates from being found, because two customers with the same job rarely ask for the same feature.

### 2. Run the blocker test

Ask the requester to put two questions to the customer: "What will you do if we never build this?" and "Would you sign, or renew, without it?" Record the answer in a blocker field with three values:

| Value | Evidence needed |
| --- | --- |
| Verified blocker | A written contingency from the customer: an email, a redline, a procurement requirement, a clause in the order form |
| Claimed blocker | The requester believes it blocks the deal but nothing is in writing |
| Not a blocker | The customer will sign, renew or keep using without it |

Only a verified blocker is reported as one. The field is not a judgement of the rep; it is the difference between "this cost us a deal" and "someone was worried it might". Track the share of blockers that are verified, and, if you add fields for the first blocker value and the deal outcome, how often claimed blockers become verified and how often verified ones lose the deal when declined; those numbers make the next argument shorter.

### 3. Merge by job, then size

Search existing records by job, not by keyword. When a new request matches, attach the customer to the existing record rather than opening a new one. Each record carries:

- Distinct customers, counted once however many people inside the account asked.
- ARR from existing customers, and ARR in open deals, kept as separate figures. Pipeline ARR is a forecast and shrinks; installed ARR is real.
- Segment of each customer, so a job held by one large account can be told apart from one held across the target segment.

A large account asking alone is a custom-build risk, not a mandate. Size is evidence for the decision, not a vote that makes it.

### 4. Check for an existing answer before deciding anything else

Before any other disposition, ask whether something already does the job: a setting, an integration, an API, a report, a documented workaround. Check the docs and the support knowledge base, and ask support. Requests filed in feature wording are often already answerable, and this is the only disposition that helps the customer this week.

### 5. Decide within five working days

Every record gets exactly one disposition within five working days of intake. Five days is short enough that a deal in flight can still use the answer, and it forces a decision on the record as it stands instead of waiting for more requests to pile up.

| Disposition | Meaning | What happens next |
| --- | --- | --- |
| Now | Goes into current work | Only if it fits without moving committed work; if it would move it, stop and use `roadmap-disruption-triage` |
| Planned | Has a slot on the roadmap | Give a quarter or a half, not a date, unless the slot is already scheduled |
| Exploring | Real job, not yet understood | A named next step and a date: interviews, data pull, a test |
| Declined | Will not be built | A reason rooted in strategy, segment or cost, stated plainly |
| Redirected-to-existing | Already possible | The how-to, sent to the requester and the customer |

Write the reason as one or two sentences the requester could read aloud to the customer without embarrassment: no internal codenames, no "it's on the list", no hint of a date you have not committed. "We are focusing this year on teams under 200 people, and this job mostly comes from much larger finance departments, so we are not planning to build it" can be repeated. "Deprioritised" cannot.

Reply templates for each disposition are in `references/request-record.md`.

### 6. Close the loop with everyone attached

Send the disposition to the requester in writing and log the date. When a record changes state, for example from exploring to planned or from planned to shipped, notify every customer and requester attached to it. Attaching customers in step 3 is what makes this possible; without it, shipping a requested feature reaches nobody who asked.

### 7. Review monthly

Once a month, report to product leadership:

1. Top jobs by distinct customers, and separately by installed ARR.
2. Verified blockers: how many, which deals, what happened to each.
3. Claimed-to-verified conversion rate.
4. Records past five working days without a disposition, with their age. This should be zero; when it is not, the intake owner has too much on.
5. Records in "exploring" past their next-step date.

The queries for these, against a simple request table, are in `references/request-record.md`.

## Output

Hand back the triaged list (one row per job record: title, customers, installed ARR, pipeline ARR, blocker status, disposition, reason, date given), the replies sent or drafted, and the monthly summary if one is due.

## Anti-patterns

**Counting tickets, not customers.** Five people at one account filing the same ask is one customer. Count accounts.

**Treating a rep's certainty as a contingency.** Without the customer's words in writing, a blocker is a forecast. Ask the two questions every time.

**"Planned" as a polite no.** A record that sits in planned for three quarters teaches sales the label means nothing. If there is no slot, it is declined or exploring.

**Deciding by whoever escalates.** An escalation skips the record, so its customer count is never checked. Route escalations back into the same record and the same five-day clock.

## Reference files

- `references/request-record.md` — read when setting up intake or writing replies: the record fields, the blocker conversation script, reply templates for each disposition, and the monthly review queries.
