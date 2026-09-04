# Interrogating for a status update

## Contents

- How to run the questioning
- The core batch
- Breaking a vague answer
- Testing the RAG status
- Converting a non-answer into a `[TK]`
- Claims that need a source

## How to run the questioning

Ask once, in a batch, then draft. Five to seven questions is the working range for a
weekly; three for a short exec note. Read the linked board, dashboard or previous update
first — asking for something that is already visible costs the author's patience and buys
nothing.

If the human cannot say what changed since the last update, the honest artefact is one
line saying so. Writing three paragraphs around an empty week is how updates become noise
that people stop opening.

## The core batch

1. What is now true that was not true at the last update — and where is that visible?
2. Is there an ask? One decision, one resource, or none. Who has to grant it?
3. What date matters, and what specifically happens if it slips?
4. What are the two live risks, who owns each, and what is being done about them?
5. What is the honest status — and if it is green, what would have to be true for it to
   be amber?
6. Who is reading this, and what can they actually act on?

## Breaking a vague answer

| Answer you get | Follow-up |
| --- | --- |
| "Good progress." | On what, measured how, compared to what last week? |
| "Nearly done." | What percent of the work items are closed, and which are left? |
| "Blocked on another team." | Blocked on whom, since when, and what was the last response? |
| "It's on track." | Track to which date, and what is the current forecast? |
| "We improved performance." | Which metric, from what to what, on which dashboard? |
| "There's some risk around X." | How likely, what does it cost if it lands, who owns it? |
| "We'll pick it up next week." | Who, and what does done look like by Friday? |
| "Everyone's aligned." | Who signed off, when, and where is that recorded? |

One follow-up per point is fair. A second on the same point usually means the fact does
not exist — place a `[TK]` and move on rather than negotiating.

## Testing the RAG status

Green survives only if the author can answer these without hedging:

- Which dated commitment is this green against?
- What is the current forecast date, and what is the gap?
- What is the largest unknown, and is it bounded?
- Is anything waiting on a person or team outside your control? (An external dependency
  with no confirmed date is amber, near enough always.)

Amber needs three things or it is noise: the specific thing that must change, an owner,
and a date by which it changes. Red needs an ask and the date the ask must land by,
otherwise it is a complaint.

The habit to prevent: green, green, green, red. It means the status was a mood rather
than a measurement, and it removes the reader's only chance to help while helping was
still cheap. Amber early is a functioning reporting system, not an admission of failure.

## Converting a non-answer into a `[TK]`

Write the gap in the shape the answer would take, with its source and, where useful, who
can fetch it:

- `[TK: deploys per week, from the DORA dashboard]`
- `[TK: confirmed date from the platform team — asked 2026-08-01, no reply]`
- `[TK: cost of the extra runners, per month — ask finance]`
- `[TK: number of teams migrated of 14]`

Do not dissolve the gap into an adjective. "Significant progress on migration" is not
better than `[TK: teams migrated of 14]` — it is the same missing fact with the evidence
requirement hidden, and it is the sentence a reader will test.

In the handoff, say how many `[TK]`s remain and which ones block sending.

## Claims that need a source

Link every one of these, or mark it `[TK]`:

- Any percentage, count, latency, cost, headcount or date
- Any statement about what another team has committed to
- Any comparison to a previous period
- Any claim that something is "resolved" or "delivered"
- Any assertion about customer impact

A source is something the reader can open: a dashboard panel, a ticket, a document, a
dated meeting note. A person's name is a source for their opinion only, and should be
written that way — "per [name], the vendor cannot start before [TK: date]".

Note what is deliberately absent from this list: anything about how an individual is
performing. If the reason a date moved is a person, the update says the date moved and
why in system terms; the rest is a one-to-one conversation, not a line in a document with
a distribution list.
