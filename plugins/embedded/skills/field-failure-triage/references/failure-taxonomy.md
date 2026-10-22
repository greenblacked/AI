# Failure taxonomy and inspection

## Contents

- Return inspection checklist
- Signs by class
- What to record
- Cases that look like one class and are another

## Return inspection checklist

In this order, before anything is changed:

1. Photograph the unit as received, including labels, damage and any seals.
2. Record serial, lot and date code, hardware revision and firmware version.
3. Note the customer's description of the symptom and the conditions, in their words.
4. Measure battery voltage open-circuit and, if safe, under a known load.
5. Read the device state without resetting it: reset reason, fault record, counters, retained logs.
6. Dump flash.
7. Only then power-cycle, and record whether behaviour changes.
8. Inspect the board under magnification for corrosion, residue, cracked parts and solder defects.

## Signs by class

| Class | Signs |
| --- | --- |
| Firmware | The fault record shows a crash or reset reason that repeats; the same symptom reproduces after a reflash; units on one version fail and others do not, in the same lot |
| Component or assembly | Failure follows the lot, date code or line; intermittent behaviour that changes with flexing or temperature; visible solder or part damage; the failure follows the board in a swap test |
| Environment | Corrosion or moisture marks; ESD damage on exposed pins or ports; failures in one climate or site; battery depleted or swollen; resets correlated with temperature or supply dips |
| Use | Fitted or powered outside specification; modified or repaired; a feature used in a way the design excludes; the same customer or site recurs |

## What to record

For every unit: class assigned, the evidence for it, and the confidence. Keep unclassified units in the table with the reason. The classification count by lot and version is the input to the correlation step.

## Cases that look like one class and are another

- A battery that dies early may be a cell defect (component), a firmware current leak (firmware), or cold-site operation (environment). Check the logged current draw and sleep state before the cell.
- A unit that resets under load may be a weak supply part (component) or a brownout from a failing battery (environment); check the reset reason for brownout and the supply rail.
- A unit that works after a power cycle is rarely proof of a hardware fault; it is more often a firmware hang with no watchdog recovery.
