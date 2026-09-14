# Profiling the JVM and Node.js

Read this when the slow code runs on a managed runtime with a JIT. Both share the same two traps: the first seconds of any run measure compilation rather than steady state, and the easiest profiler to reach for is the one whose sampling is biased.

## Contents

- [JVM: async-profiler first](#jvm-async-profiler-first)
- [JVM: safepoint bias, and why the obvious profiler lies](#jvm-safepoint-bias-and-why-the-obvious-profiler-lies)
- [JVM: Flight Recorder when you cannot install anything](#jvm-flight-recorder-when-you-cannot-install-anything)
- [JVM: allocation, GC and locks](#jvm-allocation-gc-and-locks)
- [JVM: benchmarking needs JMH](#jvm-benchmarking-needs-jmh)
- [Node: the built-in profilers](#node-the-built-in-profilers)
- [Node: the event loop is the whole story](#node-the-event-loop-is-the-whole-story)
- [Node: memory and allocation](#node-memory-and-allocation)

## JVM: async-profiler first

async-profiler attaches to a running JVM and samples with low overhead. It is the default answer for a JVM service.

```bash
asprof -d 30 -e cpu -f /tmp/flame.html 1234      # 30 seconds of CPU, flame graph out
asprof -d 30 -e wall -t -f /tmp/wall.html 1234   # wall clock, per thread, for a latency question
asprof -d 30 -e alloc -f /tmp/alloc.html 1234    # allocation by stack
asprof -d 30 -e lock -f /tmp/lock.html 1234      # contended monitors
```

Releases before 3.0 ship the same tool as `profiler.sh` with identical arguments. Attaching needs the same user as the JVM process, or root with matching namespaces in a container.

Pick the event to match the question. `cpu` answers "what is burning the core"; `wall` with `-t` answers "where did this request's two seconds go", and the two disagree whenever threads block, which is most of the time in a service that calls anything.

## JVM: safepoint bias, and why the obvious profiler lies

Profilers built on `ThreadMXBean.getStackTrace` or JVMTI's `GetAllStackTraces` — which includes the sampling mode of several IDE and GUI profilers — can only collect a stack when the JVM reaches a safepoint. Safepoints are not evenly distributed through the code: a tight counted loop may contain none at all, so its frames are systematically under-sampled and the frames near safepoint polls are over-sampled. The result is a profile that is stable, plausible, repeatable and wrong.

async-profiler uses `AsyncGetCallTrace` from a signal handler and does not wait for a safepoint, which is the reason to prefer it. If a GUI profiler and async-profiler disagree about a hot method, the GUI profiler is the one to doubt.

## JVM: Flight Recorder when you cannot install anything

JFR ships with the JDK and can be started on a running process, which makes it the tool available in environments where adding a binary is a change-management exercise.

```bash
jcmd 1234 JFR.start name=prof settings=profile duration=60s filename=/tmp/prof.jfr
jcmd 1234 JFR.dump name=prof filename=/tmp/prof-partial.jfr
```

Or from the start of a run with `-XX:StartFlightRecording=duration=60s,settings=profile,filename=/tmp/prof.jfr`. Open the file in JDK Mission Control. Its execution sampling is coarser than async-profiler's, so treat method-level attribution as indicative; where JFR is unmatched is everything around the profile — GC pauses with causes, allocation rates, thread parks, I/O events and JIT activity in one timeline, which is often what actually names the problem.

## JVM: allocation, GC and locks

Enable GC logging before theorising about pauses: `-Xlog:gc*:file=/tmp/gc.log:time,uptime,level,tags` on JDK 9 and later. Read allocation rate and pause distribution. A young-collection pause of a few milliseconds every second is healthy; the same pause every 50ms means the code is producing garbage faster than it should.

An allocation profile names the stack creating the objects, which is the actual fix. Escape analysis can remove some allocations entirely, so an allocation that appears in source and not in the profile is not a mystery.

For lock contention, `-e lock` reports contended monitors by stack. The typical finding is a synchronised block held across an I/O call, which serialises the whole service behind one remote round trip.

## JVM: benchmarking needs JMH

A hand-written loop with `System.nanoTime` around it measures the interpreter, then C1, then C2, and often measures nothing at all because the JIT removed work whose result is unused. JMH exists for this: forked JVMs per trial, warm-up iterations before measurement, `Blackhole` to consume results, and state objects that stop constant folding.

Two rules beyond using it. Fork at least once per trial, because a JVM that has already run a different implementation carries profile pollution — the compiler has seen a megamorphic call site and optimises worse. And report the distribution across forks; a single fork can be systematically fast for reasons that do not survive a restart.

## Node: the built-in profilers

Node ships the profilers, and reaching for a third-party wrapper first is usually unnecessary.

```bash
node --cpu-prof --cpu-prof-dir=./prof app.js     # writes a .cpuprofile on clean exit
node --prof app.js                                # V8 tick log
node --prof-process isolate-0x102801000-v8.log > processed.txt
node --inspect app.js                             # attach DevTools and profile a live process
```

Open a `.cpuprofile` in Chrome DevTools or VS Code and read the bottom-up view first, which is the self-time ordering. `--cpu-prof` writes its file when the process exits cleanly, so a service killed with SIGKILL produces nothing; arrange a clean shutdown before profiling one.

For `perf` on Linux to resolve JIT frames, start Node with `--perf-basic-prof`, which writes the symbol map `perf` needs. Without it the JavaScript frames appear as addresses.

## Node: the event loop is the whole story

One thread runs the JavaScript. Any synchronous work on it delays every pending request, so the characteristic Node performance bug is not a slow function but a blocking one: `JSON.parse` on a several-megabyte body, a synchronous `fs` call, a synchronous crypto call, a regular expression with catastrophic backtracking, a large loop over an array.

Measure the loop directly rather than inferring it:

```javascript
const { monitorEventLoopDelay } = require("node:perf_hooks");

const histogram = monitorEventLoopDelay({ resolution: 10 });
histogram.enable();
setInterval(() => console.log(histogram.mean / 1e6, histogram.percentile(99) / 1e6), 5000);
```

A p99 delay in the tens of milliseconds means something is blocking, and that is the finding; the CPU profile then names it. The second place to look is the libuv thread pool, which defaults to four threads and serves file system work, DNS lookups through `dns.lookup` and several crypto calls. Saturating it looks exactly like a slow application while the CPU sits idle; `UV_THREADPOOL_SIZE` raises it, though the better fix is usually to stop doing that work per request.

## Node: memory and allocation

`node --heap-prof app.js` writes a sampling allocation profile that attributes bytes to the stack that allocated them, readable in the same DevTools memory panel. `--trace-gc` prints each collection with its cause, which is enough to tell a GC-pressure problem from a slow-function problem.

Growth that never comes back down is a retention question rather than a profiling one: take two heap snapshots under load, compare, and find what still holds the reference. That belongs to `debugging`.
