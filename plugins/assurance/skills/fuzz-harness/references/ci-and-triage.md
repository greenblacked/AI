# CI and triage

Read this at steps 7 and 8: what each kind of crash report means and where it goes, how to deduplicate, how each engine replays committed inputs, and how to lay out the pull request and scheduled jobs.

## Contents

- [Classifying a finding](#classifying-a-finding)
- [Deduplicating by stack](#deduplicating-by-stack)
- [Handling a memory-safety finding](#handling-a-memory-safety-finding)
- [Regression replay per engine](#regression-replay-per-engine)
- [Job layout](#job-layout)
- [Corpus storage](#corpus-storage)
- [Ticket template](#ticket-template)

## Classifying a finding

| What the report says | Class | Where it goes |
| --- | --- | --- |
| AddressSanitizer `heap-buffer-overflow`, `stack-buffer-overflow` or `global-buffer-overflow`, on a WRITE | Memory corruption | Security process, private. The most serious class: a controlled write is how a parser bug becomes code execution. |
| The same, on a READ | Out-of-bounds read | Security process, private. Can disclose adjacent memory. |
| `heap-use-after-free`, `double-free`, `attempting free on address which was not malloc()-ed` | Memory corruption | Security process, private. |
| `SEGV on unknown address` near zero | Null dereference | Normal tracker as a denial-of-service bug, unless the address varies with the input, in which case treat it as corruption. |
| MemorySanitizer `use-of-uninitialized-value` | Uninitialised read | Security process if the value can reach output; otherwise normal tracker. |
| UndefinedBehaviorSanitizer `runtime error:` (signed overflow, invalid shift, misaligned load, out-of-range enum) | Undefined behaviour | Normal tracker, fixed rather than waived: the compiler is entitled to optimise on the assumption it never happens, so harmless today can be exploitable after an upgrade. |
| libFuzzer `timeout-` artefact | Hang or super-linear algorithm | Normal tracker as denial of service. Check for quadratic behaviour on nested or repeated structures. |
| libFuzzer `oom-` artefact, or `out-of-memory (malloc(N))` | Allocation driven by an input length field | Normal tracker as denial of service. Cap the length against the remaining input before allocating. |
| LeakSanitizer `detected memory leaks`, `leak-` artefact | Leak on an error path | Normal tracker. In a long-running server a per-request leak is a slow denial of service. |
| Go `panic: runtime error: index out of range` or `nil pointer dereference` | Unhandled malformed input | Normal tracker as denial of service. |
| Python exception other than the documented one, or `RecursionError` | Unhandled malformed input | Normal tracker. Bound nesting depth in the parser rather than raising the recursion limit. |
| Java `StackOverflowError`, `OutOfMemoryError`, or an undeclared `RuntimeException` | Unhandled malformed input | Normal tracker; Jazzer detector findings follow the security process. |
| The harness's own round-trip or differential check failed | Correctness | Normal tracker, with the input. Often the most valuable class: silent data corruption with no crash. |

Classify from the symbolised stack and the sanitiser's own wording, not from the file name. A `crash-` artefact can be any of the above.

## Deduplicating by stack

1. Make sure reports are symbolised: `llvm-symbolizer` on `PATH`, or `ASAN_SYMBOLIZER_PATH` pointing at it. An unsymbolised stack is a list of addresses that differ between builds.
2. Take the frames from the top, skipping sanitiser runtime, allocator and libFuzzer frames, and stop before the harness function.
3. Key the crash on the crash type plus the first three of those frames. ClusterFuzz's default crash state is the top three frames; fewer merges distinct bugs that share a helper, more splits one bug reached through different callers.
4. Keep one minimised input per key, and count the duplicates on the ticket. A key that keeps recurring after its fix was merged means the fix covered one caller, not the cause.

## Handling a memory-safety finding

A memory-safety finding in code that reads untrusted input is a vulnerability in your own product until shown otherwise. Treat it the way your security policy treats any other reported vulnerability:

- Open the ticket in a private tracker, or with restricted visibility, and reference it from public places by number only.
- Do not attach the crashing input or the full sanitiser output to a public issue, pull request description or chat channel until the fix has shipped to the people who run the code.
- Write the fix's commit message about the defect ("check the declared length against the remaining buffer before copying"), not about how to trigger it.
- Commit the regression input with the fix, or immediately after release where the repository is public and the disclosure policy asks for a delay.
- If other people ship or run the affected code, follow the coordinated disclosure process for an advisory and, where applicable, an identifier.
- Do not develop the crash into a working exploit to prove severity. The class and the reachable entry point are enough to rank it.

## Regression replay per engine

Every committed crash input runs on every build, in the ordinary test job, in seconds.

| Engine | Where committed inputs live | How they replay |
| --- | --- | --- |
| libFuzzer | A directory per harness, such as `fuzz/regressions/parse_message/` | `./parse_message_fuzzer fuzz/regressions/parse_message/*` runs each file once and exits non-zero on a crash. For builds without libFuzzer, link the harness against a small driver whose `main` reads each file and calls `LLVMFuzzerTestOneInput`. |
| cargo-fuzz | A directory per target | A `#[test]` in the crate that reads every file in the directory and calls the same entry point, so `cargo test` replays them on stable Rust. |
| Go | `testdata/fuzz/FuzzParse/` | Automatic: plain `go test` runs every file there as a sub-test. |
| Atheris | A directory per harness | A pytest test that calls `TestOneInput` on every file, or the harness script run with the files as arguments. |
| Jazzer | The inputs directory beside the test class in test resources | Automatic: the `@FuzzTest` method runs them as an ordinary JUnit test when `JAZZER_FUZZ` is unset. |

Name each file after its ticket (`issue-4127-length-overflow`), so the next person to see it fail knows it is load-bearing.

## Job layout

| Job | Trigger | What it does | Budget |
| --- | --- | --- | --- |
| Build | Every pull request | Builds every harness with sanitisers, so a refactor cannot silently break one | Build time only |
| Replay | Every pull request | Runs every committed regression input through the ordinary test runner | Seconds |
| Short fuzz | Pull requests touching parsing code | Fuzzes the affected harnesses from the stored corpus; a new unique crash fails the check | A few minutes per harness |
| Long fuzz | Nightly | Fuzzes every harness, merges new corpus entries back, deduplicates against known crashes, files tickets | Hours per harness, split across cores |
| Prune | Weekly | Minimises each stored corpus with the engine's merge | Minutes |
| Coverage | Weekly | Builds with coverage instrumentation, replays the corpus, publishes the report | Minutes |

ClusterFuzzLite provides this layout for libFuzzer-compatible harnesses as GitHub Actions or other CI steps, with `code-change`, `batch`, `prune` and `coverage` modes. Pin its actions to a full commit SHA like any other third-party action. OSS-Fuzz runs the long half for accepted open-source projects and reports through its own tracker.

Run every fuzz job on a runner with no deployment credentials, no secrets in the environment, and no network access beyond fetching and storing the corpus. Keep crash artefacts on short retention with access limited to the people who triage them.

## Corpus storage

- **Seeds** (curated, small, reviewed): in the repository beside the harness.
- **Regression inputs** (one per fixed bug): in the repository, replayed by every build.
- **Grown corpus** (thousands of files, regenerated constantly): in CI storage or a bucket keyed by harness name, restored at the start of each fuzz job and saved at the end of the scheduled job only.

Pull request jobs read the stored corpus and never write it. A pull request from a fork that could write the shared corpus could plant inputs that steer or slow every later run.

## Ticket template

```markdown
## Harness
[Harness name, engine, commit fuzzed.]

## Class
[From the classification table; security process or normal tracker.]

## Stack key
[Crash type and the top three frames.]

## Reproduction
[Command that replays the minimised input; input attached here only if the tracker is private.]

## Duplicates
[Count of crash files folded into this key.]

## Fix and regression
[Fix commit, regression input path, and confirmation the replay job passes.]
```
