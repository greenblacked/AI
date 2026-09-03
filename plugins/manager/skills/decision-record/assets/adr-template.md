---
status: proposed
date: [TK: YYYY-MM-DD]
decision-makers: [TK: names]
consulted: [TK: names or teams with expertise, consulted in two-way conversation]
informed: [TK: names or teams kept up to date, one-way]
---

# [Decision] [Short title naming the choice, not the problem]

Reversibility: [type-2, reversible — undo costs [TK: effort] | type-1, one-way — undo costs [TK: effort]]

## Context and Problem Statement

[Two or three sentences: the situation, and what forces a decision now. Link the ticket,
incident or document that triggered it. Do not describe the solution here.]

[Optional: state the question explicitly. "Should we X or Y?"]

## Decision Drivers

[Only constraints that discriminate between the options. Drop anything all options satisfy.]

* [driver 1 — e.g. must hold [TK: volume] with [TK: retention]]
* [driver 2]
* [driver 3]

## Considered Options

[At least two. "Do nothing" counts and is often the honest runner-up.]

* [Option 1]
* [Option 2]
* [Option 3]

## Decision Outcome

Chosen option: "[Option N]", because [one sentence tying back to the drivers].

### Consequences

* Good, because [effect — with a source link if it carries a number]
* Bad, because [cost we are accepting knowingly]
* Neutral, because [change that is neither, but that someone will notice]

[A record with no bad consequence has not been thought about.]

### Confirmation

[Name a mechanism, not an intention: a fitness function, an automated test, an
architecture lint rule, a dashboard panel with a threshold, or a scheduled review with a
named owner and a date. If none has been agreed, write:
[TK: no verification mechanism agreed] and leave it visible.]

* Check: [what is measured]
* Where: [link to test, dashboard or CI job]
* Owner and date: [TK: name, date]

## Pros and Cons of the Options

### [Option 1]

[One-line description or link.]

* Good, because [argument]
* Neutral, because [argument]
* Bad, because [argument]
* Rejected because: [the specific reason — required for every option not chosen]

### [Option 2]

* Good, because [argument]
* Bad, because [argument]
* Rejected because: [reason]

### [Option 3]

* Good, because [argument]
* Bad, because [argument]
* Rejected because: [reason]

## More Information

[Links to the design doc, benchmark data, vendor evaluation, related ADRs. If this
record supersedes another, link it here and set the older record's status to
`superseded by ADR-NNNN`. If it was superseded later, link forward.]

[If the decision has a revisit date, state it: "Revisit by [TK: date] if [TK: signal]."]
