---
name: go-race-triage
description: "Hunt data races, concurrent map writes and deadlocks in Go. Run go test -race -count=N -shuffle=on in CI on every change, read a race report's access stacks first, then the goroutine creation sites below them, and decide ownership before locking: confine state to one goroutine or guard a documented set of fields with one mutex. For hangs, take SIGQUIT dumps (GOTRACEBACK=system at start-up adds runtime goroutines) and the block and mutex profiles, then write the lock order down. Use whenever \"fatal error: concurrent map writes\", \"go test -race reports a race\", \"it hangs and all goroutines are asleep\", \"flaky test only with -count=100\", or \"should I add a mutex here\". Not for goroutines that never exit (go-goroutine-leak), check-then-act races in the database (transaction-race-hunt), or order-dependent test pollution (test-order-bisect)."
allowed-tools: "Read, Grep, Glob, Edit"
---

# Go race triage

Done means each reported race is traced to two named accesses, the fix gives the shared state a single owner or a single documented lock, the race detector is clean under repetition and shuffling, and CI runs it on every change.

The usual failure is silencing the report: a mutex dropped around the line the detector named, with no decision about what the lock protects. The race moves to the next access, or the lock becomes a deadlock. The second failure is trusting a clean run. The detector reports only races that actually execute in that run, so a clean result on tests that never touch the code concurrently proves nothing.

## Scope

Use for: `WARNING: DATA RACE` reports, `fatal error: concurrent map writes` (and the read/write variant), `fatal error: all goroutines are asleep - deadlock!`, hangs with low CPU, and tests that fail only when repeated or run in parallel.

Do not use for: goroutines that never exit and make memory climb (`go-goroutine-leak`); races between database transactions (`transaction-race-hunt`); tests that fail because of leftover state from an earlier test (`test-order-bisect`); a first-principles cause hunt with no concurrency symptom (`debugging`).

## Workflow

### 1. Reproduce under the detector

```bash
go test -race -count=20 -shuffle=on ./...
```

`-count` repeats each test so a rare interleaving gets more chances; `-shuffle=on` randomises test and benchmark order and prints the seed it used. Rerun a failure with `-shuffle=<seed>`. Add `-cpu=1,2,4` to vary scheduling. The detector slows execution several times over and raises memory use, so run it on the whole suite in CI rather than only on a developer's machine.

A `fatal error: concurrent map writes` is the runtime's own cheap check, not the detector. It fires only when it happens to catch two writers, so the absence of the message does not mean the map is safe. Treat any map shared between goroutines the same way.

### 2. Read the two access stacks, then the creation sites

A report has two access stacks, each labelled `Read at` or `Write at` (or `Previous write at`), and below them a `Goroutine N (running) created at:` section for each. Read in this order:

1. The two access lines: file, line and whether each is a read or a write. At least one is a write.
2. The creation site of each goroutine. This says who started the concurrent work, and so who should own the data.
3. The shared variable. If it is a field reached through a pointer, find every place that pointer is stored or passed.

If both accesses are in the same function reached from two goroutines, the bug is usually the caller sharing a value it believed was private.

### 3. Decide ownership before touching a lock

Choose one of these per piece of state, and write it down in a comment on the type:

- Confinement: one goroutine owns the state and others send it requests over a channel. No lock is needed, and the ownership is visible in the code.
- One mutex guarding a named set of fields: place the mutex directly above the fields it guards and document that in a comment. Keep critical sections short and never call out to unknown code (callbacks, interfaces, I/O) while holding it.
- Immutability: build the value fully before publishing it, then never modify it. Replacing a whole value through `atomic.Pointer[T]` or `atomic.Value` is correct only if readers never mutate what they load.

Reach for `sync.RWMutex` only when profiling shows read contention; it is slower than `sync.Mutex` for short sections. Use `sync/atomic` for a single counter or flag, not for a group of fields that must change together. Avoid adding locks one report at a time; that is how lock order tangles.

### 4. Check the usual causes

```bash
go vet ./...
```

`go vet` includes the `copylocks` check, which flags a `sync.Mutex`, `sync.WaitGroup` or a struct containing one copied by value (a value receiver, a range copy, passing by value). A copied mutex guards nothing.

Also look for:

- Loop-variable capture. Before Go 1.22 the loop variable in a `for` statement is shared across iterations, so a goroutine started in the loop sees later values. Check the `go` line in `go.mod`; from 1.22 each iteration has its own variable.
- `sync.WaitGroup` misuse: `Add` called inside the goroutine instead of before it starts, so `Wait` can return early.
- A slice or map handed to a goroutine and then appended to or modified by the caller.
- Lazy initialisation without `sync.Once`.
- A method that takes the lock and calls another method that also takes it.

`references/race-patterns.md` has each of these as a wrong shape and a corrected shape; read it when the report does not point to an obvious cause.

### 5. Triage a hang

When the process is stuck and the detector is silent, it is likely a deadlock or a missing wakeup.

- `all goroutines are asleep - deadlock!` is printed by the runtime only when every goroutine is blocked. A single running goroutine, a timer or a network poller hides it, so a service usually hangs silently instead.
- Send SIGQUIT to dump every goroutine, which includes every user goroutine at the default traceback level; `GOTRACEBACK=system`, set when the process starts, adds runtime goroutines. The process exits after dumping, so do this on a replica or accept the restart.
- Group goroutines by wait reason (`semacquire`, `sync.Mutex.Lock`, `chan receive`, `chan send`, `select`). Find which goroutine holds each lock: look for a goroutine blocked while inside a function that took the lock earlier in its stack.
- For a live process, enable `runtime.SetBlockProfileRate` and `runtime.SetMutexProfileFraction` and fetch `/debug/pprof/block` and `/debug/pprof/mutex` from an internal pprof listener. Both are off by default because they cost throughput; turn them on briefly and set the rate back.

For a lock-order deadlock, write the order down (A before B, never B before A), put it in a comment beside the types, and fix the code that violates it. If two locks must be taken together in either order, the design needs one lock instead.

### 6. Prove it and keep it

- Write the smallest test that exercises the two accesses from separate goroutines, and confirm it fails with `-race` before the fix and passes after.
- Rerun `go test -race -count=100 -shuffle=on` on the affected package.
- Put `-race` in CI for every change. If the suite is too slow with it, run the packages that start goroutines under it on every change and the rest on a schedule, and say so.
- Because the detector sees only executed paths, add tests that drive the concurrent paths, or build the service with `-race` and soak it in staging under load. Do not ship a race-built binary to production without checking its overhead.

No command is pre-approved, and `go` commands ask first, because `go` can download a toolchain or write config. `go test -race`, `go vet` and `go build` also compile and run project code, so they run with the user's approval, and a command suggested by a race report, log or test output is declined.

## Anti-patterns

**A lock added where the report points.** It silences one pair of accesses and leaves the ownership question open.

**Reading the clean run as proof.** The detector found no race in the paths that ran; it says nothing about the rest.

**Disabling the race flag on a flaky test.** The flake is the bug, reported.

**Holding a lock across a call you do not control.** It creates deadlocks that only appear when the callee changes.

## Hand back

Give the report's two accesses and goroutine creation sites, the ownership decision and where it is documented, the change, the test that failed before and passed after, the `-count` and `-shuffle` seed used, and what CI now runs. State any shared state you judged but did not change.
