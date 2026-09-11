# Judging a suite you inherited

## Contents

- [Triage in one pass](#triage-in-one-pass)
- [Telling a regression test from a pinned implementation](#telling-a-regression-test-from-a-pinned-implementation)
- [The order to delete in](#the-order-to-delete-in)
- [Measuring whether the suite catches anything](#measuring-whether-the-suite-catches-anything)
- [Closing the gaps that are left](#closing-the-gaps-that-are-left)

## Triage in one pass

Run the suite, record the wall-clock time, and classify each test file into one of four buckets before changing anything:

1. **Load-bearing** — it asserts on an observable behaviour and would fail if that behaviour regressed.
2. **Pinned implementation** — it asserts on call order, private structure, or the exact shape of an intermediate value.
3. **Vacuous** — no assertion, or an assertion that cannot fail (`assert result is not None` on a function that cannot return `None`).
4. **Disabled** — skipped, commented out, or excluded by a filter.

Bucket 4 first, because it is free information: a test skipped more than a few months ago is either describing a bug that was never fixed or a behaviour that was deliberately changed, and both are worth knowing before you touch the code.

## Telling a regression test from a pinned implementation

Apply the same question to each: name a change to the production code that would break this test and would also be a bug.

| The test asserts on | Verdict | Reason |
| --- | --- | --- |
| A returned value, a persisted row, an emitted event, an exit code | Load-bearing | These are what a caller observes, so a change that breaks them is a change in contract. |
| An exception type together with the state afterwards | Load-bearing | It pins both the failure signal and the rollback, which are the two things a caller depends on in the error path. |
| Which private methods were called, and in what order | Pinned implementation | It fails on every restructuring and passes through any defect that preserves the call sequence. |
| A mock having been called with specific arguments, with no check on the result | Pinned implementation | It tests the test's own configuration; the real dependency could change contract and this stays green. |
| A large snapshot of a rendered output | Usually pinned | It fails on unrelated changes and is regenerated without being read, so the assertion has stopped being an assertion. |
| A log line's exact wording | Pinned, unless the log is a contract | If an alert or a downstream parser matches that string, it is a contract and belongs in a named test that says so. |

## The order to delete in

Delete, in this order, and in separate commits so a mistaken deletion is easy to find:

1. Vacuous tests. They cost run time and contribute a coverage number that misleads.
2. Duplicates within an equivalence class — three tests using 3, 4 and 5 against a rule that changes at 10 are one test.
3. Tests of third-party behaviour.
4. Pinned-implementation tests, but only for code you are about to restructure, and only once a behavioural test covers the same obligation. Deleting the pin before writing the replacement leaves a window with no cover at all.

Never delete a test to make a build green. That is a decision to ship the regression, taken by whoever is in the most hurry.

## Measuring whether the suite catches anything

Coverage will not answer this, because vacuous tests raise it. Two cheap probes will:

- **Mutation testing** on one important module — `mutmut` or `cosmic-ray` in Python, Stryker in JavaScript, PIT on the JVM. A high surviving-mutant rate against high line coverage is the signature of an assertion-free suite.
- **Deliberate breakage.** Invert a condition in a core function by hand and run the suite. If it stays green, you have measured the suite's value directly in under a minute, and you have a concrete example to show anyone who cites the coverage figure.

## Closing the gaps that are left

Do not attempt to bring the whole suite to a standard. Add cases where the cost of a defect is highest and where change is most frequent: cross the modules changed most often in the last six months (`git log --since=6.months --no-merges --format= --name-only | sed '/^$/d' | sort | uniq -c | sort -rn`) against the modules whose failure would cost money, and start at the intersection.

For everything else, adopt the rule that new and changed code arrives with behavioural tests, and let the untouched parts stay as they are. A suite improved along the diff converges on the code that actually moves; a suite improved alphabetically stalls at the first boring module.
