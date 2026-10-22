# Symptom playbook

## Contents

- Corruption
- Freeze or deadlock
- Priority inversion
- Starvation
- Lost events
- Interrupt priority rule on Cortex-M
- Stress and soak plan

## Corruption

Order of checks, cheapest first.

1. Stack high-water marks for every task and the interrupt stack, under load. A task with almost no free stack is the first suspect, since an overflow writes into whatever is next in memory, usually another task's stack or the heap.
2. Heap: allocation failures logged, minimum ever free logged, and an allocator that checks block headers if one is available. Corruption that lands in the allocator's own structures shows up later in an unrelated allocation.
3. Shared data: list every variable written by more than one task or by a task and an interrupt. For each, name the protection. Multi-word updates, read-modify-write on a flag word shared between tasks, and a pointer swapped without the matching length are the usual holes.
4. Interrupt calls: any kernel call from an interrupt must be the `FromISR` form (or the Zephyr interrupt-safe form), and the interrupt must be at an allowed priority. The wrong form corrupts the kernel's lists silently.
5. DMA and caches: a buffer written by DMA and read by a task needs cache maintenance on parts with a data cache, and must not live on a stack that is reused.

In a trace, look for the last write to the corrupted location if the debugger supports a data watchpoint: set one on the address and read which task and interrupt hit it.

## Freeze or deadlock

1. Stop the system in the debugger or at the assert hook, and list every task with its state and what it is blocked on.
2. For each blocked-on mutex, find the holder. Build the graph: task A waits for a lock held by B, B waits for one held by A. A cycle is a lock-order bug.
3. If there is no cycle, find the object that has no giver. A queue receive with an infinite timeout on a queue whose sender crashed, or a semaphore whose giver is an interrupt that is masked, looks identical to a deadlock.
4. A task that holds a mutex while waiting on a queue turns a slow producer into a freeze for every other user of the mutex. Search for any blocking call between a take and the matching give.
5. Check the watchdog: if feeding it happens in the idle hook, a starved idle task resets the unit and hides the freeze. Record which task last fed it.

## Priority inversion

Pattern: low-priority task L takes a lock, high-priority task H blocks on it, medium-priority task M becomes ready and runs, so L cannot run to release the lock and H waits as long as M runs.

In a trace: H blocked on the lock, M running continuously, L ready but not running. Fixes: a mutex type with priority inheritance, shorter critical sections, or removing the shared resource. A binary semaphore has no owner, so the kernel cannot boost anyone.

## Starvation

- A task that never blocks (a loop reading a flag, or a delay of zero ticks) starves every task of lower or, without time slicing, equal priority.
- Look at run-time statistics: a task using nearly all the CPU time, and others with none.
- With time slicing enabled equal-priority tasks share; without, a task runs until it blocks.
- An interrupt storm (a noisy input, a missed clear of the interrupt flag) looks like starvation of the whole task level. Count interrupts per second.

## Lost events

- A send with a zero timeout to a full queue returns an error that is easy to ignore. Check every return value and count failures.
- A notification given twice before the task runs is one wake-up when used as a flag. Use the counting form, or a queue, where each event matters.
- Event bits set and cleared by different tasks can clear a bit another task has not yet seen.
- A producer in an interrupt faster than the consumer eventually fills any queue; compute the worst burst and the drain rate, and decide whether to drop, block upstream or slow the producer.

## Interrupt priority rule on Cortex-M

On Cortex-M, a smaller number means a more urgent interrupt. The kernel masks interrupts at and below a configured threshold (in FreeRTOS, `configMAX_SYSCALL_INTERRUPT_PRIORITY`) during its critical sections. An interrupt that calls a `FromISR` function must be at that priority or less urgent. An interrupt more urgent than the threshold is never masked by the kernel, so it must not call any kernel function. Check the number of priority bits the part implements, since priorities are stored in the top bits of the field and a value written without the shift can land on the wrong level. Set the priority grouping so all bits are preemption priority, as the port requires.

## Stress and soak plan

1. Establish the failing build and the time to failure on the bench, with the same inputs.
2. Add load: faster inputs, a CPU-burning task at a mid priority, shorter timeouts, and every communication channel active at once.
3. Run the build with all checks on and record the time to first failure over several runs; use the median.
4. After the fix, run the same stressed build for at least ten times the median time to failure with no stack, assert or watchdog event, and keep the log.
5. Run the unstressed release build overnight as a second check, since the fix may change timing that other bugs depend on.
