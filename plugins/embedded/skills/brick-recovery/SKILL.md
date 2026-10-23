---
name: brick-recovery
description: "Revive an unresponsive board without destroying what cannot be replaced, and make the next one recoverable: classify what is alive first (supply current on a bench supply, clock, ROM-bootloader banner on UART, SWD or JTAG answering), climb from least to most destructive (recovery button combination, ROM serial or USB DFU, SWD attach with reset under connect, mass erase last), dump flash, option bytes and fuses before any erase, and check the readout-protection level first because the top level is irreversible on several families. Use for \"the board doesn't boot after flashing\", \"locked myself out with readout protection\", \"no UART output at all\", \"how do we recover units in the field\". Not for network gear (routeros-config), preventing the brick (ota-update-safety), a wrong-but-up link (serial-bus-debug), hard faults (hard-fault-triage) or bad stored settings (flash-storage-durability)."
allowed-tools: Read, Glob, Grep
---

# Brick Recovery

Done means the unit runs again, nothing irreplaceable was erased on the way (calibration, unique keys, identity), the cause of the brick is known, and the product has a recovery path that needs only a cable.

The usual failure is reaching for a mass erase first. It always works at the cost of the device's identity: factory calibration, per-unit keys and serial numbers live in the same flash or fuses, and once erased they cannot be regenerated. A second failure is changing a protection setting on a part where the top level cannot be undone.

## Scope

Use for: a board that does not start after programming or an update, a device locked by readout protection or a bad option-byte write, silent boards with no UART output, and designing the field recovery path.

Do not use for: routers and switches (`routeros-config`); preventing the brick with safe update mechanics (`ota-update-safety`); a bus that is up but returns wrong data (`serial-bus-debug`); a fault in running code (`hard-fault-triage`); damaged settings data (`flash-storage-durability`).

## Workflow

### 1. Classify what is alive, touching nothing

Put the board on a bench supply with a current limit and read the current. Zero current means no power path: check the rail, the regulator, a short. A steady idle current means a core stuck in a loop or in reset. A repeating pulse of current means a boot loop (crash, watchdog or brownout reset). Then check, in order: the clock present on a scope, the reset pin held or released, a banner or response from the ROM bootloader on the UART, and whether the debug port answers. Write down each finding; it picks the rung of the ladder. Read `references/recovery-ladder.md` for the decision table and the per-family notes to confirm against the reference manual.

### 2. Check the protection level before connecting hard

Read how readout protection and debug lock are configured on this part and what the current level is, from the reference manual and from whatever the device reports. On several families the top level is permanent: it disables debug and bootloader access for good, and setting it by mistake produces a real brick. Mid levels typically allow regression to the unprotected level only by erasing the whole flash. Know which you are on before choosing a rung.

### 3. Climb from least to most destructive

1. A documented button or pin combination that enters a recovery mode, with nothing connected but power and a cable.
2. The ROM serial or USB DFU bootloader, entered by holding the boot-select pin during reset. It lives in ROM, so a bad flash write cannot remove it, and it can reflash the application.
3. Debug attach with the target held in reset: connect under reset (the debugger asserts the reset line, then halts the core before the bad code runs), then halt, and inspect or reprogram. This defeats firmware that disables the debug pins or sleeps immediately.
4. Mass erase, only after workflow step 4 (Read out and keep everything before erasing). It clears readout protection on parts where that is possible, and it clears everything else with it.

Stop at the first rung that works. Each failed rung is evidence about the cause.

### 4. Read out and keep everything before erasing

Before any erase, if the part allows reading it, dump the whole flash, the option bytes, any user-fuse or OTP area, and the unique device identifier, to files named for the unit. Calibration constants and keys are often in a page nothing in the build regenerates. If protection prevents reading, say so before erasing, because that is the point at which the identity is lost; ask whether the unit is worth more than its data. Hash the dump and keep it with the board's serial.

### 5. Reflash, verify and find the cause

Program the known-good image, verify by read-back, restore the preserved calibration and identity, and boot. Then find out why it bricked: an image written with the wrong vector table or load address, an option-byte or fuse change, a clock configured past what the board supports, an update interrupted by power loss, or code that disables the debug pins in its first lines. A recovered unit with an unknown cause is a repeat.

### 6. Dump a returned unit first

For a unit back from the field, read out the flash and registers as received, before reflashing, so the evidence of its failure survives. Compare the image against the release it should be running; a mismatch tells you whether storage, update or code failed.

### 7. Build recovery into the product

Every product ships with a recovery path that needs only a cable: a ROM bootloader left reachable (boot pin or test pad broken out), a recovery entry in firmware that cannot be disabled by a bad image, or an immutable first-stage loader. Protection is set at the end of the factory flow, with the level chosen deliberately and written down. Exercise the recovery path on a real unit in every release; an untested recovery path is not one.

## Output format

```markdown
## Findings
[Supply current pattern, clock, UART banner, debug response.]

## Protection level
[Level, source, reversible or not.]

## Rung used
[Which, and what the failed rungs showed.]

## Preserved data
[Files, hashes, unit serial.]

## Cause and prevention
[Why it bricked and the recovery path added or tested.]
```

## Anti-patterns

**Mass erase to see if it helps.** It destroys identity and evidence at once; try the cheaper rungs and dump first.

**Raising the protection level to test it.** On parts with an irreversible top level, the test ends the unit. Test on a sacrificial board.

**Reflashing a field return straight away.** It overwrites the only evidence of how it failed.
