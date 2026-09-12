# Testing time, randomness, concurrency and I/O

## Contents

- [Time](#time)
- [Randomness](#randomness)
- [Concurrency](#concurrency)
- [I/O and external services](#io-and-external-services)
- [Test ordering and shared state](#test-ordering-and-shared-state)

## Time

The seam is a clock passed in, not a clock called. Code that calls the system clock directly can only be tested by patching the module that calls it, which couples the test to the import path and breaks on every move.

- Python: take a `Callable[[], datetime]` parameter defaulting to `datetime.now`, or use `time-machine`/`freezegun` at the boundary when the code is not yours to change.
- JavaScript: `jest.useFakeTimers()` with `setSystemTime`, and advance the clock explicitly rather than awaiting a real delay.
- Go: take a `clock` interface; the standard trick of a `func() time.Time` field on the struct is enough.
- Java: `java.time.Clock` exists for this; inject `Clock.fixed` in tests.

Cases worth taking whenever date arithmetic is involved: a daylight-saving spring-forward (an hour that does not exist), an autumn fall-back (an hour that happens twice), 29 February, the last day of a 31-day month when adding a month, and a timestamp on either side of midnight in a non-UTC business timezone. Store and compute in UTC and convert only at the edge; a test that passes only in the developer's timezone is a production defect already.

Timeouts and retries need injected time as well, or the test for a 30-second timeout takes 30 seconds. Advance a fake clock instead.

## Randomness

Inject the source. A seeded generator passed into the function makes the case reproducible; `random.seed()` set globally in a test leaks into every other test in the process.

Where randomness is the behaviour under test — sampling, shuffling, load spreading, jitter — assert on a statistical property over many draws (every bucket hit, the mean inside a tolerance, no duplicates) rather than on a specific sequence, and pick the tolerance so the test fails less than once in a million runs. A tolerance tight enough to fail weekly is the most expensive kind of flake, because the team learns the failure is meaningless and stops reading the rest of the suite.

UUIDs, tokens and generated identifiers are the same problem in disguise. Inject the factory, or assert on the shape rather than the value.

## Concurrency

Sleeps are the failure mode. A `sleep` long enough to pass on a laptop is not long enough on a CI runner at four times the load, and it lengthens every run whether or not it was needed.

Use instead:

- A latch, barrier or semaphore the test controls, so the interleaving under test is the one that runs rather than the one that happens to.
- Deterministic schedulers where the language offers one — a single-threaded executor, a manual event-loop pump, Go's `testing/synctest` for synthetic time.
- A poll with a deadline (`waitFor(condition, timeout)`) at true asynchronous boundaries, which fails fast when broken and returns immediately when not.

Run race detectors where they exist: `go test -race`, `ThreadSanitizer`, Java's `jcstress` for memory-model questions. They find the interleaving no hand-written test reaches.

For the class of bug that appears only under contention, write the test to loop a bounded number of iterations with a shared resource, and treat one failure in a thousand runs as a genuine finding rather than noise. A concurrency test that never fails may be one that never actually concurred.

## I/O and external services

| Dependency | Use | Rather than |
| --- | --- | --- |
| Database | The real engine on an ephemeral instance (a container, or a temporary schema per worker) | An in-memory substitute with a different SQL dialect, which agrees with your mental model and not with production. |
| HTTP service you call | A stub server on a local port, or recorded interactions replayed with the recording committed | A mocked client, which stops testing your serialisation, your headers and your error handling. |
| Message broker | A real broker in a container for integration cases; an in-process fake for unit cases | Asserting that `publish` was called, which never once caught a malformed payload. |
| Filesystem | A temporary directory created per test | A path under the repository, which leaks between tests and fails in parallel runs. |
| Clock, randomness, identifiers | Injection, as above | Patching a module path. |

Give every network call in the test suite a short explicit timeout. A hung integration test consumes the CI job timeout and reports as "CI is slow" rather than as a broken dependency.

## Test ordering and shared state

Randomise test order regularly — `pytest-randomly`, `jest --randomize`, `go test -shuffle=on` — and fix what breaks. An order dependence found this way is a genuine defect in the tests and often in the code's global state.

Create state per test rather than cleaning it up afterwards: a test that failed did not reach its cleanup, so the next test inherits the mess and gets blamed. Where creation is expensive, scope the expensive part (a container, a schema) to the session and the mutable part (rows, files) to the test.

Note the boundary with `ci-triage`: this file is about designing a suite that cannot go flaky. A test already failing intermittently in CI is that skill's problem, and its quarantine policy — entry criteria, owner, exit criteria, deletion SLA — is the one to follow rather than inventing another here.
