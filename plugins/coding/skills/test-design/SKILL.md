---
name: test-design
description: "Choose what to test before writing a test: partition the input space into equivalence classes and take the boundary of each, enumerate the error and exception paths nobody writes, cut a combinatorial explosion down with pairwise selection, place every case at the unit, integration or no level at all, pin time, randomness, concurrency and I/O behind seams so the suite cannot go flaky, and keep only tests that would catch a regression rather than tests that pin the current implementation. Use this skill whenever someone asks \"what should I test here\", \"are these tests any good\", \"is our coverage enough\", \"how do I test this without it being flaky\", or wants a failing test that reproduces a reported bug before the fix lands. Do not use it to triage a test already red in CI (ci-triage), to find the cause of a bug (debugging), or to restructure code (refactoring)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(pytest:*), Bash(coverage:*), Bash(jest:*), Bash(go:*), Bash(git:*)
---

# Test Design

A suite is finished when every test names a behaviour a user or caller depends on, fails for exactly one reason, and would go red if that behaviour regressed — and when the cases that are absent are absent by decision rather than by oversight.

Test selection goes wrong in five specific ways. The happy path gets three tests and the error paths get none, because the error paths are the ones nobody imagined while writing the feature. The boundary is skipped — the test uses 5 where the code branches at 10, so the off-by-one it was written to catch survives it. The input space is enumerated exhaustively until the suite takes twenty minutes and nobody runs it locally. Time, randomness, concurrency and network are left live, so the suite fails on a Tuesday and the team learns to re-run rather than read. And coverage becomes the target, which produces tests that execute lines and assert nothing, scoring 90% while catching nothing. The workflow below forces the selection to happen explicitly, before a single assertion is written.

## Scope

Use for: deciding which cases a change needs, reviewing whether an existing suite tests anything, choosing the unit/integration/end-to-end level for a case, designing around time, randomness, concurrency and I/O, interpreting a coverage number, and writing the reproduction test for a reported bug.

Do not use for: a test that is already failing in CI and may be a flake, which is `ci-triage` and owns the quarantine policy; locating the cause of a defect, which is `debugging`; restructuring code under an existing suite, which is `refactoring`; judging a colleague's diff, which is `code-review`.

## Workflow

### 1. Name the behaviour, not the function

Write one sentence per obligation the code owes its caller: what it returns, what it rejects, what it persists, what it emits. A test whose name is `test_process` tests nothing in particular; `rejects_a_transfer_that_would_overdraw` names a promise that can regress. If you cannot phrase the obligation without naming a private helper, the case belongs a level up.

Stop the list at obligations. Ordering of internal calls, the presence of a field the caller never reads, and the exact wording of a log line are implementation, and pinning them buys a test that fails on every refactor and finds no bug.

### 2. Partition the input space, then take the boundaries

For each parameter, split the domain into classes where every member is expected to be handled identically, and take one value from each class plus the values either side of every class edge. A class with no boundary test is a class you have guessed at.

| Input shape | Classes worth separating | The boundary values to take |
| --- | --- | --- |
| A bounded number, such as a retry count or a quantity | Below minimum, the valid range, above maximum, and zero if zero is special | Minimum minus one, minimum, maximum, maximum plus one — most off-by-ones live at exactly one of these four. |
| A collection | Empty, exactly one element, many, and at the paging or batching limit | Zero, one, the limit, the limit plus one — empty and one-element are where aggregation and "first element" logic break. |
| A string | Empty, whitespace only, maximum length, and one containing characters outside the ASCII range | Length zero, length at the column or protocol limit, and a multi-byte grapheme that makes byte length differ from character length. |
| A date or timestamp | Past, present, future, and the ranges the business rules split on | Midnight, the daylight-saving transition, the last day of a month, and 29 February — these are where date arithmetic written against a 30-day mental model fails. |
| An optional or nullable value | Present, absent, and present-but-empty | Absent and empty separately, because code that treats them the same is usually wrong for one of them. |

Two values from the same class are one test and one duplicate. Cut the duplicate; the time it costs is spent on an error path instead.

### 3. Enumerate the error paths deliberately

Ask, for each external interaction and each input: what does this do when it fails, and is that behaviour something a caller depends on? The usual missing set is a timeout, a malformed or truncated response, an authorisation failure, a conflicting concurrent write, a partial write followed by a failure, and a resource that has gone away since it was checked.

Test the error path where the caller can observe it — the exception type, the exit code, the rollback, the retry count, the message the user sees. Asserting merely that "an exception was raised" without the type or the state afterwards passes when the code raises the wrong error for the wrong reason.

### 4. Cut the combinations with pairwise selection

When independent parameters multiply, full enumeration is unaffordable and unnecessary: four parameters at three values each is 81 cases, and a pairwise set covering every pair of values at least once is roughly 9 to 12. Most defects triggered by combinations are triggered by a pair rather than by a specific triple, so pairwise is the default when the cross product exceeds about twenty cases.

Enumerate fully instead when the parameters genuinely interact — a pricing matrix, a permission grid, a protocol state machine — and say so in a comment, because otherwise the next person will thin it. Read `references/case-selection.md` when the cross product is large enough that you are about to guess at which combinations matter.

### 5. Place each case at the cheapest level that can catch it

| The thing that could break | Test it here | Because |
| --- | --- | --- |
| A branch, a calculation, a parser, a state transition | Unit test, in-process, no I/O | It is the only level where you can afford the twenty boundary cases the logic needs, and it fails in milliseconds with the cause in the name. |
| A query, a schema constraint, a serialisation format, a transaction boundary | Integration test against the real engine, not a fake | A mocked database agrees with your mental model of SQL rather than with the database, which is precisely the disagreement that breaks production. |
| A contract between two services you both own | Contract test pinning the shape both sides agreed | It fails on the producer's build rather than in the consumer's integration environment three days later. |
| One critical user journey end to end | A small number of end-to-end tests, counted and owned | They are the slowest and flakiest tests you own, so they earn their place only for journeys where failure is not recoverable. |
| A third-party library behaving as documented | Nothing | You are testing someone else's code; when their behaviour matters, pin it with one integration test at your boundary instead. |
| A getter, a data class, generated code | Nothing | The test restates the code and fails only when both are changed together. |

Push cases down the pyramid until they stop being catchable. A suite whose slow tests outnumber its fast ones gets run less often, and a test nobody runs before pushing is documentation.

### 6. Remove non-determinism at the seam, not with a sleep

Each of the four sources needs an injection point rather than a workaround. Read `references/determinism.md` when a test touches the clock, a random source, more than one thread, or the network.

- **Time.** Inject a clock and pass a fixed instant. Never assert on `now()`; a test that passes at 23:59 and fails at 00:00 is teaching the team to ignore the suite.
- **Randomness.** Seed the generator explicitly and record the seed in the failure output, so a property-based failure is reproducible rather than a story.
- **Concurrency.** Drive the interleaving from the test with a latch or barrier rather than waiting on a sleep. A `sleep(0.5)` is a race with a longer fuse and it fails on a loaded CI runner, not on your laptop.
- **I/O.** Use a real engine on an ephemeral instance for the database, a stub server for HTTP, and a temporary directory for the filesystem. Reset state by creating it fresh per test rather than by deleting afterwards, because a test that failed did not run its cleanup.

Order dependence is the fifth source and is caught, not designed around: run the suite in a randomised order regularly, and fix what breaks rather than pinning the order.

### 7. Ask what each test would catch

Apply one question to every test before keeping it: name a plausible change to the production code that would make this test fail and would also be a bug. If the only changes that break the test are renames and reorderings, the test pins the implementation and costs more than it returns.

The mechanical version of the same question is mutation testing: change a `>` to a `>=`, invert a condition, delete a line, and see whether the suite notices. A surviving mutant is a hole the coverage number cannot see. Run it on the modules where a defect is expensive rather than across the whole repository, because it costs a full suite run per mutant.

### 8. Reproduce a reported bug before fixing it

Write the failing test first, from the report, in this order: reproduce the reported symptom exactly, run it and watch it fail with the same error the reporter saw, then fix the code, then watch it pass. A test written after the fix confirms your understanding of the fix; a test written before it confirms the bug existed.

Narrow the reproduction after it is red, not before — start from the end-to-end path the reporter used, then push it down to the smallest level that still fails, so the test that lands is fast and the cause is already localised. Keep the bug's identifier in the test name, because the next person to see that assertion needs to know it is load-bearing rather than arbitrary.

## What coverage tells you

Line and branch coverage measure which lines were executed, not which behaviours were checked. A test with no assertions covers every line it touches, so a coverage number is a lower bound on what is untested and says nothing about what is tested.

Use it in exactly two ways. Read the uncovered list, because an uncovered error path is a genuine finding worth acting on. And watch the direction of travel on changed lines, because coverage falling on a diff means new code arrived without tests. Setting a global percentage target instead produces assertion-free tests written against the lines cheapest to execute — usually getters and generated code — which raises the number and lowers the information.

Branch coverage is worth more than line coverage, because a one-line `if` is fully line-covered by a test that never takes the false path. Where the tool offers it, measure branches and ignore the line figure.

## Choosing a test double

Pick by what the test needs to observe, not by which library is already imported. The wrong double is how a suite ends up asserting on its own configuration.

| What the test needs | Double to use | The failure the alternative causes |
| --- | --- | --- |
| A dependency that must return a canned value so the code under test can proceed | A stub, returning data and nothing else | A mock with call expectations here couples the test to how many times the code asks, which is implementation. |
| Proof that an outgoing effect happened — an email sent, an event published | A spy recording the calls, asserted once at the end | Asserting on the return value alone lets a silently dropped side effect pass. |
| The real behaviour of a stateful collaborator — a queue, a store, a cache | A fake with a working in-memory implementation, or the real thing | A stub returning fixed values cannot express state, so the test passes for sequences the real dependency would reject. |
| A third-party HTTP API you cannot call in tests | A stub server speaking the real protocol, from a recorded interaction | A mocked client skips your serialisation, headers and error handling, which is where the defects are. |
| Nothing — the dependency is pure and fast | The real object | Every double is a copy of a contract that will drift; do not create one you do not need. |

Count the doubles per test. More than two or three means the code under test has too many collaborators, and that is a design finding worth reporting rather than a mocking problem to solve.

## Naming and failure output

A test name states the condition and the expected outcome, so a failure in a CI summary is diagnosable without opening the file: `rejects_a_transfer_that_would_overdraw`, not `test_transfer_2`. One reason to fail per test — a test with four unrelated assertions reports only the first, and the other three are untested until someone fixes it.

Make the failure message carry the input. An assertion that prints `expected True, got False` costs the next reader a debugger session; one that prints the case's parameters and the actual value costs them nothing. Parameterised tests need the parameter in the generated case name for the same reason.

## Output format

Report a test design in this shape, before writing the tests:

```markdown
## Behaviours under test
[One line per obligation the code owes its caller.]

## Cases
[Table: case name | class or boundary it represents | level (unit/integration/e2e) | what a failure would mean.]

## Deliberately not tested
[Each omission with its reason — covered by a lower-level case, third-party behaviour, or accepted risk.]

## Non-determinism
[Each of time, randomness, concurrency, I/O that this code touches, and the seam used to control it. Omit any it does not touch.]

## Coverage note
[Uncovered branches that matter, and why. Omit if the design is complete.]
```

## Anti-patterns

**The assertion-free test.** Calls the code, asserts nothing, and turns green forever while raising coverage. It is worse than no test because the number it produces is read as evidence. Every test asserts on an observable outcome or is deleted.

**Testing the mock.** The test configures a stub to return a value, calls the code, and asserts the stub was called. It passes when the real dependency changes its contract, so it catches nothing and blocks every refactor. Assert on the result the code produced, and pin the dependency's contract with one integration test.

**One test per function.** Produces exactly one case for a function with six branches and zero for the error paths. Cases come from behaviours and boundaries, not from the shape of the source file.

**Boundary-adjacent values.** Testing 5 and 50 against a rule that changes at 10 exercises the middle of two classes and neither edge, which is where the off-by-one lives. Take the edge and both its neighbours.

**The sleep-based wait.** `sleep(2)` makes the suite two seconds slower on every run and still fails on a loaded runner. Wait on the condition — a latch, a poll with a deadline, a completion callback — so the test is both faster and deterministic.

**A shared fixture that tests mutate.** One test's leftover row makes another fail, and which one fails depends on execution order, so the failure is blamed on whichever test ran second. Build state per test and let the ephemeral instance be thrown away.

**Snapshot tests of everything.** A snapshot over a whole rendered page or serialised object fails on every unrelated change and is updated without being read, which converts the assertion into a rubber stamp. Snapshot the small things whose exact shape is the contract.

**Chasing a coverage percentage.** The cheapest way to move the number is to execute trivial code without asserting on it, so a target reliably produces the least valuable tests available. Gate on coverage of changed lines and on the uncovered-branch list instead.

**Fixing a bug before reproducing it.** Without a red test first you cannot tell whether the fix worked or whether the bug was never in the code path you changed, and the regression test you eventually write is shaped by your fix rather than by the defect.

**Conditionals inside a test.** An `if` in a test means it asserts different things on different runs, and the branch that never executes hides a case nobody notices is missing. Split it into two tests.

## Reference files

- `references/case-selection.md` — read when the cross product of parameters exceeds about twenty cases, or when choosing between a hand-picked table, pairwise selection and a property-based generator.
- `references/determinism.md` — read when a test touches the clock, a random source, more than one thread, or the network: the seams to inject at, per-language, and the failure each one prevents.
- `references/legacy-suites.md` — read when inheriting a suite with unknown value: how to tell a load-bearing test from a pinned implementation, and the order in which to delete.
