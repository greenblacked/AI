# Measurement and budget reference

## Contents

- Instrument set-up
- Worked life estimate
- Derating checklist
- Bisect table template

## Instrument set-up

A current-ranging profiler (a source-meter style instrument that switches internal ranges and logs at high rate) is the simplest route. With a shunt and scope:

1. Choose the shunt so the voltage across it at the highest burst current is under about 2 per cent of the supply, and at sleep current still well above the scope's noise floor. If no single value does both, use two shunts switched by a transistor or a profiler.
2. Measure the shunt voltage with a differential probe or an amplifier; do not ground-reference a probe across it on a grounded device.
3. Check the instrument against a known resistor load at the sleep current and at the burst current before trusting any trace.
4. Check that the supply being measured is the one the battery would provide: a lab supply with a large output capacitance hides short pulses.

## Worked life estimate

Cell: 220 mAh nominal primary coin cell. Usable after derating for cold, cutoff voltage and pulse load: assume 70 per cent, so 154 mAh. Cycle: a 20 mA burst of 100 ms once an hour, 3 microamps asleep.

- Burst charge per hour: 20 mA x 0.1 s = 2 mA s, which is 0.56 microamps averaged over 3,600 s.
- Average current: 3 + 0.56 = about 3.6 microamps.
- Life: 154 mAh / 3.6 microamps = about 43,000 h, nearly 5 years.

Same device with an 800 microamp floor: 154 mAh / 800 microamps = 192 h, eight days. The burst is irrelevant; the floor is the whole story. Add self-discharge (a few tenths of a per cent to about a per cent a year for good lithium primaries) as a separate sink, not folded into capacity.

## Derating checklist

- Capacity quoted at what load current and cutoff voltage? Re-read the discharge curve at your load.
- Lowest operating temperature: capacity and pulse capability both drop.
- Pulse load against internal resistance: a burst can sag the rail below the brownout level even with charge remaining.
- Self-discharge over the target life.
- Regulator efficiency at light load, which can be poor.
- Margin for ageing and manufacturing spread.

## Bisect table template

| Step | Configuration | Floor (microamps) | Change |
| --- | --- | --- | --- |
| 0 | Sleep-only firmware, all pins analogue, no probe | | |
| 1 | + production GPIO configuration | | |
| 2 | + sensors initialised then powered down | | |
| 3 | + radio initialised then off | | |
| 4 | + external memory | | |
| 5 | + debug interface enabled | | |
