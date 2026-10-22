---
name: sleep-current-hunt
description: "Find why a battery device draws milliamps asleep or dies in months instead of years, and estimate battery life from a measured trace: measure with a current-ranging power profiler or a shunt and scope, never a bench multimeter, capture a full cycle and integrate charge, rank slices by charge rather than peak, derate capacity for cold, cutoff voltage and self-discharge, then bisect the sleep floor with sleep-only firmware and restore peripherals one at a time. Use for \"sleep current is 800 uA, datasheet says 3\", \"battery lasts weeks not years\", \"estimate battery life from this current trace\". Not for devices that fail to wake or lose state (sleep-wake-bug-hunt), CPU time hot spots (profiling), phone app battery use or a unit that will not start (brick-recovery). A debugger-attached current reading is here; a debugger-attached hang is sleep-wake-bug-hunt."
allowed-tools: Read, Glob, Grep
---

# Sleep Current Hunt

Done means the average current over a full duty cycle is measured with an instrument that can be trusted at that range, the largest consumers are ranked by charge, the sleep floor is explained down to the microamp, and the battery life estimate states the derating it used.

The usual failure is trusting a datasheet figure that holds for the bare chip under ideal conditions, or a multimeter reading that hides short bursts. A board that sleeps at the chip's 3 microamps can still draw 800 because a pin, a pull-up or another part is leaking, and nothing in the firmware looks wrong.

## Scope

Use for: measuring and explaining a device's current in sleep and in its active slices; estimating battery life from a trace; locating the part of the board or firmware that holds the floor high.

Do not use for: a device that does not wake, wakes instantly or loses state (`sleep-wake-bug-hunt`); finding CPU time hot spots (`profiling`); reviving a dead unit (`brick-recovery`). When a debug probe changes the reading, the current question is here, but the functional hang it hides is `sleep-wake-bug-hunt`.

## Workflow

### 1. Measure with an instrument that can follow the load

A bench multimeter's burden voltage drops the rail under load and its range switching drops readings during the transition, so a duty-cycled load reads wrong in both directions. Use a current-ranging power profiler, or a shunt resistor and a scope or logger with enough resolution. Size the shunt so its drop is small against the minimum supply at the highest current, and use a lower-value path or auto-ranging for the burst. Power the device from the battery chemistry's real voltage, not an arbitrary 3.3 V from a lab supply, since regulators and leakage change with voltage. Read `references/measurement-and-budget.md` for set-up, ranges and the checks that your instrument is not lying.

Disconnect the debug probe and serial adapter for the final measurement; both can hold clocks on and back-power pins.

### 2. Capture a whole cycle and integrate charge

Record at least one complete wake-sleep period, and several for a device whose bursts vary (radio retries, sensor warm-up). Integrate current over time to get charge per period. Average current is total charge divided by the period. Peak current matters for the battery's pulse capability but not for the budget.

### 3. Rank slices by charge

Break the cycle into slices (boot, sensor read, radio, processing, sleep) and compute charge for each, as current times duration. A radio burst of tens of milliamps for a fraction of a second usually dominates until the period is long; at long periods the sleep floor takes over, since it runs the whole time. Work on the largest slice first, and say so when the floor is the largest, because shortening the burst then changes nothing.

### 4. Estimate life honestly

Life = usable capacity divided by average current. Usable capacity is the datasheet figure derated for the load's current, for temperature (cold lowers it sharply on many primary cells), for the cutoff voltage at which the electronics stop working, and for self-discharge over the target life. Say which derating factors were used. The worked example and a derating checklist are in `references/measurement-and-budget.md`.

### 5. Bisect the sleep floor

Build firmware that does nothing but enter the lowest sleep mode, with every peripheral clock and pin set as the final product sets them, and measure. Compare against the chip's datasheet figure for that mode, at the same supply voltage and temperature. If it matches, the chip is fine and the excess lies on the board or in a peripheral. Then restore one thing at a time, measuring after each: GPIO configuration, sensors, radio, external memory, debug interface. The step that raises the floor names the culprit. Record each step's reading; a table beats a memory of what was tried.

### 6. Check the usual culprits

- A floating input, or an output driving a pulled-up or pulled-down line against its load, leaking continuously. Configure unused pins as analogue or driven to a defined level, per the vendor's low-power guidance.
- A pull-up to a rail that is on, wired to a chip whose own rail is off, back-powering it through its protection diodes so it never truly turns off.
- A debug probe or an enabled debug domain holding a clock and a regulator on.
- A sensor or transceiver left in standby when it has a power-down mode, or an LED with a series path to a live pin.
- A regulator with a quiescent current larger than the whole sleep budget, or a divider monitoring the battery that is always connected.
- A leaky capacitor or damp, contaminated board, which shows as a floor that varies with humidity and time.

### 7. Verify at the conditions that matter

Repeat the final measurement at the battery's real voltage across its discharge curve, and at the lowest operating temperature, where leakage and capacity both move. A floor that is good on a warm bench at 3.3 V and bad in a cold room at 2.4 V is a field failure waiting.

## Output format

```markdown
## Measurement
[Instrument, range, shunt, supply voltage, probe state, period captured.]

## Charge by slice
[Slice, current, duration, charge per period, share of total.]

## Sleep floor
[Measured against datasheet, bisect table, the culprit found.]

## Life estimate
[Usable capacity and derating, average current, life, sensitivity to the period.]
```

## Anti-patterns

**Reading a multimeter on a duty-cycled load.** It averages in its own way and changes the circuit; the number it shows is neither the sleep floor nor the average.

**Optimising the peak.** Halving a burst that is 5 per cent of the charge saves 2.5 per cent. Rank by charge first.

**Quoting the chip's sleep current for the product.** The datasheet figure excludes every other part on the board, so measure the assembled unit.
