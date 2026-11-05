# Test plan

One change, planned before any assertion is written. Fill in every section from the code and
the caller, not from the tests that already exist; delete the guidance in brackets.

## Behaviour and caller

- Change: [one sentence]
- Obligations the code owes its caller: [what it returns, rejects, persists, emits; one line each]
- Who depends on each: [caller, service or user]

## Equivalence classes and boundaries

| Input | Class | Boundary values taken | Why this class is handled alike |
| --- | --- | --- | --- |
| [parameter] | [below minimum / valid / above maximum / empty / one / many] | [min-1, min, max, max+1] | [the rule that splits it] |

- Combinations: [full cross product, or pairwise because the parameters are independent]

## Error paths

| Failure | Where the caller sees it | Expected behaviour |
| --- | --- | --- |
| [timeout / malformed response / auth failure / conflicting write / partial write] | [exception type, exit code, rollback, message] | [what must hold afterwards] |

## Cases and level

| Case name | Class or boundary | Level (unit / integration / none) | What a failure would mean |
| --- | --- | --- | --- |
| [condition_and_expected_outcome] | [class] | [level] | [the regression it catches] |

- Deliberately not tested: [each omission and its reason]

## Seams for time, randomness and I/O

- Clock: [injected clock and the fixed instant, or "not touched"]
- Randomness: [seed and where it is printed on failure, or "not touched"]
- Concurrency: [latch, barrier or deadline-polled wait, or "not touched"]
- I/O: [ephemeral engine, stub server, temporary directory, or "not touched"]

## Reproduction (bug fixes only)

- Reported symptom and the error the reporter saw: [text]
- The test fails with that same error before the fix: [yes / not yet run]
