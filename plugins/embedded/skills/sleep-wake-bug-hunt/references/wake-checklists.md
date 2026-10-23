# Wake checklists

## Contents

- Pin trace layout
- Lost wakeup sequence
- Retention audit
- Re-wake loop checks

## Pin trace layout

Use three or four spare GPIOs and a logic analyser with the debugger detached.

| Pin | Meaning |
| --- | --- |
| 0 | high while the CPU is running, low just before sleep is entered |
| 1 | pulse on every wake interrupt handler entry |
| 2 | high from wake until the clock and external chip are ready |
| 3 | pulse each time the application handles an event |

Read the trace for: a handler pulse with no matching application pulse (a flag set but not consumed), two wakes with no sleep between them (a re-wake loop), a long gap with pin 0 low and no handler pulse (a lost wakeup or a missing source).

## Lost wakeup sequence

In pseudocode, the check and the sleep are one sequence with interrupts masked:

```text
disable interrupts
if no event pending:
    wait for interrupt        # returns when an enabled interrupt becomes pending
enable interrupts
handle event
```

The wrong sequence tests the flag, enables interrupts, then sleeps: an interrupt landing after the test and before the sleep is lost until the next event.

## Retention audit

1. Name the exact low-power mode in use.
2. From the reference manual list: RAM retained (by bank), registers retained, clocks running, regulators on.
3. Write a distinct pattern into every retained region and into configuration registers of every peripheral in use.
4. Sleep, wake, compare. Anything that changed is not retained and needs re-initialising.
5. Check the always-on domain separately for reset-cause and wake-source registers.

## Re-wake loop checks

- Is the wake source level triggered and still asserted?
- Was the pending flag cleared in the peripheral, and in the interrupt controller if both are separate?
- Does an external chip hold its interrupt line until its own status register is read?
- Is a floating wake pin picking up noise? Check the pull.
- Does a timer reload value make the next compare event fall in the past?
