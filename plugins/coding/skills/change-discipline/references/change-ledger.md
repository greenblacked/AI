# Change ledger

The ledger is the evidence trail for a change: what was done, why, and what showed it worked. It is written while the work happens, one row per action, because a ledger reconstructed afterwards records what seems likely rather than what was observed.

## Contents

- When to keep it, and how much
- Template
- Worked example: a T2 change
- Reading a ledger back

## When to keep it, and how much

| Tier | Ledger |
| --- | --- |
| T0 | None. The diff is the record. |
| T1 | Two lines: the failing test or reproduction and its result, and the gate numbers for the changed function. |
| T2 | The full template below. |
| T3 | The full template, with one actions row per delivered step and a gates table repeated after each step. |

## Template

```markdown
# Change ledger: <short name>

**Tier:** T<n> (re-tiered from T<m> at <point>, if it changed)
**Goal:** <one sentence: the behaviour that will be different>
**Bars:** CRAP <= <n>, no new clone of <n>+ tokens, no surviving or no-coverage mutant on changed lines
(state any project override here and where it comes from)

## Actions

| # | Action | Reason | Evidence |
| --- | --- | --- | --- |
| 1 | <what was done> | <why this and not the alternative> | <command run and its result, or the commit> |

## Gates

| Function or gate | Before | After | Bar |
| --- | --- | --- | --- |
| <file>:<function> CRAP | <n> | <n> | <n> |
| Duplication, new clones | - | <n> | 0 |
| Mutation, survivors and no-coverage mutants on changed lines | - | <n> | 0 |

## Exceptions accepted

| What | Reason | Who accepted |
| --- | --- | --- |

## Mitigations standing (cause still open)

- <the guard that stops the symptom, and what the cause is believed to be>

## Open risks

- <anything not measured, any gate skipped with the owner's agreement, any survivor left as pre-existing>
```

Rules for filling it in:

- The evidence column holds something a reader can rerun or look up: a command and its result, a commit, a path. "Looked fine" is not evidence.
- A "before" figure is measured before the first edit. A before figure measured afterwards is a guess with a number on it.
- Mitigations and fixes are separate sections. A change can ship with a mitigation standing, but it cannot call it a fix.
- An exception names a reason specific to that function. "Legacy code" is a reason for the ratchet to exist, not for an exception to it.

## Worked example: a T2 change

The request: orders may carry a per-customer discount cap, so a stack of promotions cannot take more than the cap off a total.

```markdown
# Change ledger: discount cap

**Tier:** T2 (stayed T2; touches pricing, the customer record and tests)
**Goal:** the total after all promotions never drops below the total minus the customer's cap.
**Bars:** CRAP <= 10, no new clone of 50+ tokens, no surviving or no-coverage mutant on changed lines

## Actions

| # | Action | Reason | Evidence |
| --- | --- | --- | --- |
| 1 | Measured `pricing.py:apply_promotions` before any edit | The function already has an if-chain per promotion kind; its starting score decides how much room the change has | CRAP 13.8 (complexity 9, coverage 61%) |
| 2 | Wrote a failing test: two stacked promotions on a capped customer exceed the cap | A test that fails for the predicted reason fixes the target | Failed with "total 62.00, expected 80.00", which is the missing cap and nothing else |
| 3 | Sketched the design as if caps had always existed: promotions return a discount amount, one function sums them and clamps to the cap | Adding a cap check inside each branch would put the rule in six places | Sketch in the commit body |
| 4 | Split `apply_promotions` into a table of promotion functions and `total_discount` | The restructure the sketch needs, done under the existing tests before adding the cap | Existing suite green, no test edited |
| 5 | Added the cap clamp in `total_discount` only | One decision, one place | Failing test from step 2 now passes |
| 6 | Ran the three gates on the diff | Required at T2 | See gates |
| 7 | Mutation run found one survivor: the clamp's `<` changed to `<=` | At equality both branches return the same amount, so no test can tell them apart: an equivalent mutant, not a missing test | Checked by hand that the two forms agree for every discount and cap; recorded under Exceptions |

## Gates

| Function or gate | Before | After | Bar |
| --- | --- | --- | --- |
| `pricing.py:apply_promotions` CRAP | 13.8 | removed (split) | 10 |
| `pricing.py:total_discount` CRAP | - | 3.0 | 10 |
| Promotion functions, highest CRAP | - | 4.1 | 10 |
| Duplication, new clones | - | 0 | 0 |
| Mutation, survivors and no-coverage mutants on changed lines | - | 0 after step 7 (one equivalent mutant excepted) | 0 |

## Exceptions accepted

| What | Reason | Who accepted |
| --- | --- | --- |
| Equivalent mutant: clamp `<` to `<=` in `total_discount` | Returns the same amount at equality, so it cannot be killed | Reviewer, in the PR |

## Mitigations standing (cause still open)

None.

## Open risks

- Caps are read from the customer record on every call; no caching was added, so a slow customer lookup would now sit on the pricing path. Not measured.
```

Notice what the example does. The first row records a number before any edit, so the after figure means something. The restructure in rows 3 and 4 happens before the new behaviour and under a green suite, so the diff for the cap itself is five lines. And the mutation survivor in row 7 turned into a boundary test, which is the reason the gate exists.

## Reading a ledger back

A reviewer or the next session should be able to answer three questions from the ledger alone: what was the bar, what were the numbers, and what was left unproven. If any answer needs the diff, the ledger was written too late or too thinly.
