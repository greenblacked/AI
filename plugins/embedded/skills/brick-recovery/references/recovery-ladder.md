# Recovery ladder reference

## Contents

- Symptom to rung table
- Per-family notes
- Dump checklist
- Recovery path design checklist

## Symptom to rung table

| What you observe | Likely state | First action |
| --- | --- | --- |
| Zero supply current | No power path or dead regulator | Check rails with a meter and scope, look for a short |
| Steady idle current, no output | Core stuck, held in reset, or clock failure | Check the reset pin and clock; try debug attach under reset |
| Repeating current pulse | Boot loop (crash, watchdog, brownout) | Attach under reset, halt, read the reset cause |
| ROM banner on UART when boot pin held | ROM bootloader alive | Use serial or DFU to reflash |
| Debug port answers, firmware does not | Bad image or disabled pins | Halt and reprogram |
| Debug port refuses, ROM bootloader answers | Protection or pin disabled | Read the protection level; use the bootloader |
| Nothing answers anywhere | Protection top level, damaged part or wrong wiring | Verify wiring on a known good board first |

Verify the tools on a known-good board before blaming the unit: a faulty probe or cable produces the same silence.

## Per-family notes

These are patterns to confirm against the reference manual and the vendor's programming guide for your part, not recipes.

- Many Cortex-M families have a ROM bootloader entered by a boot-select pin at reset and reachable over UART, USB DFU or both.
- Some families protect the debug port with a lock; the vendor's tool offers a recover command that erases the flash to remove it. That erase removes calibration too.
- STM32-style read-out protection has three levels: none, a level where regression to none erases the flash, and a final level that cannot be undone. Confirm the exact behaviour for your part.
- ESP32-class parts enter a ROM download mode when a strapping pin is held low at reset; eFuses are one-time and cannot be erased.
- RP2040-class parts present a USB mass-storage bootloader from ROM when the boot button is held at power-up.
- Fuses and OTP bits, once blown, are permanent; document which ones the factory flow sets.

## Dump checklist

1. Full flash image.
2. Option bytes or user configuration registers.
3. OTP or fuse area, including unique ID.
4. Calibration pages in external flash or EEPROM.
5. File name with unit serial, date and the tool version used; store the hash separately.

## Recovery path design checklist

- Boot-select pin or test pad reachable in the enclosure, or a documented sequence.
- A first-stage loader that is never overwritten by updates.
- Debug access either left enabled in a protected way or recoverable by a documented erase that preserves identity elsewhere.
- Identity stored where an erase of the application cannot reach it, or backed up at manufacture.
- The recovery procedure run on one unit from every release candidate, by someone who did not write it.
