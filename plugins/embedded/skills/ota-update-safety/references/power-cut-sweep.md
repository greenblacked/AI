# Power-cut sweep

## Contents

- The write inventory table
- Harness
- Offsets to cut at
- Fault cases beyond power loss
- Pass criteria
- Recording results

## The write inventory table

Fill one row per erase or program the update path performs. A row with an empty last column is a write nobody has thought about.

| Write | Where | Erase or program | State if power is lost here | What the bootloader does next |
| --- | --- | --- | --- | --- |
| Slot erase | inactive slot | erase, per block | slot half erased, flag unchanged | boots old slot |
| Image chunk | inactive slot | program | partial image, header not yet valid | boots old slot |
| Slot header | inactive slot | program | header torn | header CRC fails, slot ignored |
| Flag record | flag copy B | erase then program | copy B invalid, copy A valid | uses copy A |
| Confirm record | flag copy | program | trial still pending | next boot is another attempt |
| Counter raise | counter area | program | counter old or new | both accepted by the checks |
| Data migration | data area | erase, program | old and new format mixed | old image can still read it |

## Harness

A relay or programmable supply controlled by a script, a way to watch the unit's boot (a serial log or a GPIO that the bootloader and application toggle), and a way to read back which slot ran. Cut the supply, wait long enough for the rail and any capacitance to fall fully below brown-out, restore it and record the outcome. Pulling a connector by hand is not a sweep: it lands on the same moments each time.

Let the script trigger the cut from a signal the firmware emits at the start of each write (a pin toggle added for test builds), then add a delay so the cut falls at a chosen point inside the operation. Keep the test build's flash layout identical to the release layout.

## Offsets to cut at

For each write, cut at the start, partway through, and just before it completes. For an erase, the middle matters most because a block can be left partly erased and read back unreliably. For a program of a record larger than the flash write unit, cut between units. Run the whole sweep more than once: a single pass can land on the lucky side of a race.

## Fault cases beyond power loss

- Truncated download: the connection drops at several byte counts, then restarts.
- Corrupted byte in the stored image: flip one bit in a programmed slot.
- Valid signature, wrong target: an image for another board or a lower version.
- Image that boots and hangs: relies on the watchdog and attempt counter.
- Image that boots and fails the health check: relies on the revert.
- Image with a data format change: confirm the old image still reads it after revert.
- Update of the update client itself.

## Pass criteria

Every run ends with the unit running a complete, signed image, either the old one or the new one, and no run requires a programmer. A run that ends in the old image is a pass if the new image was the one that was interrupted. Any run that needs manual recovery is a defect in the sequence, not a rare case.

## Recording results

Keep one line per run: write, offset, fault, slot that ran, time to recover, notes. Re-run the sweep whenever the update code, the bootloader or the flash layout changes, because the inventory changes with them.
