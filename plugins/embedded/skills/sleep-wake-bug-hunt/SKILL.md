---
name: sleep-wake-bug-hunt
description: "Fix devices that miss wakeups, hang on wake, or lose state after deep sleep: classify first as a lost wakeup (event lands between the flag check and sleep; check with interrupts masked and sleep on WFI), a wake-source fault (wrong edge or level, flag not cleared, instant re-wake loop) or a retention fault (RAM, registers and clocks that did not survive that mode), allow oscillator, PLL and external chip start-up times, reproduce with the debugger detached using spare GPIOs and a logic analyser, and record reset reason and wake source first after wake. Use for \"it sometimes never wakes up\", \"works until I unplug the debugger\", \"peripheral dead after standby\", \"wakes and immediately sleeps again\". Not for sleep current (sleep-current-hunt), generic method (debugging), watchdog resets (watchdog-design) or hard faults (hard-fault-triage)."
allowed-tools: Read, Glob, Grep
---

# Sleep-Wake Bug Hunt

Done means the failure is classified as a lost wakeup, a wake-source fault or a retention fault, reproduced with the debugger detached, fixed at that cause, and covered by a loop test that sleeps and wakes thousands of times without a miss.

The usual failure is debugging on the bench with the probe attached. A debugger keeps clocks and power domains running through sleep, so the part never reaches the state that fails in the field, and the bug vanishes under observation. Anything learned with the probe connected is about a different chip state.

## Scope

Use for: a device that sometimes does not wake, wakes and sleeps again at once, hangs after wake, or has dead peripherals or wrong variables after a low-power mode.

Do not use for: how much current sleep draws (`sleep-current-hunt`); the general method of narrowing a bug (`debugging`); a reset caused by the watchdog (`watchdog-design`); a hard fault after wake (`hard-fault-triage`).

## Workflow

### 1. Reproduce detached and instrument cheaply

Remove the debug probe and its power path, and run the real firmware on battery or a plain supply. Trace with what does not keep the chip awake: spare GPIOs toggled at entry to sleep, at wake and at first use of each peripheral, watched on a logic analyser; and a few bytes of retained memory. Do not use a serial port that stays powered through the sleep as the only trace, since that is a power domain the product may not have. Read `references/wake-checklists.md` for the pin trace layout.

### 2. Record why the device woke

The first lines after wake, before any initialisation, store into memory that survives the mode: the reset-cause register, the wake-source or pending-interrupt register, and a counter of wakeups. Names and bits are vendor specific, so take them from the reference manual for the part. Clear the flags after recording them. A device that comes out of sleep and cannot say why is a device whose failures cannot be classified.

### 3. Classify the failure

Match what the trace shows to one of three classes, because each has a different fix.

**Lost wakeup.** The device sleeps and the event that should wake it has already happened. The pattern: the main loop tests a flag, finds it clear, and an interrupt sets the flag before the sleep instruction runs; the device then sleeps until the next event, which may never come. Fix: test the flag with interrupts masked and enter sleep before unmasking. On Cortex-M, masking with PRIMASK and then executing WFI is safe because WFI still returns when an enabled interrupt becomes pending, even though PRIMASK keeps its handler from running; unmask afterwards and the handler runs at once. A flag set in an interrupt handler must be declared so the compiler re-reads it, and the check and the sleep must be one sequence, not a test, a function call and a sleep.

**Wake-source fault.** The device wakes at the wrong time or at once. Check the edge or level configuration of the wake pin, the pull on that pin, whether the source is still asserted when sleep begins (a level source stays asserted), and whether its flag was cleared before sleeping. An uncleared flag is an instant re-wake loop, which looks like a device that never sleeps; a mis-set edge is a device that never wakes.

**Retention fault.** The device wakes and misbehaves. For the exact sleep mode used, list from the datasheet what is retained: which RAM banks, which registers (peripheral configuration is often lost), which clock trees and which regulators. Everything not on that list must be initialised again after wake; verify by writing a pattern before sleep and reading it after, per bank and per peripheral register of concern.

### 4. Respect start-up times

After wake the system clock may run from a slow internal oscillator until the crystal and PLL settle; an external sensor or radio may need milliseconds before it answers. Use the datasheet's start-up times, wait on the ready flag rather than a delay tuned on the bench, and give the wait a timeout that records an error. A peripheral initialised before its clock is stable fails sporadically, and temperature and supply voltage move the start-up time, which is why the fault appears in the field and not on the bench.

### 5. Fix at the cause and write the regression

Apply the one fix for the class found. Then build a test that cycles sleep and wake as fast as the hardware allows, with a stimulus (a timer, a function generator on the wake pin, or a second board), counts missed wakeups and checks the retained pattern each time, running for tens of thousands of cycles with the debugger detached. A rare race needs volume to show.

### 6. Keep the diagnostics

Leave the wake record in production: reset cause, wake source and wakeup counter, reported in the next telemetry. A fleet's field failures are then classifiable without a return.

## Output format

```markdown
## Reproduction
[Detached or not, supply, trace method, how often it fails.]

## Class
[Lost wakeup, wake-source fault or retention fault, with the trace that shows it.]

## Cause and fix
[The exact sequence or setting and the change.]

## Evidence
[Cycle count with misses, retained-state check, wake record left in place.]
```

## Anti-patterns

**Fixing with a delay.** Sleeping a little longer or waiting a fixed time after wake hides a race at one temperature and supply voltage.

**Attaching the debugger to look.** It changes the state under test. Observe with GPIOs and retained memory instead.

**Testing wake with a human button press.** A race measured in microseconds needs a machine stimulus repeated thousands of times.
