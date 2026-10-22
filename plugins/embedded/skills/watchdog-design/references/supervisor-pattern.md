# Supervisor pattern

## Contents

- Structure
- Pausing around a long operation
- Reset record
- Choosing N and M

## Structure

One supervisor task or loop owns the watchdog peripheral. Each monitored task has a slot that holds a progress token. A task advances its token from inside its loop, after the useful work, not at the top. Every supervisor period:

1. For each monitored task, compare its token with the last seen value.
2. If every token moved, remember the new values and feed the hardware.
3. If any did not move, do not feed; write the name of the stalled task to the retained record so the reset cause survives.

The supervisor period is shorter than the timeout by at least the margin chosen, so one missed period does not itself cause a reset. A task that legitimately blocks for long periods reports from a timer-driven helper only if the helper checks the task is making progress, never unconditionally.

## Pausing around a long operation

Prefer lengthening the timeout for the duration of the operation over disabling the watchdog. Where the part allows neither, split the operation into steps short enough to fit in the window and report between them. Put the pause and its release in one function with a single exit, so an error return cannot leave the watchdog paused.

## Reset record

| Field | Why |
| --- | --- |
| reset cause | tell a watchdog reset from power loss or a fault |
| stalled task | the task that did not report |
| last tokens | state at the moment of the last feed |
| uptime before reset | how long the device ran |
| reset count and window start | the safe-mode decision |

Keep it in retained memory and clear it after upload.

## Choosing N and M

Choose M long enough that a transient fault does not trip it and short enough that a boot loop does. Three resets in ten minutes is a starting point to adjust for the device's boot time: if a boot takes a minute, three resets in ten is already a loop. Record the choice and the reason.
