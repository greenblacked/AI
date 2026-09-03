# Interrogating for evidence

## Contents

- How to run the questioning
- Question bank by section
- Breaking a vague answer
- Converting a non-answer into a `[TK]`
- Claims that need a source
- Judgement calls

## How to run the questioning

Ask in one batch, then draft. Question-at-a-time interrogation wastes the human's
patience and produces the same answers. Four to seven questions is the working range; if
you need more than that, the decision is not ready to be written up.

Order the batch by what would change the document most if the answer surprised you. If
the answer to "what forced this now?" is "nothing, it came up in planning", the rest of
the questions may not matter.

Do not ask questions whose answers you can read out of a linked ticket, dashboard or
previous record. Read those first.

## Question bank by section

### Context and problem statement

- What forced this now, rather than last quarter or next?
- What breaks or costs money if we decide nothing?
- Which ticket, incident or thread does this trace back to?
- Who asked for it, and who has to live with the answer?

### Decision drivers

- Which constraints would actually change the answer if they moved?
- Which of these drivers do all the options satisfy equally? (Those are not drivers.)
- Is there a hard constraint — contract, compliance, deadline, budget — that rules
  options out before preference enters?

### Considered options

- What else was seriously on the table, and who argued for it?
- What does doing nothing cost? (Always an option; frequently the honest runner-up.)
- Was any option ruled out before evaluation, and on what basis?
- If a vendor or library was chosen: what was the runner-up, and what would have to be
  true for the runner-up to win?

### Decision outcome and consequences

- What are we knowingly giving up by choosing this?
- Who has to change how they work, and have they been told?
- What is the worst realistic outcome, and what does it cost?
- What does this foreclose — what gets harder to do later?

### Confirmation

- How would we find out this was wrong, and how quickly?
- Is there a test, lint rule, fitness function or dashboard that can hold this?
- If it is a review: who owns it and on what date?

### Reversibility

- If we wanted to undo this in six months, what would it take — hours, weeks, a migration?
- Is there a point of no return, and when do we cross it?

## Breaking a vague answer

Vague answers are the default, not a sign of bad faith. The follow-ups that work:

| Answer you get | Follow-up |
| --- | --- |
| "It's faster." | Faster at what, measured how, compared to what baseline? |
| "The team prefers it." | Which team members, and what did the people who disagreed say? |
| "It scales better." | To what number, by when, and what is the current number? |
| "It's the industry standard." | Which comparable organisations, and does their constraint set match ours? |
| "It'll save time." | Whose time, how many hours a week, measured where? |
| "We evaluated the options." | What was the runner-up and what specifically knocked it out? |
| "It reduces risk." | Which risk, currently how likely, and what is the residual after? |
| "Later / we'll review it." | Who owns the review and on what date? |

One round of follow-up is fair. A second round on the same point usually means the number
does not exist — stop asking and place the `[TK]`.

## Converting a non-answer into a `[TK]`

When the evidence is not there, write the gap into the document in the shape the answer
would take:

- `[TK: current p95 checkout latency, from the Grafana service dashboard]`
- `[TK: annual licence cost at 400 seats — ask procurement]`
- `[TK: date the vendor contract expires]`
- `[TK: name of the reviewer who owns the 90-day check]`

A good `[TK]` names the missing value, its likely source, and who can get it. It converts
a hole into an assigned task. It also survives review: a reviewer who sees three `[TK]`s
knows exactly what the document is missing, whereas a reviewer who sees three smoothed-over
estimates learns nothing and may act on them.

Do not remove a `[TK]` by softening the sentence. "Significantly reduces build time" is
not an improvement on `[TK: build time before and after]`; it is the same missing fact
with the evidence requirement hidden.

Say plainly, in the handoff, how many `[TK]`s remain and which ones block acceptance.

## Claims that need a source

Attach a link to every one of these, or mark it `[TK]`:

- Any percentage, latency, throughput, cost, headcount or date
- Any statement about what another team needs, wants or has committed to
- Any claim about a vendor's capability or SLA
- Any comparison to the status quo
- Any assertion about compliance or legal obligation

"Source" means something a reader can open: a dashboard panel, a ticket, a benchmark run,
a contract, a meeting note with a date. A person's name alone is a source only for their
own opinion, and should be written that way: "per [name], the migration cannot start
before [TK: date]".

## Judgement calls

Not every decision has evidence behind it, and pretending otherwise is the more damaging
error. When the human says the honest answer is experience and instinct, write that:

> This was a judgement call. We have no comparative benchmark; the choice rests on
> [name]'s experience running [system] at [scale], and on the team's existing familiarity
> with the stack.

That sentence is defensible in any review. A weighted scoring matrix assembled after the
winner was known is not, and an experienced reader can spot one — the weights are always
exactly what they need to be. Never build a scoring framework to dress up an intuition.
Score only when the criteria and weights were agreed before the options were scored, and
say when that happened.
