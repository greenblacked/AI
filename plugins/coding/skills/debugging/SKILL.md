---
name: debugging
description: "Drive a failure down to a proven cause before changing any code: capture the exact failure and its conditions, reproduce it reliably, reduce it to the smallest case that still fails, form one falsifiable hypothesis at a time, bisect through history and through the input, instrument instead of guessing, then prove the fix by turning the failure off and on again. Use this skill whenever a program misbehaves and nobody knows why — \"this crashes sometimes and I cannot work out why\", \"it works on my machine\", \"the test passes locally but not on the runner\", \"it worked yesterday and nothing changed\", \"intermittent 500s in the order service\", \"I have been staring at this for three hours\". Not for classifying a red pipeline, which is ci-triage; not for restoring a broken cluster workload or running a live outage, which is k8s-triage; not for judging someone else's diff, which is code-review."
allowed-tools: "Read, Grep, Glob, Edit, Bash(git:*), Bash(rg:*), Bash(jq:*), Bash(python:*), Bash(node:*), Bash(go:*), Bash(pytest:*), Bash(npm:*), Bash(curl:*)"
---

# Debugging

Debugging is finished when you can turn the failure on and off at will by making one change and reverting it, and can say in one sentence why that change is the cause.

The job goes wrong in four ways, all of which feel like progress. The first is editing before reproducing: a change is made against a guess, the symptom moves, and now the system differs from the one that failed with no record of how. The second is the multi-variable fix — three things changed at once, the failure went away, and nobody knows which one mattered, so the same bug returns in a month wearing different clothes. The third is mistaking location for cause: the top frame of a stack trace is where the program noticed, which is usually several layers below where it went wrong, and a null check added there converts a loud failure into a silent one. The fourth is credulity about absence — the failure stops, and its stopping is accepted as evidence, when a restart, a cache expiry, a deploy or a quieter hour is at least as likely an explanation. This skill imposes two gates: no edits until there is a reproduction, and no claim of a fix until the failure has been switched off and back on. Everything else is in service of those two. Microsoft's Time Warp study puts debugging at roughly 9% of developer time, ahead of code review, so the cost of doing it by guesswork is paid continuously rather than once.

## Scope

Use for: a crash, a wrong answer, a hang, a leak, a corruption, an intermittent failure, a performance cliff; a test that fails only in one environment; a regression that appeared without an obvious change; narrowing a failure to the commit, the input or the configuration that causes it.

Do not use for: classifying a red pipeline and deciding whether it is a flake, infra or a real break, which is `ci-triage` — come here once it is classified as a real application defect; restoring a misbehaving Kubernetes workload or running a live outage, which is `k8s-triage`; reviewing a change for defects nobody has observed yet, which is `code-review`; deciding what a suite should cover once the bug is fixed, which is `test-design`; restructuring code that already works, which is `refactoring`.

## Hard gates

Each of these exists because breaking it produces a confident wrong answer, which costs more than no answer.

1. No edit to product code until the failure reproduces on demand, or until you have written down explicitly that it cannot be reproduced and what you are doing instead.
2. One variable at a time. Two simultaneous changes make every result uninterpretable.
3. One hypothesis at a time, stated before the experiment, with the observation that would falsify it.
4. The fix is not proven until reverting it brings the failure back and reapplying it removes the failure.
5. Record every experiment and its result as you go. Debugging that lasts more than an hour outlives your memory of what you have already ruled out.
6. Change nothing in the failing environment before capturing its state. Logs, cores, heap dumps and the exact input are destroyed by the restart that was going to fix it.

## Workflow

### 1. Capture the failure exactly

Before anything else, write down what actually happened, in the system's words rather than yours.

- The verbatim error, the full stack trace, and the log lines either side of it — not a paraphrase. A paraphrased error cannot be searched for and drops the detail that turns out to matter.
- The exact input, request, message or command that produced it. Save it to a file.
- Time, host, version or commit, configuration, and the environment. "It failed in staging" is missing the commit.
- The expected result, stated concretely. "It should have returned 402 with `insufficient_funds`" is a testable claim; "it should work" is not.
- Frequency: always, one in ten, once. This decides which of the paths in step 2 you are on.

For anything intermittent or already gone, preserve the evidence first — copy the log, keep the core file, snapshot the database row, keep the request body — because the first remediation anyone attempts will destroy it.

Then read the stack trace properly. The top frame is where the program detected the problem; the cause is where the bad value was created, which is usually further down or in an earlier call that has already returned. Walk the frames outward asking at each one "was the state already wrong when it arrived here?" and stop at the first frame where the answer is no. That frame is the boundary the bug crossed.

### 2. Reproduce it reliably

This is the gate. The measure is a command you can run that fails, repeatably, and whose failure you can then make stop.

```bash
git checkout <the-exact-failing-commit>
./run-repro.sh            # one command, prints PASS or FAIL, exits accordingly
for i in $(seq 1 20); do ./run-repro.sh; echo "run $i: $?"; done
```

Build the reproduction in the cheapest environment where it still fails, and check at each step that it still does: production, then a staging copy with the same data, then a local run with the captured input, then a unit test. Many bugs stop reproducing as you move down this ladder — that is not a failure of the process, it is the finding. The step at which it stops reproducing names the difference that matters, and that difference is now your first hypothesis.

Record the failure rate rather than a feeling. "Fails 3 times in 20" is a baseline you can compare a fix against; "flaky" is not. For anything below 100%, decide your run count from the rate now: a fix for a one-in-twenty failure needs about sixty clean runs before "it stopped" means anything, and a single green run means nothing at all.

**When it will not reproduce.** Do not start editing. Work the difference instead: diff the failing environment against the working one along one axis at a time — version, configuration, data, dependencies, locale and timezone, CPU count and memory, network reachability, clock, file system case sensitivity, environment variables. Add instrumentation to the failing environment (step 6) and wait for the next occurrence with better evidence. Increase the rate deliberately: run under load, restrict the process to one CPU or raise the thread count, add jitter, shrink a cache, use a slower disk. A bug that appears under contention can usually be made to appear far more often on purpose. And if the failure is genuinely unreproducible, say so and switch strategy to defensive instrumentation plus a targeted review of the suspect path — which is a legitimate outcome, provided it is declared rather than quietly substituted for a diagnosis.

`references/reproduction-tactics.md` has the per-class tactics: concurrency and race amplification, environment diffing, time and timezone bugs, memory and resource leaks, network and partial failures, and what to capture when the failure has already gone. Read it when the failure will not reproduce or the rate is too low to work with.

### 3. Reduce it to the smallest failing case

A reproduction that takes eight minutes and 400 lines of input costs you every subsequent experiment. Cut it down before you start hypothesising.

Remove one thing at a time and re-check that it still fails: half the input, one service from the chain, one middleware, one configuration block, one test-suite dependency. Bisecting the input this way is usually faster than removing items one by one. Stop when every remaining element is load-bearing — each one removed makes the failure disappear.

The reduced case is worth the time twice over. It makes every experiment below cheap, and by the time you have finished cutting, the remaining elements are frequently a description of the bug. If a reduction is itself expensive, `git bisect run` on the input with a scripted predicate works the same way as bisecting history.

### 4. One falsifiable hypothesis at a time

Write the hypothesis down before running anything, in this shape: "I believe the failure is caused by X. If that is true, then Y will be observed. If Y is not observed, X is wrong."

A hypothesis that cannot be wrong is not a hypothesis. "Something is off in the cache layer" predicts nothing; "the cache is being written before the transaction commits, so a read between the two returns the new value with the row still old, and I will see the cache key populated with a timestamp earlier than the row's `updated_at`" predicts something you can look at.

| Symptom | First hypothesis to test | The observation that settles it |
| --- | --- | --- |
| Worked yesterday, no code change | An input moved: a dependency, a data shape, an upstream response, a certificate, a clock crossing a boundary | Diff the resolved dependency tree and the upstream payload against a known-good capture. Same code plus different input is the whole bug |
| Fails only in CI or only in the container | Environment difference: locale, timezone, CPU count, file ordering, case sensitivity, a missing service | Print the differing values from inside both environments and compare. Directory listing order is the classic one |
| Fails only under load or only sometimes | Concurrency: check-then-act, a shared buffer, connection reuse, a race between a write and a read | Raise parallelism until the rate rises. A rate that moves with concurrency is a race, not a flake |
| Vanishes under a debugger or with logging added | Timing-dependent, or undefined behaviour whose symptom moves | Do not chase it with a debugger. Use recorded tracing or timestamped logging that does not change the schedule |
| Fails for one user or one record only | Data-dependent: an encoding, a null, a boundary value, an unusual permission set | Bisect the record's fields to find which one carries the failure |
| Slow rather than wrong | Measure first: a profile or a trace, never a guess | Guessed hotspots are wrong more often than not, and the fix for a guessed hotspot is permanent complexity for no gain |
| Wrong answer with no error | Assumption failure somewhere upstream; the data was already wrong when it arrived | Assert the invariant at successive layers and find the first layer where it does not hold |
| Memory or handles growing | Something accumulates per request and nothing removes it | Take two heap snapshots an interval apart and diff by allocation site |

Never run two experiments at once. When you find yourself changing a timeout and a query in the same run, stop and revert one.

### 5. Bisect: in history, then in the input

Once a deterministic predicate exists, bisection converts an unbounded search into about a dozen runs.

```bash
git bisect start <known-bad-sha> <known-good-sha>
git bisect run ./run-repro.sh
git bisect reset
```

The predicate's exit code is the contract: `0` is good, `1`-`127` other than `125` is bad, and `125` means the commit cannot be tested and should be skipped rather than blamed. The failure mode that wastes a whole afternoon is a commit that does not build being scored as bad, which places the blame several commits early.

Bisection assumes determinism. A predicate that fails only 30% of the time will confidently return the wrong commit, and someone will act on it. Either raise the rate until the predicate is reliable or run the predicate enough times per commit that a pass means good — any pass means good, and only an all-fail means bad.

Two things worth remembering about the result. The commit bisect names is where the failure became observable, which is not always where the mistake is: a commit that merely started calling an already-broken function is a true bisect result and a false culprit. And bisecting the input is the same technique against a different axis — halve the dataset, the configuration, the feature flags, the request — and it works when history gives you nothing because the code never worked.

### 6. Instrument rather than guess

When the hypothesis needs evidence from inside a running system, add the observation deliberately rather than scattering print statements.

- Log values, not arrivals. `reached line 40` tells you nothing that a breakpoint would not; `order=8123 state=pending balance=0 retry=2` tells you whether the invariant holds.
- Log at the boundaries you identified in step 1: where the value enters the function, where it is transformed, where it is persisted. The first boundary where it is wrong is the answer.
- Assert the invariant rather than printing near it. An assertion that fires names the exact moment the state went bad and stops the program there, which a log line read afterwards cannot.
- Use the tools that do not perturb timing when timing is the suspect: recorded execution (`rr`), sampling profilers, tracing with span attributes, `strace`, `tcpdump`, the language's own race detector (`go test -race`, `TSan`). A debugger that changes the schedule cannot diagnose a bug that depends on the schedule.
- For anything that fails in production only, prefer a trace attribute or a structured log field over a debugger — and give the instrumentation the same review and the same removal ticket as any other change.

Remove the instrumentation in the same change that fixes the bug, or promote the useful parts to permanent structured logging on purpose. Debug prints left in a hot path are a performance regression with a note attached explaining who did it.

### 7. Prove the fix by switching the failure on and off

A fix is a hypothesis about the cause, and it gets the same treatment as any other.

1. Confirm the failure reproduces at the current commit. Rate recorded.
2. Apply the fix, one change. Confirm the failure is gone, over enough runs for the recorded rate.
3. Revert the fix. Confirm the failure comes back. This step is the one that gets skipped and it is the only one that distinguishes a fix from a coincidence.
4. Reapply. Confirm it is gone again.
5. Write a test that fails without the fix and passes with it, and check that it actually fails when you revert — a regression test that has never been seen to fail proves nothing.

Then check the altitude of the fix. A null check at the crash site stops the crash; it does not stop whatever produced the null, which will arrive again somewhere without a check. Ask where the bad state was created, whether an invariant should have been enforced further up, and whether the same mistake exists elsewhere — a bug found by a category of mistake is usually not alone. Fix at the highest layer where the fix is still correct, and if you deliberately patch lower to stop the bleeding, say so and record the real fix as follow-up.

## Anti-patterns

**Editing before reproducing.** Every change made against a guess alters the system that was failing, so even a correct diagnosis afterwards cannot be checked against the original behaviour. It also destroys the baseline, which means "it seems better now" becomes the only available verdict.

**The multi-variable fix.** Three changes, symptom gone, cause unknown. Two of the three are now permanent complexity nobody can justify removing, and the actual defect is still present in the two other places it also lives.

**Accepting the top stack frame as the cause.** The top frame is where the program noticed, typically several layers below where the state went bad. A guard added there converts a crash that told you something into a wrong answer that tells you nothing, and the real defect keeps producing bad values.

**Treating a debugger that makes it vanish as a dead end.** A heisenbug is evidence, not an obstacle: the failure depends on timing, on memory layout or on optimisation, which already narrows it to races, uninitialised memory or undefined behaviour. Switch to recorded execution, a race detector or timestamped logging instead of attaching again.

**Declaring victory on absence.** The failure stopped after a restart, a deploy, a cache flush or a quiet afternoon. Without the revert step in the procedure above, "it went away" and "I fixed it" are indistinguishable, and the difference surfaces at the next traffic peak.

**Fixing the symptom at the wrong altitude.** Rounding the total in the view because it displays 0.30000000000000004, rather than fixing the currency type, leaves every other consumer of that value wrong and adds a rule the next reader cannot explain.

**Chasing an intermittent failure with single runs.** A one-in-twenty failure needs about sixty clean runs before "it stopped" carries information. One green run after a change is noise, and treating it as a result is how a race gets closed twice and reopens.

**Debugging without a written log of what has been ruled out.** Past the first hour you re-run experiments you have already done and re-form hypotheses you have already falsified, and you cannot hand the problem to anyone else. Three lines per experiment costs nothing and is what makes a handover possible.

**Blaming the platform, the compiler or the library first.** It is occasionally right and usually a dead end that consumes a day. Rule out your own code and your own assumptions first, and if you do reach for an upstream bug, prove it with a minimal case — which is also exactly what the upstream issue will require.

**Reading code instead of running it.** Reading is how you form hypotheses; it is a poor way to test them, because the mental model that produced the bug is the one doing the reading. When a read and an observation disagree, the observation wins.

## Output format

```markdown
## Symptom
[The verbatim error or wrong behaviour, where it appeared, the version or commit, and the frequency.]

## Reproduction
[The command or sequence that fails, the environment it fails in, and the observed rate — "12 of 20 runs".]

## Minimal case
[What was removed and what is load-bearing. Omit if the original case was already small.]

## Hypotheses tested
| Hypothesis | Experiment | Result |
[One row each, including the falsified ones — they are what makes the conclusion trustworthy.]

## Cause
[One sentence naming the mechanism, then the evidence. Not the location: the reason.]

## Proof
[Failure present at baseline, absent with the fix, present again on revert, absent on reapply — with the run counts.]

## Fix
[The change, and the altitude argument: why here and not at the crash site or further up.]

## Regression test
[The test, and confirmation that it was observed to fail without the fix.]

## Still open
[Anything unexplained, other places the same mistake may exist, instrumentation left in place.]
```

## Reference files

- `references/reproduction-tactics.md` — read when the failure will not reproduce or its rate is too low to experiment against: environment diffing checklists, race amplification, time and timezone traps, resource-leak workflow, network and partial-failure simulation, and what to capture from a failure that has already gone.
- `references/tooling-by-symptom.md` — read when you know the symptom class and need the specific tool and invocation: debuggers and recorded execution, race and memory detectors, profilers, tracing, system-call and packet capture, heap snapshots, and the language-specific flags for Python, JavaScript, Go, Java, Rust and C++.
