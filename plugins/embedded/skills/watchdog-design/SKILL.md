---
name: watchdog-design
description: "Design or fix a watchdog so it recovers real hangs without masking them: feed it from exactly one place, only after every monitored task has checked in with a progress token inside the window, never from an ISR or a lone idle hook, set the timeout from measured worst-case loop time with a 2x to 3x margin and longer than the slowest legitimate blocking operation, use a window watchdog when running too fast is also a fault, confirm it cannot be disabled in the release build, and on reset persist cause and last check-in to enter safe mode after repeated resets. Use for \"device hangs in the field\", \"watchdog reset loop\", \"where should I kick the watchdog\", \"it resets during flash erase\". Not for finding the deadlock (debugging), wake failures (sleep-wake-bug-hunt) or revert mechanics (ota-update-safety)."
allowed-tools: Read, Glob, Grep
---

# Watchdog Design

A watchdog is done when it resets the device from a real hang in every task, does not reset it from legitimate slow work, and leaves a record of why it fired.

The usual failure is a watchdog that proves a timer is alive. Feeding it from a timer interrupt or an idle hook keeps it quiet while the application deadlocks, so the device hangs in the field with the watchdog still being fed. The opposite failure is a timeout shorter than a flash erase, which turns normal work into a reset loop. Both come from not deciding what the watchdog is meant to prove.

## Scope

Use for: choosing where to feed the watchdog, the timeout, the window, the reset reaction, and the test that proves it works.

Do not use for: working out why a task deadlocked, which is `debugging`; a device that will not wake from sleep, which is `sleep-wake-bug-hunt`; reverting an update after resets, whose mechanics are in `ota-update-safety`; decoding a fault that triggered a reset, which is `hard-fault-triage`.

## Workflow

### 1. Decide what it must prove

List the tasks and conditions that mean the device is doing its job: the control loop ran, the sensor was read, the communication task serviced its queue. The watchdog must be fed only when all of these hold. Anything weaker, such as the scheduler is running, lets the hang you care about pass.

### 2. Feed from exactly one place

Create one supervisor that owns the watchdog. Each monitored task reports a progress token (a counter it advances, or a bit it sets) from the point in its loop where it has done real work. The supervisor checks that every task has reported inside the window, clears the tokens and only then feeds the hardware. Never feed from an interrupt service routine, which keeps running while tasks are stuck, and never from a lone idle hook, which runs whenever nothing else does. Read `references/supervisor-pattern.md` for the structure.

### 3. Set the timeout from measurement

Measure the worst-case time of the monitored loop under load, including the slowest path, then set the timeout to two to three times that. The timeout must also be longer than the slowest legitimate blocking operation, such as a flash erase or an update step. If it cannot be, pause or lengthen the watchdog deliberately around that operation, with the pause confined to one place and ended on every exit path including errors.

### 4. Choose the type

A window watchdog also resets when it is fed too early, which catches a runaway loop that feeds as fast as it can. Use it when running too fast is a fault. Prefer a watchdog on an independent low-speed clock so a failed main oscillator does not stop it. Where the part has both an independent and a windowed one, use the independent one for the last line of defence.

### 5. Make sure it is really on

Confirm in the release build, and in the option bytes or fuses, that the watchdog is enabled at start and cannot be disabled by software or by a debug connection that leaves it paused. A watchdog that is on in the debug build and off in the release build is the commonest field gap. Read back the configuration at boot and report it.

### 6. Record the reset and react

At start-up read the reset-cause register and store: that a watchdog fired, which tasks had checked in, and the uptime. After N watchdog resets within M minutes, stop restarting the failing path: enter a safe mode that keeps communications and reporting alive, or revert the update if the resets began after one. A device that resets forever on the same fault is worse than one that reports it and waits.

### 7. Test by hanging each task

For each monitored task, hang it on purpose (an infinite loop, a blocked wait) and check the device resets within the timeout and records which task failed. Also run the slow paths, the flash erase and the update, and confirm they do not reset. Test the reset loop reaction by forcing repeated resets. A watchdog that was never seen to fire is untested.

## Output format

```markdown
## Proof obligation
[Tasks and conditions that must hold for a feed.]

## Supervisor
[Where the single feed is, tokens, checks.]

## Timing
[Measured worst case, margin, slowest blocking operation, pauses.]

## Configuration
[Type, clock, window, enabled in release, option bytes.]

## Reset reaction
[Recorded state, threshold N in M minutes, safe mode or revert.]

## Test results
[Each task hung, slow paths run, outcome.]
```

## Anti-patterns

**Feeding from a timer interrupt.** The watchdog stays quiet through a deadlock.

**Feeding in several places.** One healthy task hides a dead one.

**A timeout below a flash erase.** A normal operation causes a reset loop.

**Disabled in release.** The debug build passes every test.

**Resetting forever.** A repeated fault needs a safe mode, not another try.

## Reference files

- `references/supervisor-pattern.md` — read at steps 2, 3 and 6: the supervisor structure, how to pause around a long operation, and the reset record layout.
