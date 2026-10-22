---
name: rtos-concurrency-hunt
description: "Find the cause of corruption, deadlock, starvation or lost events in RTOS firmware. Map the symptom to a class: unprotected shared data, a non-ISR-safe call from an interrupt or a stack overflow for corruption; a lock-order cycle, a mutex held across a queue wait or priority inversion through a binary semaphore for freezes; a polling high-priority task for starvation; queue overflow or notification coalescing for lost events. Turn on the RTOS's own checks first (stack overflow hook, assert, run-time stats, queue registry), then capture a trace around the failure and read task states and lock holders. Use for \"FreeRTOS task never runs\", \"deadlock after a few hours\", \"queue drops messages\", \"random memory corruption with tasks\". Not for generic method (debugging), static review (firmware-code-review), low-power wake issues (sleep-wake-bug-hunt) or decoding the fault (hard-fault-triage)."
allowed-tools: Read, Glob, Grep
---

# RTOS Concurrency Hunt

The hunt is done when the failure is tied to one named mechanism, such as a lock order, an interrupt priority or an unbounded queue, shown in a trace or a counter rather than argued from the code, and the rule that prevents the class is written down where the next change will meet it.

The usual failure is reading code for the race. Concurrency bugs depend on timing, so reading finds a dozen plausible races and no proof, and a fix that moves the timing makes the symptom vanish without removing the cause. Turn on the cheap instrumentation the kernel already offers, then capture the failure with timestamps.

## Scope

Use for: firmware running a preemptive kernel (FreeRTOS, Zephyr, ThreadX or similar) where tasks hang, starve, corrupt data or lose events, usually rarely and after hours.

Do not use for: choosing a debugging method in general, which is `debugging`; reviewing code that has no failing symptom, which is `firmware-code-review`; a bug that appears only on wake from low power, which is `sleep-wake-bug-hunt`; reading the register dump after a crash, which is `hard-fault-triage`.

## Workflow

### 1. Name the symptom class

Write down exactly what was observed and when, then pick the class. The class decides where to look first.

| Symptom | First suspects |
| --- | --- |
| Corrupted data, wrong values, crashes in unrelated code | Shared data without protection; stack overflow; a call that is not interrupt-safe made from an interrupt; heap corruption |
| System or part of it stops, other tasks still run | Lock-order cycle; mutex held while waiting on a queue or event; a task blocked forever on something nobody gives |
| A high-priority task stalls a low-priority one for long periods | Priority inversion; a task that polls instead of blocking |
| A task never runs | Starved by a higher-priority busy task; suspended; blocked on an object never signalled; created with too little stack and crashed at once |
| Events or messages missing | Queue full with a zero timeout send; notification coalescing; an interrupt that fires faster than the task drains |

### 2. Turn on the kernel's own checks

These cost little and often end the hunt at once.

- Stack overflow detection. In FreeRTOS set `configCHECK_FOR_STACK_OVERFLOW` to 2 and define `vApplicationStackOverflowHook`; log the task name and stop. Stack depth in `xTaskCreate` is counted in words, not bytes, a common source of stacks a quarter of the intended size. `uxTaskGetStackHighWaterMark` reports the minimum free stack seen; check every task under load and keep a margin. In Zephyr enable `CONFIG_STACK_SENTINEL` or hardware stack protection where the part has it, and `CONFIG_THREAD_ANALYZER` for usage.
- Assertions. Define `configASSERT` to log and halt. On Cortex-M ports the kernel asserts if an interrupt that calls a `FromISR` function is more urgent than `configMAX_SYSCALL_INTERRUPT_PRIORITY`, which is exactly the check that finds the interrupt-priority bug. It is compiled out when `configASSERT` is undefined.
- Allocation failures. Define `vApplicationMallocFailedHook` and log `xPortGetMinimumEverFreeHeapSize` to see how close the heap came to empty.
- Task states and run time. Enable the trace facility and run-time statistics (`configUSE_TRACE_FACILITY`, `configGENERATE_RUN_TIME_STATS`) and dump `vTaskList` and `vTaskGetRunTimeStats` output periodically and from a console command. A task that is always Ready and never Running is starved; a task Blocked with a long age is waiting on something.
- Queue and semaphore registry. `vQueueAddToRegistry` (with `configQUEUE_REGISTRY_SIZE`) gives names in a debugger's kernel-aware view, so you can see who is blocked on which object. Zephyr offers thread listing through its kernel shell commands and a thread monitor when enabled.

Ship the checks in a debug build first; stack overflow and assert hooks belong in the release build too if the part can afford them.

### 3. Reproduce under pressure

A bug that appears every few hours appears every few minutes if you raise the load: shorten timeouts, speed up the producer, add a task that burns CPU at a mid priority, enable time slicing, run a stress script that hits every input at once. The aim is a failure you can capture, not the failure at its natural rate. Record how long it took, since a change that moves it from minutes to hours is evidence.

### 4. Capture a trace around the failure

When the checks name nothing, record scheduling and kernel events with timestamps: SEGGER SystemView, Percepio Tracealyzer, or the Zephyr tracing subsystem. Use a ring buffer that continuously overwrites, and stop it from the failure's own detection point (an assert, a watchdog pre-warning, a missed deadline), so the buffer holds the seconds before it.

Read the trace for: which task holds each lock, what blocked the first task to stop, the priority and run order around a stall, interrupts firing at a high rate, and the last events before a corrupted value was used. Details of reading each symptom class are in `references/symptom-playbook.md`.

### 5. Confirm the mechanism

Before changing code, predict something checkable from the hypothesis: "if this is inversion, the medium task will be running while the high task waits on the mutex the low task holds". Find that in the trace or provoke it with a test that forces the order. A fix without a confirmed mechanism is a timing change.

### 6. Fix the mechanism, then leave the rule behind

- Shared data: protect it with a mutex, a critical section for a few instructions, or by making one task own it and communicate by message. Atomic access to a single word is not protection for a structure.
- Lock cycles: define one global lock order, document it beside the declarations, and acquire in that order.
- Blocking while holding a lock: do not wait on a queue, an event or a long operation inside a critical region. Copy the data out, release, then wait.
- Inversion: use a mutex with priority inheritance, not a binary semaphore, for mutual exclusion. In FreeRTOS that is `xSemaphoreCreateMutex`; in Zephyr, `k_mutex`. Neither helps if the low task is itself blocked on something else.
- Interrupts: do the minimum, signal a task through a `FromISR` call, and yield when the call reports a higher-priority task was woken. Never take a mutex in an interrupt.
- Starvation: replace polling loops with blocking waits, and give priorities by deadline, not by importance.
- Lost events: make queues count and report overflow, size them from the worst burst, and use a counting semaphore or a queue where each event matters. A task notification used as a binary flag merges events that arrive before the task runs.

### 7. Hand back

Give the symptom class, the instrumentation enabled and what it showed, the trace excerpt or counter that confirms the mechanism, the fix, and the soak result: how long the stressed build ran clean compared with how soon it used to fail. Add the rules (lock order, no blocking under lock, interrupts only signal, queues count overflow, priorities by deadline) to the project's contributing notes.

## Anti-patterns

**Adding a delay to make it go away.** The race is still there and will return when the load changes.

**Using a binary semaphore as a lock.** It has no owner and no priority inheritance, which is how inversion gets in.

**Raising priorities until it works.** It converts a freeze into starvation of something else.

**Disabling interrupts for a long region.** Latency spikes appear elsewhere and the symptom moves.

## Reference files

- `references/symptom-playbook.md` — read at steps 2 to 4: per-class checklists, what each looks like in a trace, the interrupt priority rule on Cortex-M, and a stress-test and soak plan.
