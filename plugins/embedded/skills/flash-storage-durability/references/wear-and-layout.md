# Wear and layout worked reference

## Contents

- Inventory table
- Worked wear budget
- Two-slot record layout
- Measuring hold-up
- Choosing a mechanism

## Inventory table

| Datum | Size | Writes per day | Loss tolerable | Class | Mechanism |
| --- | --- | --- | --- | --- | --- |
| Calibration constants | 64 B | once at factory | none | rare | two slots, written at test, read-only after |
| User settings | 200 B | 20 | last change | on action | key-value log (NVS or similar) |
| Runtime counter | 8 B | 288 | up to 5 minutes | continuous | RAM, flushed every 5 minutes or on warning of shutdown |
| Event log | 32 B per entry | 5,000 entries | tail of ring | continuous | RAM ring, flushed in erase-block units |

A datum with "none" tolerable loss and a high rate cannot be satisfied by flash alone; it needs FRAM, battery-backed RAM, or enough stored energy to write on power-fail.

## Worked wear budget

Region: 8 sectors of 4 KiB on a part rated 100,000 cycles per sector. Data: a 16-byte record saved 1,440 times a day, laid out as a log that fills each sector before erasing it.

- Records per sector: 4,096 / 16 = 256 (ignoring headers, so use perhaps 240).
- Erases per day: 1,440 / 240 = 6.
- Wear levelled across 8 sectors: each sector erased 0.75 times a day.
- Life: 100,000 / 0.75 = about 133,000 days, far beyond any product life.

The same record rewritten in place in one sector: 1,440 erases a day, so 100,000 / 1,440 = about 69 days. The layout, not the flash, decides the result. Where the part is rated 10,000 cycles the log layout gives about 36 years; apply the three-times rule against the product life, not against the arithmetic.

## Two-slot record layout

```text
offset  field
0       sequence number (32 bit, increments on every write)
4       length
8       payload
8+len   CRC-32 over sequence, length and payload
```

Read both slots; discard any whose CRC fails; the survivor with the higher sequence (compared with wrap-around in mind) is current. Write the slot that is not current. If neither is valid, fall back to defaults and record a counter of how often that happened, which is the field signal that the design is losing data.

## Measuring hold-up

1. Find the longest program or erase time in the flash datasheet and the supply current during it.
2. Trigger a scope on the supply monitor output or the reset line. Cut the input supply while the firmware erases a sector in a loop.
3. Measure the time from the monitor trip to the point where the rail falls below the flash minimum voltage. That time must exceed the longest operation with margin; repeat cold and at end-of-life battery or worst-case input.
4. If it does not, enlarge the capacitor, raise the monitor threshold, or stop starting erases once the monitor has tripped.

## Choosing a mechanism

| Situation | Choice |
| --- | --- |
| A few settings, rarely changed | key-value log (NVS on ESP32 parts) or two slots |
| Files, configuration trees, many small writes | littlefs, with its block size set to the erase size |
| Fixed small record at high rate | FRAM or battery-backed RAM; flash only with RAM coalescing |
| Factory data | write once, protect against erase if the part allows |
