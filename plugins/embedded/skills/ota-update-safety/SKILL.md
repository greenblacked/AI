---
name: ota-update-safety
description: "Design or audit the device-side firmware update so a power cut or a bad image never bricks a unit: list every flash write in the update path and cut power at each with a relay harness before shipping, write to the inactive slot, verify hash and signature over the whole image after the last write, flip the boot-select flag last as one atomic record, run the new slot as a trial confirmed only by an application health check, and raise the anti-rollback counter after confirm. Use for \"design our firmware update\", \"do we need A/B partitions\", \"devices bricked after the OTA\", \"what happens if power dies mid-update\". Not for server-side gradual rollout (release-strategy), store builds (mobile-release), the campaign across devices (ota-fleet-rollout), a unit already dead (brick-recovery) or settings and logs in flash (flash-storage-durability)."
allowed-tools: Read, Glob, Grep
---

# OTA Update Safety

An update path is done when you have cut power at every flash write it performs, with a relay and not by reasoning, and the unit booted a working image each time.

The usual failure is an update tested only on the path where it succeeds. Power loss, a truncated download, a signed but broken image and a new image that boots and then hangs are all ordinary field events across thousands of units, and each one bricks a device that has no second slot, no trial boot or no way back. A brick in the field costs a truck roll or a replacement, so the design has to make the bad outcome impossible rather than unlikely.

## Scope

Use for: designing the on-device update sequence, auditing an existing one, deciding between A/B slots and a single slot with a staging area, and writing the power-cut test plan.

Do not use for: the rollout across a fleet (waves, halts, telemetry gates), which is `ota-fleet-rollout`; server-side progressive delivery, which is `release-strategy`; store submissions, which is `mobile-release`; recovering a unit that no longer boots, which is `brick-recovery`; wear and corruption of settings and log storage, which is `flash-storage-durability`.

## Workflow

### 1. Enumerate every flash write

Read the update code, bootloader and linker layout and list each place flash is erased or programmed: image chunks, the manifest or header, the boot-select flag, any counter, any data the new image migrates. Draw the layout: bootloader, slot A, slot B, flag area, data area, with addresses and erase-block sizes. This list is the test plan, so a write left off it is a write nobody cut power on. Read `references/power-cut-sweep.md` for the table to fill in.

### 2. Write to the inactive slot only

Never write over the image that is running or that the flag points at. Download into the other slot, erasing as you go, and keep the running image intact until the new one has proved itself. If the part has one executable bank and cannot run from a slot it is writing, go to step 8.

### 3. Verify the whole image after the last write

Hash and check the signature over the complete image as stored in flash, after the final byte is written, not over the stream as it arrived. A per-chunk check proves the transport, not what the flash holds. Reject on any mismatch, erase the slot header so a half image never looks valid, and leave the flag untouched. Check the image's version against the anti-rollback counter here, but do not raise the counter yet.

### 4. Flip the boot-select flag last, atomically

Switching slots is one small write that either happened or did not. Keep two copies of the record, each with a sequence number and a CRC, and have the bootloader pick the valid copy with the higher sequence number. A torn write then leaves either the old or the new record readable, never neither. Write the new record to the older copy so the current one stays as the fallback.

### 5. Boot the new slot as a trial

The flag from step 4 marks the new slot as pending, with an attempt counter. The bootloader decrements the counter on each boot of a pending slot and reverts to the old slot when it reaches zero. A watchdog reset during the trial counts as a failed attempt, which is why `watchdog-design` matters here: a hung new image must be reset, not left to spin.

### 6. Confirm only on a real health check

Reaching `main()` proves the image starts, not that it works. Confirm, by writing the confirmed state to the flag record, only after the application has done its job: reached the cloud endpoint, read its sensors, completed its main loop for N minutes. Choose N from the slowest start-up path, not the lab one. An image that never confirms reverts when attempts run out.

### 7. Raise the anti-rollback counter after confirm

The monotonic counter stops an attacker or a stale server installing an old, vulnerable image. Raise it only on confirm; raised earlier, a failed trial leaves a unit that refuses its own known-good old slot. Treat the counter as one-way and rehearse the case where it is ahead of every installed image.

Two further checks belong here. Anything the new image writes to persistent storage before confirm must stay readable by the old image, because a revert runs old code on that data: version the format and keep migrations additive until the update is confirmed. And A/B protects the application, not the bootloader: make the bootloader immutable, or use a dual-bank scheme where a second bootloader exists, and test the update of it separately.

### 8. If there is only one slot

Size a staging area for a compressed or delta image, apply it with a recovery path that survives power loss mid-apply (an apply journal, or a minimal recovery loader that can re-fetch a full image), and keep that loader small enough to be immutable. State plainly that a delta needs the exact installed base version and fall back to a full image on any mismatch.

### 9. Run the power-cut sweep

On a harness with a relay or programmable supply, cut power at every write on the list, at several offsets inside each erase and program, and after each cut let the unit boot and record what it ran. Repeat with a corrupted image, a truncated download, a valid image that hangs, and one that boots and fails the health check. Read `references/power-cut-sweep.md` for the harness and pass criteria.

## Output format

```markdown
## Layout
[Bootloader, slots, flag area, data area: addresses and erase sizes.]

## Flash-write inventory
[Each write, what it protects, the state if power is lost there.]

## Sequence
[Download, verify, flag flip, trial, health check, confirm, counter.]

## Revert triggers
[Attempts exhausted, watchdog, failed health check; where the state lives.]

## Sweep results
[Writes cut, offsets tried, outcomes, failures and fixes.]

## Gaps
[Bootloader update, single-slot limits, data compatibility on revert.]
```

## Anti-patterns

**Confirming at `main()`.** An image that starts and then hangs is now the only image. Confirm after the application has done real work.

**Verifying the stream, not the flash.** A hash computed while downloading says nothing about what was programmed. Re-read the slot.

**One copy of the flag.** A torn write to a single record can leave neither slot selected. Two copies with sequence and CRC.

**Raising the counter early.** A failed trial then locks out the only working image.

**Testing by pulling the plug by hand.** You will hit the same two moments every time. Use a relay and sweep the offsets.

**Assuming A/B covers the bootloader.** It covers the slots. The bootloader needs its own protection.

## Reference files

- `references/power-cut-sweep.md` — read at steps 1 and 9: the write inventory table, harness setup, offsets to try, fault cases and pass criteria.
