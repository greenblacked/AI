# Reading ANR traces and watchdog reports

Read this at step 3 with a trace or report open.

## Contents

- [Android ANR subjects](#android-anr-subjects)
- [Anatomy of an Android ANR trace](#anatomy-of-an-android-anr-trace)
- [Thread states](#thread-states)
- [Patterns that recur](#patterns-that-recur)
- [iOS termination codes](#ios-termination-codes)
- [Reading an iOS watchdog report](#reading-an-ios-watchdog-report)

## Android ANR subjects

The ANR's subject line says which component timed out, which tells you where to look:

| Subject | What timed out | Look at |
| --- | --- | --- |
| `Input dispatching timed out` | An input event not handled within five seconds | Whatever the main thread was doing at the time: the commonest ANR |
| `Broadcast of Intent` | A `BroadcastReceiver.onReceive` that did not return in time | Work done inside `onReceive`; move it to `goAsync()` with a bounded job, or WorkManager |
| `executing service` | A service's `onCreate`, `onStartCommand` or `onBind` that did not return in time | Service lifecycle methods doing I/O |
| `Context.startForegroundService() did not then call Service.startForeground()` | A foreground service slow to call `startForeground()` | Anything before that call in the start path |
| `ContentProvider not responding` | A provider's query or publish too slow | Provider work on the main thread, including provider `onCreate` at process start |

## Anatomy of an Android ANR trace

```text
"main" prio=5 tid=1 Blocked
  | group="main" sCount=1 ucsCount=0 flags=1 obj=0x72a8f1a8 self=0xb400007a1c0
  | sysTid=12345 nice=-10 cgrp=top-app sched=0/0 handle=0x7b8c3d24f8
  at com.example.cache.ImageCache.get(ImageCache.kt:42)
  - waiting to lock <0x0a1b2c3d> (a java.lang.Object) held by thread 23
  at com.example.feed.FeedAdapter.onBindViewHolder(FeedAdapter.kt:88)
  ...
```

- The first line gives the thread name, `tid` and state. The main thread is `tid=1`.
- `waiting to lock ... held by thread 23` names the owner. Search the trace for `tid=23`
  and read that thread: what it is doing while holding the lock is the real cause.
- Two threads each waiting on a lock the other holds is a deadlock; both stacks belong in
  the report.
- The trace file also lists every other thread in the process, and the system log around
  the ANR usually carries a CPU usage section showing whether the device itself was
  saturated.

## Thread states

| State | Meaning for the main thread |
| --- | --- |
| `Runnable` | Executing code: the main thread is busy computing — parsing, layout, a tight loop |
| `Blocked` | Waiting to enter a `synchronized` block held by another thread |
| `Waiting`, `TimedWaiting` | Parked on a latch, future, `Object.wait` or `Thread.join`, waiting for other work |
| `Native` | In native code: a binder call, file or socket I/O, JNI |
| `Sleeping` | In `Thread.sleep`, which has no place on the main thread |
| `Suspended` | Paused by the runtime, for example for garbage collection |

## Patterns that recur

| Stack shape | Cause | Fix |
| --- | --- | --- |
| `QueuedWork.waitToFinish` under an activity or service lifecycle method | Pending `SharedPreferences.apply()` writes flushed on the main thread | Fewer, smaller writes; move the data to DataStore |
| `BinderProxy.transactNative` with a system service proxy below it | A synchronous call into another process — package manager, account manager, a content provider | Cache the result, or move the call off the main thread |
| Room or SQLite frames | Database work on the main thread | A suspend DAO or a background dispatcher |
| `MessageQueue.nativePollOnce`, idle | Main thread not blocked at snapshot time | Group by cluster; check device CPU load and the ANRs around it |
| Your code `Runnable` in a loop or parser | CPU work on the main thread | Move it to a background dispatcher, or do less of it |
| SDK frames during `Application.onCreate` or a content provider's `onCreate` | Third-party initialisation on the main thread at process start | Defer or lazily initialise it |

## iOS termination codes

| Code | Meaning | What it demands |
| --- | --- | --- |
| `0x8badf00d` | Watchdog: a launch, resume, suspend or scene transition took too long | Move the work off the main thread or out of the transition |
| `0xdead10cc` | Suspended while holding a file lock or SQLite lock, typically in an app group container | Finish writes and release locks before suspension; wrap writes that may span it in a background task |
| `0xc00010ff` | Killed because the device was too hot | Find what heats it: sustained CPU, GPU, camera or radio use (`battery-drain-diagnosis` owns that hunt) |
| `0xbaadca11` | A PushKit VoIP push arrived and no call was reported to CallKit | Report a call for every VoIP push |
| `0xbaaaaaad` | Not a crash: a stackshot of the system taken on request | Do not triage as a crash |

## Reading an iOS watchdog report

- `Exception Type: EXC_CRASH (SIGKILL)` and a termination reason carrying `0x8badf00d`.
- The termination description names the transition (such as scene creation or update),
  the wall-clock time allowance it exhausted, and the CPU time used in that period. Low
  CPU time against a long wall clock means the main thread was waiting — on I/O, a lock,
  a semaphore, the network — not computing.
- The main thread's backtrace shows what it was doing when killed. Look for
  `semaphore_wait`, `dispatch_sync`, synchronous `URLSession` wrappers, Core Data or
  SQLite fetches, keychain access and file reads in launch or `sceneDidBecomeActive`
  code.
- The watchdog does not run while a debugger is attached, so reproduce from the home
  screen on the slowest supported device.
