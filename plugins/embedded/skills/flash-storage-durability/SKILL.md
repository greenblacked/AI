---
name: flash-storage-durability
description: "Make settings and logs kept in flash or EEPROM survive power cuts and wear: classify each datum by write rate and tolerable loss, compute a wear budget (endurance times erasable units over writes per day times erases per write, at least three times product life), never update in place (two slots with sequence number and CRC, or a log-structured store such as littlefs or NVS), set the brownout threshold above the flash write minimum and size hold-up for the worst erase, tell wear-out from corruption with erase counters, and prove it with a randomised power-cut sweep. Use for \"config corrupted after power loss\", \"flash wore out after a year\", \"littlefs or raw sectors\", \"how often can we write this setting\". Not for server data (backup-recovery-design), database tables (schema-design), firmware image slots (ota-update-safety) or a unit that no longer boots (brick-recovery)."
allowed-tools: Read, Glob, Grep
---

# Flash Storage Durability

Done means every datum the device keeps has a stated write rate, a stated loss it can tolerate, a computed wear life at least three times the product life, and a power-cut test that leaves the store readable at every interruption point.

The usual failure is a store that works on the bench and fails in the field in one of two ways: a setting rewritten in place is half-written when the supply drops, or a counter saved every few seconds burns through one sector in months. Both are design errors that no amount of testing with a stable supply will show.

## Scope

Use for: choosing how settings, counters, calibration and logs are laid out on internal flash, external NOR flash or EEPROM; sizing wear; making writes power-fail safe; diagnosing a unit whose stored data is wrong or whose flash has stopped accepting writes.

Do not use for: backing up server data (`backup-recovery-design`), modelling database tables (`schema-design`), updating the firmware image itself (`ota-update-safety`), or reviving a unit that will not start (`brick-recovery`).

## Workflow

### 1. Inventory every datum

List each item the device writes: name, size, writes per day at the worst realistic use, and what happens if the last write is lost (nothing, one minute of data, a wrong calibration, a security counter rolling back). Group into three classes: written once or rarely (calibration, identity), written on user action (settings), written continuously (logs, counters, state snapshots). The class decides the mechanism, and the loss tolerance decides how often it needs to be written at all. Read `references/wear-and-layout.md` for the inventory table and the worked budget.

### 2. Compute the wear budget

Take endurance in program/erase cycles per erasable unit and the number of units given to the store, both from the datasheet for the temperature range you will see. Then:

years = (endurance x units) / (writes per day x erases per write x 365)

Erases per write is the write amplification expressed per erasable unit: 1 when each application write erases a sector (in-place update), and the record size divided by the usable sector size when records are packed into a log, so 16-byte records in a 4 KiB sector give about 1/240 once headers are allowed for. Divide by what the layout really does, not by the nominal figure. Require at least three times the product life, because wear levelling is never perfect and field use is heavier than the plan. If the number fails, reduce the writes (coalesce, write on change only, write on shutdown from hold-up energy), enlarge the region, or move the datum to FRAM or battery-backed RAM; do not accept a short life on the grounds that the device will be replaced by then.

Internal MCU flash often has an endurance far below external NOR or EEPROM, and datasheets quote it at room temperature; check the figure and its retention trade-off before relying on it.

### 3. Never update in place

An erase or program that is cut leaves a sector in an undefined state, so a record rewritten where it lies can be lost along with its previous value. Use one of two shapes:

- Two slots, each holding a sequence number, the payload and a CRC covering both. Always write the slot that is not current; the valid slot with the highest sequence is the current one. A cut leaves either the old record whole or the new one whole, and the CRC rejects the torn one.
- A log-structured store: littlefs for files, NVS or a similar key-value log for settings. These append and garbage-collect, spreading wear as a side effect. Pin the version, set the block size and cache sizes to the real flash geometry, and read the project's notes on its power-loss guarantees rather than assuming them.

Order matters inside a record: payload first, commit marker or CRC last, so a record without its marker is ignored. Never trust a flash status of "done" without checking the CRC on read-back for anything security-relevant.

### 4. Cover the erase window with the supply

The erase is the longest vulnerable window: a sector erase can take tens to hundreds of milliseconds at the datasheet maximum, during which the device must not lose the voltage the flash needs. Set the brownout or supply-monitor threshold above the minimum programming voltage in the flash datasheet, and make firmware refuse to start a program or erase once the monitor has tripped. Then measure, on the real board, that the hold-up capacitance carries the worst-case program plus erase: the energy needed is the supply current times the longest operation, and the capacitor must supply it while falling from the monitor threshold to the flash minimum (C = I x t / delta V, with margin for capacitor ageing and cold). Read `references/wear-and-layout.md` for the measurement.

### 5. Tell wear-out from corruption

When a unit returns with bad data, decide which it was before blaming either. Read per-block erase counters (littlefs and NVS statistics, or a counter you keep in a block header). Blocks all near the endurance figure while others are young point to missing wear levelling or a hot sector; counters far below the figure with scattered bad data point to torn writes, a brownout window, or a driver that skips the ready check. Failed erase or program status, and reads that need repeated retries, are the signs of true wear-out.

### 6. Prove it with a power-cut sweep

Run the store against a flash model or a switched supply and cut it at a different point on every run: in simulation, abort after the Nth program or erase for every N across a full workload; on hardware, a relay or MOSFET rig on a random timer, thousands of cycles. After each cut, boot, run the consistency check, and compare the data to either the previous or the next state, never anything else. Keep the failing seed. Run the same check on every normal boot in production: verify slot CRCs and the file system, repair or fall back to defaults and record that it happened.

### 7. Route high-rate logs through RAM

A log written line by line wears the region at the line rate. Collect entries in a RAM ring and flush in coarse blocks that match the erase or page size, at an interval the loss tolerance allows. State plainly what is lost on a cut (the unflushed tail) and make the log format self-synchronising so a torn final block does not hide the earlier ones.

## Output format

```markdown
## Inventory
[Datum, size, writes per day, tolerable loss, mechanism.]

## Wear budget
[Endurance, units, erases per write, years against product life.]

## Power-fail design
[Slot or log layout, commit order, brownout threshold, hold-up measurement.]

## Evidence
[Power-cut sweep count and result, boot-time check, counters inspected.]
```

## Anti-patterns

**Saving a counter on every event.** One sector takes every write; a device at ten events a minute, rewriting one sector each time, passes a ten-thousand-cycle limit in under a day. Coalesce or move the counter to a store that tolerates it.

**Testing power loss by pulling the plug a few times.** The vulnerable window is milliseconds in a run of minutes; a dozen manual cuts land outside it. Only a sweep across every flash operation shows the gap.

**Trusting the file system's guarantee without the flash's.** A log-structured store assumes the flash completes or fails an operation cleanly; a low supply voltage breaks that assumption underneath it.
