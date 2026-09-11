# Tooling by symptom

The specific tool and invocation for each symptom class, and the language-specific flags.
Read when you know what class of bug you are in and need the command.

## Contents

- [Choosing by symptom](#choosing-by-symptom)
- [Recorded and reversible execution](#recorded-and-reversible-execution)
- [Race and memory detectors](#race-and-memory-detectors)
- [Profilers](#profilers)
- [System calls, packets and files](#system-calls-packets-and-files)
- [Tracing and logging in production](#tracing-and-logging-in-production)
- [Language-specific flags](#language-specific-flags)
- [Bisect predicates](#bisect-predicates)

## Choosing by symptom

| Symptom | Reach for | Why this one |
| --- | --- | --- |
| Deterministic crash or wrong value | A debugger with a conditional breakpoint on the bad value | You can stop exactly when the invariant breaks rather than stepping from the start |
| Fails only sometimes, vanishes when observed | Recorded execution (`rr`, or `udb` from Undo), or timestamped structured logging | A debugger changes the schedule; a recording replays the exact failing run |
| Intermittent with concurrency | The language race detector, then jitter injection | Detectors find races that did not fail, which is most of them |
| Memory grows without bound | Two heap snapshots and a diff by allocation site | The total tells you there is a leak; the diff tells you where |
| Crash with memory corruption | Address and undefined-behaviour sanitisers | They fail at the moment of corruption rather than at the later symptom |
| Hang or deadlock | A thread dump or stack dump of the live process | Free, instant, and usually conclusive about which lock is held by whom |
| Slow | A sampling profiler or a distributed trace | Guessed hotspots are wrong more often than right |
| Wrong data in, wrong data out | Boundary assertions at each layer | Finds the first layer where the invariant fails, which is the boundary the bug crossed |
| Fails only against a real dependency | Packet or system-call capture | Shows what was actually sent, which is often not what the code appears to build |

## Recorded and reversible execution

The highest-value tool for anything intermittent, because it converts a one-in-twenty
failure into a deterministic artefact you can replay and step backwards through.

```bash
rr record ./myprogram --with-args      # record until it fails
rr replay                              # deterministic replay, gdb interface
# in the replay: reverse-continue, reverse-step, watch -l addr
```

Record in a loop until the failure is captured, then debug the recording rather than the
program. `gdb` and `lldb` both support watchpoints on a memory location, which is the
fastest way to find who wrote a bad value. Java has similar ground via JFR recordings;
`.NET` via time-travel debugging on Windows.

`rr` needs Linux and access to hardware performance counters, which most containers and many
cloud instances do not expose — check with `rr record /bin/true` before planning around it,
and fall back to `udb`, to a JFR recording or to timestamped logging where it will not run.

## Race and memory detectors

```bash
go test -race ./...
go build -race && GORACE="halt_on_error=1" ./bin/app

clang -fsanitize=thread -g            # data races
clang -fsanitize=address -g           # use-after-free, overflow
clang -fsanitize=undefined -g         # signed overflow, bad shifts, misaligned access
valgrind --leak-check=full --show-leak-kinds=all ./prog
valgrind --tool=helgrind ./prog
```

Sanitisers slow execution several times over and are worth running in CI on a nightly
job rather than every push. A detector finding nothing is weak evidence; a detector
firing is strong evidence and names the two stacks involved.

Python's `faulthandler` and `threading.settrace` are thin by comparison; for Python
concurrency, prefer forcing the interleaving with explicit synchronisation in a test.

## Profilers

Sample, do not instrument, unless you need exact call counts.

```bash
go test -cpuprofile cpu.out -bench . && go tool pprof -http=: cpu.out
py-spy record -o profile.svg --pid 1234
py-spy dump --pid 1234                 # what every thread is doing right now
node --cpu-prof --cpu-prof-dir=./prof app.js
perf record -F 99 -g -- ./prog && perf script | stackcollapse-perf.pl | flamegraph.pl > out.svg
asprof -d 30 -f out.html <jvm-pid>            # async-profiler 3.x; ./profiler.sh up to v2
```

`flamegraph.pl` consumes folded stacks, so `perf script` has to pass through
`stackcollapse-perf.pl` first; piping `perf script` straight into it produces an empty or
malformed SVG.

Profile the workload that is slow, not a synthetic one, and compare a profile of the slow
case against one of the fast case. A profile in isolation shows you where time goes,
which is not the same as where the regression is.

For latency rather than CPU, the profile is the wrong tool — use a trace, which shows
waiting as well as working.

## System calls, packets and files

```bash
strace -f -T -e trace=openat,connect,read,write -p 1234     # Linux
sudo fs_usage -w -f filesys <pid>                           # macOS: file and socket activity
sample <pid> 10                                             # macOS: where the time goes
lsof -p 1234                                                # open files, sockets
tcpdump -i any -w capture.pcap 'port 5432'
mitmproxy --mode reverse:https://upstream                   # readable HTTPS, with TLS you control
ltrace ./prog                                               # library calls
```

On macOS, `dtruss` is the closest equivalent to `strace` but needs System Integrity
Protection disabled, which is rarely acceptable on a work machine; `ktrace` is a kernel
trace collector rather than a user-facing syscall tracer. Reach for `fs_usage` and `sample`
first.

`strace` answers "is it even trying?" in seconds — a missing file, a connection to the
wrong host, a permission denied that the application reported as a generic error. Use `-T`
for durations to find which call is the slow one.

## Tracing and logging in production

Add a trace attribute carrying the suspect value rather than a log line, so it is queryable
and joined to the request. Designing that — the fields, the sampling, the cardinality and
the redaction — belongs to `instrumentation`, which is where to go next.

## Language-specific flags

```bash
# Python
python -X dev -W error -X tracemalloc=10 app.py
PYTHONFAULTHANDLER=1 pytest -x --lf -p no:randomly
pytest --pdb -k test_name              # drop into a debugger at the failure

# Node / JavaScript
node --inspect-brk --stack-trace-limit=50 app.js
NODE_OPTIONS='--trace-warnings --unhandled-rejections=strict' npm test
node --heap-prof --heapsnapshot-near-heap-limit=2 app.js

# Go
GODEBUG=gctrace=1,schedtrace=1000 ./app
go test -run TestX -count=50 -race -v
kill -QUIT <pid>                       # full goroutine dump to stderr

# Java
jcmd <pid> Thread.print
jcmd <pid> GC.heap_info
java -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp

# Rust
RUST_BACKTRACE=full cargo test -- --nocapture --test-threads=1
cargo test -- --test-threads=1         # isolates ordering-dependent tests

# C / C++
gdb --args ./prog
ulimit -c unlimited                    # keep the core
```

The last two are entered at the `gdb` prompt, not at the shell, where `catch` is not a
command and `watch` is the unrelated `procps` one:

```gdb
catch throw
watch -l *0xaddr
```

`-count=50`, `-p no:randomly` and `--test-threads=1` each exist to separate two
hypotheses that are easy to confuse: a test that fails on its own versus a test that
fails only after another test ran.

## Bisect predicates

A predicate script is the contract for `git bisect run`, and getting the exit codes right
is what stops a bisect from blaming a commit that merely failed to build.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
npm ci --prefer-offline >/dev/null 2>&1 || exit 125   # untestable commit: skip, not bad
for _ in 1 2 3 4 5; do
  if node ./repro.js; then exit 0; fi                 # any pass means good
done
exit 1                                                # all attempts failed: bad
```

`0` good, `125` skip, anything else from `1` to `127` bad, and `128` or above aborts the
bisect. Run the predicate by hand on the known-good and known-bad commits before starting
— a predicate that returns bad on both ends will search happily and report nonsense.

For bisecting the input rather than history, the same shape applies with the dataset
halved at each step; keep the halves on disk so a wrong turn is cheap to undo.
