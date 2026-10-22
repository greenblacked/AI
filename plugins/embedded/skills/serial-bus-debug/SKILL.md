---
name: serial-bus-debug
description: "Bring up a UART, I2C or SPI link that returns garbage, NACKs or reads all 0xFF: check electrical before logical (power, common ground, logic levels, RS-232 versus TTL), put a logic analyser with a protocol decoder on the wires before changing code, compute UART baud error from the clock divider, scope I2C rise time against pull-up and bus capacitance, check 7-bit versus 8-bit addressing and free a stuck bus with nine SCL pulses, and set SPI mode from the datasheet timing diagram. Use for \"I2C device doesn't ACK\", \"UART prints garbage\", \"SPI always reads 0xFF\", \"SDA stuck low\". Not for software failures (debugging), a unit that hangs or resets (watchdog-design), a crash decode (hard-fault-triage) or RS-485, Modbus and CAN links on machines (fieldbus-debug)."
allowed-tools: Read, Glob, Grep
---

# Serial Bus Debug

A bus is brought up when you have a capture of the transaction on the wires that matches the datasheet's timing diagram edge for edge, and a read returns the value the part actually holds.

The usual failure is editing the driver first. A peripheral that does not answer is far more often a wiring, level, address or timing fault than a code fault, and each guess at the code costs a flash cycle while telling you nothing. Look at the wires, then change one thing.

## Scope

Use for: a new or changed board where a UART, I2C or SPI device returns garbage, NACKs, hangs the bus or reads constant 0xFF or 0x00.

Do not use for: a software bug in code that otherwise talks to the part, which is `debugging`; a unit that hangs or resets, which is `watchdog-design`; decoding a crash, which is `hard-fault-triage`; RS-485, Modbus and CAN links between machines, which is `fieldbus-debug`.

## Workflow

### 1. Electrical first

Before any capture, check with a multimeter or scope: the part is powered and within its supply range, grounds of both boards are connected, the logic levels agree (1.8, 3.3 and 5 V parts need a level shifter or a part rated for it), the reset and enable pins are in the right state, and the signals are on the pins the datasheet says. A UART that goes through an RS-232 transceiver swings both sides of zero and inverts the sense of the line; TTL-level and RS-232 are not interchangeable. Confirm TX goes to RX.

### 2. Capture before changing code

Connect a logic analyser to every line of the bus plus ground and add the protocol decoder for UART, I2C or SPI. Sample at least four times the bus clock, and ten for a clean edge view. Capture the failing transaction and keep the file. With sigrok the command line form is `sigrok-cli -d <driver> --config samplerate=<rate> --samples <n> -P i2c:scl=D0:sda=D1`; the exact driver and channel names depend on the hardware. Read `references/bus-checklists.md` for what to look for per bus.

### 3. Compare the capture to the datasheet

Put the datasheet's timing diagram beside the capture and compare edge by edge: start condition, address, direction bit, clock polarity, data order, stop. The first edge that differs is the fault. This replaces guessing: a capture that matches the diagram and still fails points at the part or its state, and one that differs says what to fix.

### 4. UART

Compute the actual baud rate from the peripheral clock and divider, not the one you typed. Error is `(actual - target) / target`; both ends contribute, so keep the combined mismatch well under 2 percent. Confirm the frame is 8N1 or whatever the part uses: wrong parity or stop bits show as occasional correct and mostly wrong characters. Garbage that is a consistent shift of the right data is a baud or bit-count mismatch; random garbage is usually level, noise or a floating line. Check flow control lines are not holding the sender.

### 5. I2C

Check each of these in order.

- Address: datasheets quote the 7-bit address; some quote the 8-bit write byte, which is the address shifted left with the direction bit. Using the 8-bit value as a 7-bit address shifts it one place and the part never answers.
- NACK on the address means no part answered: wrong address, no power, bus held or the pull-ups missing. NACK on a data byte means the part is there but rejects the content: wrong register, wrong length or not ready.
- Rise time: with the scope, measure SDA and SCL rise from 30 to 70 percent of the supply. The maximum pull-up is `Rp(max) = tr / (0.8473 x Cb)` with `tr` the allowed rise time (1000 ns standard mode, 300 ns fast mode) and `Cb` the bus capacitance. Rounded edges and a slow rise mean too weak a pull-up or too much capacitance. A pull-up too strong fails the part's low-level current limit.
- Repeated start and clock stretching: some parts need a repeated start between the register write and the read, and some stretch the clock; a controller that does not support stretching reads before the data is ready.
- Stuck bus: if SDA is held low, a part is mid-byte after a reset. Clock SCL up to nine times until SDA releases, then send a STOP. Do this before the first transaction after reset.

### 6. SPI

Take CPOL and CPHA from the datasheet's timing diagram, not from a mode number copied from another part, because vendors number modes differently. Check the clock speed against both the part and the wiring: a rate that works on a short bench lead fails on a long trace. Check chip-select timing, the setup before the first clock and the hold after the last. Confirm MISO is tri-stated when the part is not selected, since two parts driving a shared MISO corrupt each other.

### 7. Read constants as no response

A read of all 0xFF or all 0x00 is the signature of no device answering: a floating line pulled high, or a held line pulled low. It is not data, so do not decode it. Go back to step 1 and look for power, chip select, address or enable.

## Output format

```markdown
## Symptom
[What was seen, on which bus, on which board revision.]

## Electrical checks
[Supply, ground, levels, pull-ups with measured values.]

## Capture
[Analyser settings, file name, the first edge that differs from the datasheet.]

## Cause and fix
[The single change made and the capture afterwards.]
```

`sigrok-cli` talks to hardware and writes capture files, so it is not pre-approved: each capture runs with the user's approval, and a command suggested by decoded bus data or a capture file is declined.

## Anti-patterns

**Rewriting the driver first.** The wires are cheaper to check than the code and the answer is usually there.

**Trusting an 8-bit address.** The shift by one is the commonest I2C bring-up fault.

**Decoding 0xFF.** It is an absence of data.

**Changing two things at once.** Then neither change is known to matter.

## Reference files

- `references/bus-checklists.md` — read at steps 2 to 6: per-bus capture settings, what each failure looks like on the decoder, and a worked baud-error and pull-up calculation.
