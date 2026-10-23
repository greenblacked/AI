---
name: domain-ramp-up
description: "Get competent in an unfamiliar domain such as payments, logistics, ad-tech, clinical billing or telecom in about two weeks, in a fixed order: one page of the money, data and decision flow before any vocabulary, a glossary capped at 30 terms each with a real example record, one real transaction traced end to end including its refund, chargeback or recall path, five 30-minute expert interviews, then the regulatory and contractual constraints that make obvious designs illegal. A day-10 gate: wrong-beliefs list and a five-minute explanation to an outsider. Use when someone says \"I'm joining a fintech and know nothing about settlement\", \"how do I learn this industry fast\" or \"nobody in these meetings explains the terms\". Not for a repository (codebase-orientation), source notes (learning-notes) or a joiner's 90-day plan (onboarding-plan)."
allowed-tools: Read, Glob, Grep
---

# Domain Ramp-Up

Ramp-up is finished when you can explain the domain to an outsider in five minutes, an expert corrects no more than three points, and you hold a ranked list of the questions you still cannot answer.

The usual failure is learning vocabulary first. A glossary memorised before the flow of money and decisions is known produces someone who can use the words in a meeting and cannot predict what happens when a payment fails. The second failure is collecting notes without a deliverable, so after two weeks there is a folder and no map. The order below puts structure first, words second, an exception path third, and people fourth, because people answer better once you can ask about specifics.

## Scope

Use for: starting a job, project or acquisition in a business or technical domain you have not worked in; preparing to design or review software for an industry; recovering when meetings run on terms nobody defines.

Do not use for: orienting in a repository (`codebase-orientation`), processing a book or article into notes (`learning-notes`), or a manager's plan for a new joiner (`onboarding-plan`). A tool or framework is `learn-new-technology`, not a domain.

## Workflow

Budget about ten working days. Steps 1 to 3 take the first four days, interviews run in days 4 to 9, step 5 overlaps them, and the gate is day 10.

### 1. Draw the flow on one page

Before any vocabulary, answer on one page: who pays whom, what artefact moves between parties (an invoice, a claim, a bill of lading, an ad impression log), what data each party holds, and who can say no at each hop (a bank, a regulator, a carrier, a payer). Mark where time passes: settlement lag, claim adjudication, delivery windows. Mark where money or goods can be reversed.

Use the product's own public documentation, an industry body's explainer, and the company's architecture overview. If two sources draw the flow differently, keep both and add the disagreement to the question list. Read `references/flow-and-glossary-templates.md` for the page layout and the glossary entry format.

### 2. Build a capped glossary

Cap it at 30 terms. The cap forces a choice: a term earns a slot only if you heard it in a meeting, or it names a hop or artefact from step 1. Each entry carries a one-line definition, one real example record (a redacted row, a sample message, a real claim line), and the system or party that owns it.

Then write the three pairs of terms people confuse in this domain. Every domain has them (authorisation versus capture versus settlement in payments; consignee versus notify party in freight). Ask a practitioner which pairs they see mixed up, and write the distinguishing test for each.

### 3. Trace one real transaction, including its exception path

Pick a transaction that already happened, not a textbook one, and follow it through every system and party, noting timestamps and who held the money or goods at each point. Then trace one that went wrong: a refund, a chargeback, a recall, a rejected claim, a returned shipment. The exception path is where most domain rules actually live, and a happy path alone teaches the version of the business that does not need your help.

### 4. Run five 30-minute expert interviews

Pick five people from different seats: operations, finance or billing, a customer-facing role, a compliance or risk person, and someone who has been on call for the domain. Ask each the same fixed set, so answers can be compared:

- What fails most often, and how do you find out?
- Which rule does everyone forget until it bites?
- Who gets called when the main flow breaks, and what do they do first?
- What would a newcomer assume that is wrong?
- Which number do you watch every day?

Take the trace from step 3 to each interview and ask them to correct it. Corrections to a concrete artefact are more reliable than answers to an open question. Thirty minutes is enough if you arrive having done steps 1 to 3; do not schedule the interviews first.

### 5. List the constraints that make obvious designs illegal

Write down the regulatory and contractual constraints, each with its source and what it forbids or forces: data retention and residency rules, licensing, mandated hold periods, scheme or carrier rules, contractual service levels, audit duties. For each, give an example of a design that looks sensible and is not allowed. Cite the document, not a colleague's memory, and mark anything you could only confirm verbally. This is a procedure for orientation, not legal advice; a constraint that affects a design goes to the people who own compliance.

### 6. Day-10 gate

Do both, in writing, before declaring the ramp-up done:

1. Write the list of beliefs you held on day one that turned out wrong. An empty list means you have not yet learned anything, or have not checked.
2. Explain the domain to an outsider in five minutes, then hand the same explanation to an expert. Count the corrections. More than three means go back to the step where the errors originated (usually step 3) and repeat that step, not the whole plan.

## Hand back

A domain map, not notes: the one-page flow, the capped glossary with example records and confusable pairs, the two traced transactions, the constraint list with sources, the day-10 wrong-beliefs list, and a ranked question list. Rank questions by how much a wrong answer would cost, not by how easy they are to ask. Name who could answer each.

## Anti-patterns

- **Reading the whole wiki.** Volume feels like progress; the flow page and one traced transaction teach more.
- **Glossary past 30.** A long glossary is a second copy of the source. Cut to what you will actually hear.
- **Interviewing the friendly person five times.** Five seats, not five colleagues from one team.
- **Skipping the exception path.** The refund and the recall carry the rules nobody writes down.
- **Treating one expert as the domain.** Note where two experts disagree; the disagreement is a finding.

## Reference files

- `references/flow-and-glossary-templates.md` - read at steps 1 and 2: the one-page flow layout, the glossary entry format with an example, and the confusable-pairs table.
- `references/interview-and-gate-kit.md` - read before step 4 and at the gate: the interview script with follow-ups, the transaction trace table, the constraint register and the day-10 scoring sheet.
