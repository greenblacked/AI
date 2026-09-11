# Selecting cases when the input space is large

## Contents

- [Choosing the technique](#choosing-the-technique)
- [Pairwise selection by hand](#pairwise-selection-by-hand)
- [Decision tables for interacting rules](#decision-tables-for-interacting-rules)
- [Property-based testing](#property-based-testing)
- [State machines](#state-machines)

## Choosing the technique

| Situation | Technique | Why this one |
| --- | --- | --- |
| Under about twenty combinations | Enumerate them all in a parameterised table | Cheaper to write than any selection scheme, and complete, so nobody has to justify an omission later. |
| Independent parameters whose cross product exceeds twenty | Pairwise selection | Most combination defects are triggered by a pair of values, so pairwise covers the realistic failure space at a small fraction of the cost. |
| Parameters that genuinely interact — pricing, permissions, tax rules | A decision table, enumerated fully | Pairwise assumes independence. Where the rules interact, the triple you dropped is exactly the one the business cares about. |
| An invariant that should hold across the whole domain | Property-based testing with a seeded generator | A single property replaces dozens of examples and finds the input you would never have thought to write down. |
| An object with a lifecycle | Model the state machine and cover every transition, valid and invalid | Defects cluster in the transitions nobody drew, particularly the ones back out of a terminal state. |

## Pairwise selection by hand

For four parameters at three values each, the cross product is 81 and a pairwise set is around 9.

1. Order the parameters by number of values, descending. The largest two drive the row count.
2. Write out every pair of values of the first two parameters — that is the skeleton.
3. Fill each remaining column greedily, choosing at each row the value that covers the most pairs not yet covered.
4. Sweep for uncovered pairs and add rows only for those.

Two adjustments matter in practice. Force the all-defaults row in, because it is the configuration most users run and a greedy fill will not necessarily produce it. And add any combination that has caused a production incident, permanently and with the incident reference in the comment, regardless of what the algorithm says.

Generators exist — `allpairspy` in Python, `PICT` as a standalone tool, `jqwik` combinators on the JVM — and are worth it above about six parameters. Commit the generated table rather than generating it at test time, so the case set is reviewable in a diff and stable across runs.

## Decision tables for interacting rules

Write the conditions as rows and each rule as a column, with the action at the bottom. The table is finished when every combination of conditions maps to exactly one action, and the value of the exercise is that the gaps are visible: a combination with no action is a specification defect found before any code was written.

Collapse columns only where the action is identical *and* the reason is identical. Two rules that happen to return the same value today for different reasons are two cases, because they diverge the first time the rule changes.

## Property-based testing

Use it where an invariant is easier to state than the examples: a round trip (`decode(encode(x)) == x`), an ordering that must be preserved, an idempotence claim, a conservation law such as a ledger summing to zero, or agreement with a slow reference implementation.

Rules that keep it useful rather than decorative:

- Seed the generator explicitly and print the seed on failure. An unreproducible property failure is a rumour.
- Commit the shrunk counterexample as an ordinary example test once it is found. The property finds it; the example test keeps it found, in a millisecond, forever.
- Constrain the generator to the domain the code actually accepts, rather than adding guards inside the property. A property that discards 95% of its inputs is testing the guard.
- Bound the run count in CI and raise it in a nightly job. Properties are the one test type where more runs genuinely buys more coverage, and where you do not want that cost on every push.

## State machines

List the states, list the events, and fill the grid. Every cell is either a transition to test or an invalid event whose rejection is itself a case — and the rejection cases are the ones that are usually missing.

Pay particular attention to: the event that arrives twice (idempotence), the event that arrives out of order, the transition out of a terminal state (which should be rejected, not silently ignored), and any transition that also writes to an external system, because that one is where a crash between the write and the state change leaves an inconsistency.
