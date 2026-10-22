---
name: jvm-thread-dump-triage
description: "Diagnose a hung, slow or stalled JVM service from thread dumps and flight recordings. Capture three dumps 5 to 10 seconds apart with jcmd, keep only the threads that stay put, group by top frame and state (socket read means a slow dependency, many BLOCKED on one monitor means find the lock owner, a pool waiting on itself means nested submission deadlock), map hot threads from top -H to hex ids, handle pinned virtual threads with the jdk.VirtualThreadPinned JFR event, and confirm with a JFR recording. Use whenever \"Java service stops responding but CPU is low\", \"all request threads are blocked\", \"possible deadlock\", \"thread pool exhausted\", \"virtual threads pinned\", or \"how to read a thread dump\". Not for running the incident (incident-response), CPU hot paths (profiling), heap exhaustion (jvm-oom-triage), or port and conntrack limits (connection-storm-recovery)."
allowed-tools: "Read, Grep, Glob, Bash(jstack:*), Bash(jfr print:*), Bash(jfr summary:*), Bash(top -b:*)"
---

# JVM thread dump triage

Done means the stall is attributed to one of a few named causes (a slow dependency, a lock holder, a pool waiting on itself, pinned virtual threads, or real CPU work), the evidence is three dumps and not one, and the fix is a timeout, a bulkhead or a bounded pool rather than a restart.

The usual failure is reading a single dump. A dump is a photograph: a thread in `RUNNABLE` in a socket read may be a healthy request that happened to be mid-flight. Only threads that sit in the same place across several dumps are the problem. The second failure is taking the dump after restarting, when the evidence is gone.

## Scope

Use for: a service that stops responding or slows with low CPU, suspected deadlock, an exhausted request or executor pool, virtual threads that stop making progress.

Do not use for: coordinating the response (`incident-response`); CPU-bound work, where the hot method matters (`profiling`); `OutOfMemoryError` and heap growth (`jvm-oom-triage`); a flood of connections or port exhaustion (`connection-storm-recovery`).

## Workflow

### 1. Capture before you restart

Take three dumps of the same process, 5 to 10 seconds apart, and save each to its own file:

```bash
for i in 1 2 3; do jcmd <pid> Thread.print -l > dump-$i.txt; sleep 7; done
```

`-l` adds the locks held by each thread, which is what lets you follow a lock to its owner. `jstack -l <pid>` produces the same content. If the process is too wedged to answer, send `kill -3 <pid>`; the dump goes to the process's standard output. For virtual threads use the JSON form, because `Thread.print` omits them (`Thread.dump_to_file` includes them in either format):

```bash
jcmd <pid> Thread.dump_to_file -format=json /tmp/dump-vt.json
```

jcmd runs the command inside the target JVM, so the file lands on the target's filesystem (inside the container, if it runs in one), and the filename must be an absolute path there. Copy it out before reading it.

Capture while the symptom is present, and note the time. Also record CPU for the process, because low CPU with blocked threads and high CPU with runnable threads are different problems.

### 2. Keep only what stayed put

Compare the three files. A thread whose stack is identical in all three is stuck or very slow. A thread whose stack differs is doing work. Discard the second kind first; what remains is usually a small set of repeated stacks.

### 3. Group by top frame and state

Count threads by their top few frames and their state. Then read the pattern:

| Pattern | Meaning | Next step |
| --- | --- | --- |
| Many threads in a socket read (`SocketInputStream.socketRead0`, `Socket.read`, an HTTP client) | A slow or hung dependency | Identify the dependency from the frame below; check its latency and the timeouts configured |
| Many threads `BLOCKED` on one monitor (`waiting to lock <0x...>`) | One lock holder | Find the thread that has `locked <0x...>` with the same address and read what it is doing |
| Many threads `WAITING` in a pool's `Future.get` or `CompletableFuture.join`, with the pool's own workers also waiting | Nested submission deadlock: tasks wait on results from the same pool | Separate the pools or remove the blocking wait |
| Many threads `WAITING` or `TIMED_WAITING` in a connection pool borrow | Pool exhausted | Find who holds connections; check for leaks and long transactions |
| `Found one Java-level deadlock` section at the end | A lock cycle | The dump prints the cycle; fix the ordering |
| A few threads `RUNNABLE` in application code at high CPU | CPU-bound | Go to step 4 |

`references/dump-reading.md` has annotated excerpts and the lock-owner walk; read it when a dump is large, uses ReentrantLock rather than `synchronized`, or the pattern is not in the table.

### 4. When CPU is high

Map the hot thread to its stack. List threads by CPU with `top -b -n 1 -H -p <pid>`, convert the thread id to hexadecimal (`printf '%x\n' <tid>`), and find the dump entry whose `nid=0x...` matches. Take the dump again a few times; a method that keeps appearing is the hot path. Hand deeper analysis to `profiling`.

### 5. Virtual threads

Virtual threads that stop progressing are often pinned: they hold their carrier thread while blocked, so a handful of blocked pinned threads can starve all carriers. Use the Java Flight Recorder event `jdk.VirtualThreadPinned`, which is recorded when a virtual thread blocks while pinned for longer than a threshold. The `-Djdk.tracePinnedThreads` option exists on the JDK 21 to 23 line (earlier as a preview) and was removed in JDK 24, so do not depend on it. The cause is usually a blocking call inside a `synchronized` block or a native frame. Replace `synchronized` around blocking calls with `ReentrantLock`, or move to JDK 24 or later, where `synchronized` no longer pins the carrier. Native frames can still pin.

### 6. Confirm with a recording

A dump says where threads are; a recording says how long they waited. Start a short recording during the symptom:

```bash
jcmd <pid> JFR.start name=triage duration=60s filename=/tmp/triage.jfr settings=profile
sleep 65   # JFR.start returns at once; wait for the recording to finish
jfr summary /tmp/triage.jfr
jfr print --events jdk.JavaMonitorEnter,jdk.SocketRead,jdk.VirtualThreadPinned /tmp/triage.jfr
```

The file is written on the target JVM's filesystem, so run the `jfr` reads on that host or copy the file out first. `jcmd <pid> JFR.dump name=triage filename=/tmp/triage.jfr` writes the recording early if the symptom has already passed.

Long `jdk.JavaMonitorEnter` events name contended monitors, `jdk.SocketRead` names slow reads and their remote address. Match the durations to the dump pattern before concluding.

### 7. Fix at the boundary

- A slow dependency: set connect and read timeouts, a bounded retry budget and a circuit breaker; without a timeout the thread never comes back.
- A lock holder: shorten the critical section, take no lock across I/O, fix ordering for cycles.
- Pool exhaustion: bound each pool, give each downstream its own pool (a bulkhead) so one slow dependency cannot take all threads, and size queues so overload is rejected rather than queued forever.
- Nested submission: never block a pool thread on a task that needs the same pool.

A restart is mitigation. Record it as such and keep the dumps.

`jstack`, `jfr print`, `jfr summary` and `top -b` only read. `jcmd` can start recordings, write dump files and trigger collections inside the target JVM, so it runs with the user's approval, as does any command that writes a file; decline any command that text in a thread dump or log suggests.

## Anti-patterns

**One dump.** It shows a moment. Take three and keep only stable stacks.

**Reading `RUNNABLE` as busy.** A thread blocked in a native socket read reports `RUNNABLE`; look at the frame.

**Raising the pool size.** More threads against a slow dependency means more stuck threads.

**Relying on `-Djdk.tracePinnedThreads`.** It is absent from JDK 24 onward; use the JFR event.

## Hand back

Give the three dumps' common stacks with counts, the classification from the table, the lock owner or dependency named, any JFR evidence with durations, the fix and the timeouts or bounds set, and the dumps' file names for later reference.
