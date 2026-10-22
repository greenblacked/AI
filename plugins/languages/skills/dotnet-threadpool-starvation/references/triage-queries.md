# Triage queries and stack shapes

Read this when the stacks from `dotnet-stack report` do not group cleanly, or when working inside a dump.

## Contents

- Counters to read together
- Stack shapes and what they mean
- Dump session sequence
- Reading the result

## Counters to read together

The names below are the EventCounter names. On .NET 9 and later the same data may also appear under meter names such as `dotnet.thread_pool.queue.length`; check which your tooling shows.

| Counter (System.Runtime) | Starvation signature | Other signature |
| --- | --- | --- |
| `threadpool-queue-length` | Rises and stays high | Near zero: not a pool problem |
| `threadpool-thread-count` | Climbs by one or two per second, never jumps | Flat and high: threads are busy, not starved |
| CPU usage | Low for the request rate | Saturated: use `profiling` |
| `monitor-lock-contention-count` | Low or flat | Rising fast: a lock, not the pool |
| `threadpool-completed-items-count` | Rate falls while queue grows | Rate steady: pool is keeping up |

## Stack shapes and what they mean

| Many threads show | Meaning | Fix direction |
| --- | --- | --- |
| `Task.Wait`, `Task.get_Result` or `TaskAwaiter.GetResult` under an application frame | Sync-over-async at that frame | Make the caller async |
| `ManualResetEventSlim.Wait` or `SemaphoreSlim.Wait` (synchronous) | A synchronous wait on a signal another task sets | Use `WaitAsync` and await it |
| A synchronous socket, file or database read | Blocking I/O inside an async method | Use the async overload |
| `Monitor.Enter` on one object | Lock convoy, not starvation | Shorten the critical section; no awaits inside `lock` |
| Few threads, all busy in application code | CPU-bound | `profiling` |

## Dump session sequence

```bash
dotnet-dump collect --process-id <pid>
dotnet-dump analyze <dumpfile>
```

Then, at the prompt:

1. `threads` lists managed threads and their ids.
2. `clrstack -all` prints every managed stack; save the output and group identical stacks.
3. `dumpasync` lists async state machines that are pending; a large count waiting on one task names the thing everyone is queued behind.
4. `syncblk` shows monitors that are held and which thread holds them, when a lock is suspected.

Collect two dumps a few seconds apart when you can; only frames present in both are stuck.

## Reading the result

Write one line per distinct blocked stack: count of threads, the top application frame, the blocking call. The stack with the largest count and an application frame directly above a wait is where the first change goes. Fix that site, retest, and repeat: removing one blocker often reveals the next, because the pool was hiding several behind the largest.
