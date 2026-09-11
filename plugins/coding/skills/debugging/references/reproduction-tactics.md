# Reproduction tactics

What to do when the failure will not reproduce, or reproduces too rarely to experiment
against. Read alongside step 2 of the workflow.

## Contents

- [Diff the environments, one axis at a time](#diff-the-environments-one-axis-at-a-time)
- [Amplifying a race](#amplifying-a-race)
- [Time, clocks and timezones](#time-clocks-and-timezones)
- [Data-dependent failures](#data-dependent-failures)
- [Resource leaks and slow growth](#resource-leaks-and-slow-growth)
- [Network and partial failure](#network-and-partial-failure)
- [When the failure has already gone](#when-the-failure-has-already-gone)
- [When it truly will not reproduce](#when-it-truly-will-not-reproduce)

## Diff the environments, one axis at a time

"Works locally, fails in CI" and "works in staging, fails in production" are the same
problem: two systems differ and you do not yet know along which axis. Print the value
from inside both environments rather than reasoning about what it should be.

| Axis | What to compare | The classic failure |
| --- | --- | --- |
| Code | Resolved commit, not the branch name. Build flags and optimisation level | A stale build, or a release build where the assertion is compiled out |
| Dependencies | The resolved tree, not the manifest: `npm ls --all`, `pip freeze`, `go list -m all` | A floating transitive version that moved yesterday |
| Locale and encoding | `LANG`, `LC_ALL`, default file encoding | Case-insensitive sorting, decimal commas, a UTF-8 default that is ASCII on the runner |
| Timezone | `TZ`, and the database session timezone separately | A test that passes until the office crosses a date boundary against UTC |
| CPU and memory | Core count, cgroup limits, available memory | Thread-pool sizes derived from core count; an OOM that only happens at the container limit |
| File system | Case sensitivity, path length, ordering of directory listings, permissions | An import that works on macOS and fails on Linux because of capitalisation |
| Clock and uptime | Process start time, NTP drift, monotonic versus wall clock | A cache TTL computed from wall clock across an NTP correction |
| Configuration | The fully resolved configuration as the process sees it, dumped at startup | A default that differs from the value someone believes is set |
| Data | Row counts, null distribution, encodings, one specific record | A query plan that flips at a table size that only production has |
| Network | DNS resolution, egress rules, proxies, TLS trust store, MTU | A certificate chain that the runner trusts and the container does not |
| Identity | The principal the process runs as, and its permissions | Works under a developer's credentials, fails under the service account |

Dump the resolved configuration and the resolved dependency tree from both sides into
files and diff them. Two minutes of this beats an hour of hypotheses.

## Amplifying a race

A failure whose rate moves with concurrency is a race, and the rate is a dial you can
turn. Raise it until the bug is reliable, fix it, then check at the raised rate.

- Increase parallelism well past the realistic value: more threads, more workers, more
  concurrent requests than production sees.
- Restrict the process to one CPU (`taskset -c 0`, `GOMAXPROCS=1`) — this changes which
  interleavings are reachable and often exposes a different class than more cores do.
- Add jitter at suspect points: a random small sleep either side of the critical section
  makes narrow windows wide. Remove it before shipping.
- Slow the dependency rather than the code: a proxy that adds latency to the database or
  the downstream service widens every window that depends on it.
- Shrink the pools and caches so eviction and reuse happen constantly.
- Run the language's race detector, which finds races that did not happen to fail:
  `go test -race`, `-fsanitize=thread`, `RUSTFLAGS="-Z sanitizer=thread"`, Java's
  `-XX:+UnlockDiagnosticVMOptions` with a concurrency stress harness.
- For distributed races, run the two callers against the same key deliberately rather
  than waiting for it: a loop issuing the same two requests simultaneously will find a
  check-then-act in seconds.

Record the rate at each setting. A rate that scales with concurrency confirms the class
before you have found the line.

## Time, clocks and timezones

- Run the reproduction under a fixed clock (`libfaketime`, a frozen-time test helper, an
  injected clock interface) so the failure is deterministic and does not require waiting.
- Test the boundaries deliberately: midnight UTC, midnight local, month and year end,
  the two daylight-saving transitions, a leap day, the 23-hour and 25-hour days.
- Check that durations use a monotonic clock. A duration computed from wall-clock
  timestamps goes negative when the clock steps backwards, and negative durations turn
  into enormous unsigned values or immediate timeouts.
- Separate the timezone of the process, the database session and the client. Three
  places, three defaults, and the bug lives where two of them disagree.

## Data-dependent failures

When it fails for one record and not another, the record is the reproduction.

1. Export the failing record and the nearest passing one.
2. Bisect the fields: copy the passing record, replace half its fields with the failing
   record's values, re-run. Halve again. Usually four or five runs to a single field.
3. Once you have the field, look at its exact bytes rather than its rendering —
   `hexdump`, `repr()`, the raw column value. Trailing whitespace, a non-breaking space,
   a combining accent, a CRLF, an emoji outside the basic plane and a null byte all look
   ordinary on screen.
4. Boundary values worth trying directly: empty string, zero, negative zero, one, the
   maximum for the column type, a very long string, a string containing the delimiter
   used downstream, and the value `null` distinguished from absent.

## Resource leaks and slow growth

Leaks do not have a moment of failure, so the reproduction is a gradient rather than an
event.

1. Establish a baseline metric — resident memory, heap size, open file descriptors,
   connection count, thread count, goroutine count — sampled on an interval.
2. Apply a repeating workload and confirm the metric rises and does not return after the
   workload stops. A rise that settles is a cache, not a leak.
3. Take two snapshots an interval apart and diff by allocation site rather than by total:
   `pprof`, `heapdump`, `jmap` plus a heap analyser, `tracemalloc`, `valgrind --leak-check=full`.
4. The diff names the allocation site; the cause is whatever holds the reference. Follow
   the retention path, not the allocation.
5. Common holders: an unbounded map or list keyed by request, a subscription or listener
   never removed, a closure capturing a large object, a connection returned to a pool
   without being reset, a background task that never exits.

## Network and partial failure

Reproduce the failure mode rather than waiting for it.

- Kill the dependency mid-request, not before it — the interesting failures are partial
  responses, half-closed connections and a socket that accepts and never replies.
- Add latency and packet loss deliberately (`tc netem`, a toxic proxy, a stub that sleeps
  past the client timeout) to find the timeout that is absent or wrong.
- Return the error shapes that are not the happy path: a 500 with an HTML body where JSON
  was expected, a 429 with a `Retry-After`, a 200 with a truncated body, a redirect loop.
- Check the failure on the retry path specifically. Most partial-failure bugs are in the
  code that runs the second time.
- Capture the wire (`tcpdump`, `mitmproxy`, the client's own debug logging) before
  theorising about what was sent. Requests are frequently not what the code appears to
  build.

## When the failure has already gone

Capture before remediating; the restart is the evidence-destroying step.

- Application logs around the event, with enough context either side, saved to a file
  rather than left in a rotating buffer.
- The core dump, heap dump or thread dump if the process is still alive. A thread dump
  taken during a hang is the single highest-value artefact for a hang and is free.
- The exact request or message, including headers, and the state of the records it
  touched.
- The versions: the deployed commit, the image digest, the resolved dependency versions,
  the configuration as resolved.
- Metrics and traces for the window, exported rather than linked, since retention is
  shorter than the investigation.

## When it truly will not reproduce

Declare it rather than substituting guesswork, and switch strategy:

1. Add instrumentation to the failing path that would identify the cause on the next
   occurrence — values at boundaries, an assertion on the invariant, a trace attribute
   carrying the suspect state. Ship it, and wait with a better net.
2. Narrow by reasoning where you cannot narrow by experiment: enumerate every way the
   observed state could have been produced, and eliminate the ones contradicted by the
   evidence you do have. Write the list down; it is what makes the next occurrence quick.
3. Consider making the failure impossible rather than finding it — an invariant enforced
   at the boundary, a type that cannot represent the bad state, a unique constraint — and
   be explicit that this is mitigation without diagnosis.
4. Set a time budget and say what you spent it on. An unreproducible bug that has
   consumed two days with a written record of what was excluded is a legitimate handover;
   one with no record is a repeat of the same two days for whoever picks it up.
