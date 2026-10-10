# Fan-out and synthesis

## Contents

- Why two
- Splitting a question
- The synthesis step
- When one is enough

## Why two

Each parallel agent returns a report the main conversation must read and trust. Two returns on separate questions are read closely. Three or four overlap, disagree on shared ground and hand the main conversation reconciliation work that costs more than the reading they saved. Two covers the common cases: a survey beside a claim check, or two surveys on separate questions.

Fan-out applies to survey-shaped work, the stages that read and report. The stage a fan-out serves, for example Architect drafting while two claims are checked, is not one of the two.

## Splitting a question

Two questions are disjoint when neither answer changes the other and no file or claim is read by both. A test: write each question as one sentence; if a good answer to the first would be a useful input to the second, they are one question.

- Good: "what in the repository already covers this?" and "does the third-party limit the design assumes actually hold?"
- Good: "which of our services call this endpoint?" and "which of our docs describe it?"
- Not disjoint: "how does auth work here?" and "where is the session handled?"

If the work does not split, run one agent.

## The synthesis step

Name it in the plan so it is not skipped: after both return, the main conversation does the following before the next stage starts.

1. Read both returns in full, not their summaries.
2. Note where they agree, where they disagree, and what neither assessed.
3. Settle each disagreement in the conversation, by reading the evidence one of them cited, not by choosing the more confident report.
4. State the decision in one paragraph, with what it rests on and what is still open.
5. Pass the next stage that paragraph, not the two reports.

The synthesis is not delegated. It depends on everything the session has learned, which a cold prompt does not carry, and handing it on gives the decision to an agent that has seen half the picture.

## When one is enough

A single survey on a bounded question needs no fan-out and no synthesis step beyond reading the report. Add the second agent only when there is a second question that is genuinely separate. Starting two to be thorough produces overlapping returns and the reconciliation this file exists to avoid.
