# Spaced review and card writing

## Contents

- [What earns a card](#what-earns-a-card)
- [Interval schedule](#interval-schedule)
- [Writing cards](#writing-cards)
- [Card formats worth using](#card-formats-worth-using)
- [Running a review session](#running-a-review-session)
- [Session summary format](#session-summary-format)

## What earns a card

Ask one question: will the user need this without a search box? If they will look it up, a
card is make-work that feels like study.

| Material | Card? | Why |
| --- | --- | --- |
| Exam or certification syllabus | Yes | Recall is the actual requirement |
| A command sequence used during an incident | Yes | No time to search, hands shaking |
| A definition they must produce in a meeting | Yes | Fluency is the point |
| The mental model behind a design choice | Yes, as a "why" card | Transfers to new problems |
| Flag names, ports, API signatures | No | Cheatsheet note, `--help`, or docs |
| Anything from a source read once out of curiosity | No | The note is the artefact, not the card |

## Interval schedule

A plain schedule the user can run by hand or feed into a plugin. Days after the last
successful review:

| Step | Interval |
| --- | --- |
| 1 | same day, a few hours later |
| 2 | 2 days |
| 3 | 5 days |
| 4 | 12 days |
| 5 | 30 days |
| 6 | 75 days |
| 7 | 180 days |
| 8+ | yearly, or retire the card |

Rules:

- A miss drops the card back to step 2, not to step 1. Restarting from zero punishes a card
  that is nearly learned and inflates the queue.
- Two misses at the same step means the card is broken, not the memory. Rewrite it before the
  next review.
- Retire cards. A fact recalled cleanly at 180 days for material no longer in use should leave
  the deck; a growing deck that never shrinks becomes a reason to stop reviewing entirely.
- Cap the daily queue at roughly fifteen minutes. Beyond that, review quality drops and the
  session gets skipped, which costs more than the missed cards.

## Writing cards

**One fact per card.** If the answer contains "and", it is probably two cards.

- Bad: "What are the four golden signals and what does each measure?"
- Better: four cards, plus one card asking "Which golden signal catches a slow dependency
  before error rate moves?" — the one that carries the reasoning.

**Unambiguous questions.** The user should know what shape of answer is wanted.

- Bad: "kubectl drain?"
- Better: "Which two things does `kubectl drain` do that `kubectl cordon` does not?"

**Prefer why/when over what for concepts.** Definition cards produce recognition, which does
not survive contact with a real decision.

- Weak: "What is a circuit breaker?"
- Strong: "When does a circuit breaker make an outage worse rather than better?"
- Strong: "Why does a retry budget belong at the client, not the server?"

**No cloze deletions over list items.** Deleting one item from a five-item list teaches
position rather than content. If a list must be memorised, use a card that asks for the whole
list with a stated count ("Name all four; there are four"), or find the organising principle
and card that instead.

**Context in the question, not the answer.** "In a multi-tenant cluster, why …" — a card with
no context gets answered correctly for the wrong scenario.

**Ten-second rule.** If the user cannot start answering within ten seconds, the card is
overloaded or vague. Split it, add context to the question, or delete it. Slow answers are a
card-quality signal, not a discipline problem.

## Card formats worth using

| Format | Shape | Good for |
| --- | --- | --- |
| Plain Q/A | Question front, single fact back | Definitions, thresholds, commands |
| Why/when | Decision framed as a question | Concepts, trade-offs, architecture |
| Scenario | Two-line situation, "what breaks first?" | Incident response, debugging paths |
| Reverse | Give the consequence, ask for the cause | Symptom-to-cause recall |
| Cloze (single) | One deleted term inside a sentence | Terminology in context |

## Running a review session

1. State the scope and the count up front: "12 cards due from `area/platform`, roughly eight
   minutes."
2. One question per message. Do not show the answer, the note, or a hint unless asked.
3. Grade against the note's own wording, and be blunt. Useful grades: "correct", "partial —
   you gave the mechanism but not the condition", "wrong — the note says the opposite".
   Encouragement that papers over a miss guarantees the same miss in thirty days.
4. When the answer is wrong, quote the exact line from the note. Paraphrasing the correction
   lets the user believe they were closer than they were.
5. If the user disputes the grade and is right, the note is wrong or ambiguous — fix the note,
   and say which line changed.
6. Close the session with three lists: missed, shaky, retire. For each miss, name the repair —
   split the card, add context, or rewrite the underlying note.

## Session summary format

```text
Reviewed 12 · correct 8 · partial 2 · wrong 2 · 7 min

Wrong
- "Why does a retry budget belong at the client?" — you said load, note says
  correlated retry storms amplify a partial failure into a full one.
- "Two things drain does beyond cordon?" — you named eviction, missed respecting
  PodDisruptionBudgets.

Shaky (answered slowly)
- "When does a circuit breaker make an outage worse?" — 40s. Card is doing two jobs;
  split into the half-open probe case and the fallback-path case.

Repairs proposed
- Split the circuit breaker card.
- [[Retry budgets belong at the client]] does not actually state the storm mechanism.
  The note is the problem, not the card. Fix it first.
```
