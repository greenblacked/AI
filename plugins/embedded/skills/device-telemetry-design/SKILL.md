---
name: device-telemetry-design
description: "Decide what a device reports so field problems stay diagnosable inside a data and battery budget: fix bytes per day per device from plan cost and radio energy, then spend it on a minimum (reset reason and count, uptime, build id, fault record with PC, LR and CFSR, update state, heap and stack watermarks, battery voltage, link quality, time since contact, error counters); keep a ring log in retained RAM or flash and flush it with the crash on next boot; aggregate counters, send events on state change; use a compact versioned schema; bound any log-level raise; test with three days offline. Use for \"what should devices send\", \"we can't tell why units reset\", \"cellular bill is too high\", \"log strategy for devices\". Not for service instrumentation (instrumentation), paging (alert-design), cloud spend (cost-review), reading telemetry once a problem exists (field-failure-triage)."
allowed-tools: Read, Glob, Grep
---

# Device Telemetry Design

Telemetry is designed when its daily byte budget is a number, every field in the report earns its place against a diagnosis it enables, the device keeps enough locally to explain a crash it cannot report at once, and the whole scheme survived three days with no connectivity.

The usual failure is deciding what to send at the end, from what the firmware happens to log. The result is a stream of free-text lines that costs a fortune on a cellular plan and still cannot answer the first question after a bad week: why did these units reset. The opposite is a bare heartbeat that proves the device is alive and nothing more. A fixed budget forces the choice of what matters, and a fixed set of fields makes fleets comparable.

## Scope

Use for: choosing what a device reports, how often, in what format and under what budget; local logging that survives resets; and remote log-level control.

Do not use for: instrumenting a server-side service, which is `instrumentation`; deciding what pages a person, which is `alert-design`; analysing cloud spend, which is `cost-review`; reading the telemetry once a fleet problem already exists, which is `field-failure-triage`.

## Workflow

### 1. Fix the budget first

Work out bytes per day per device from two limits and take the smaller:

- Money: the data-plan cost per megabyte against what each device may cost per month, remembering the overheads (TLS, MQTT or CoAP headers, TCP or DTLS handshakes) that dominate small messages.
- Energy: the energy of a radio-on second against the battery budget. Each transmission wakes the radio, attaches or resumes, sends and lingers in a connected state; a few large messages cost far less than many small ones.

Write the budget as bytes per day, and the number of connections per day it permits. Everything that follows is spending that number.

### 2. Require a minimum set

Every device reports, at least on a slow cycle:

| Field | Why |
| --- | --- |
| Reset reason and reset count | Separates brownout, watchdog, software and fault resets |
| Uptime since boot | Distinguishes a fresh reset from a long-lived unit |
| Firmware version and build id | Matches crashes to the exact ELF |
| Fault record (PC, LR, CFSR and related registers) | Turns a reset into a source line; see `hard-fault-triage` |
| Update state | Shows stuck or reverted updates |
| Heap low-water mark | Shows slow memory exhaustion |
| Stack watermarks per task | Shows approaching overflow; see `memory-footprint-budget` |
| Battery voltage | Shows depletion and brownout risk |
| Link quality | Separates a device fault from a coverage fault |
| Seconds since last cloud contact | Shows how long it was disconnected |
| Error counters per subsystem | Locates the failing part without log text |

Add fields only when you can name the diagnosis they allow. Remove ones that nobody has used.

### 3. Keep a ring log locally and flush it with the crash

Keep a ring log of the last events, in retained RAM that survives a warm reset or in flash if it must survive power loss, using compact event codes with arguments rather than strings. On the next boot, if the reset was abnormal, attach the ring log and the fault record to the first report. This is what makes a reset diagnosable: the device cannot send during the fault, but it can send what it saw before it on the next boot. Guard the log against being overwritten by the fault itself and against wearing flash out; see `flash-storage-durability`.

### 4. Aggregate on the device, send events on change

Count on the device and send the counter, not each occurrence. Send an event only on a state change: link lost, update started, battery low crossed. A heartbeat is a counter that increments, not a timestamp; the receiver notices a gap in the sequence and does not have to trust the device clock, which see `device-clock-handling`. Report on a schedule that spreads across the fleet with jitter, so a restart does not cause every unit to connect at once.

### 5. Choose a compact, versioned schema

Use a binary encoding such as CBOR or protobuf with numeric keys, not JSON with long names. Put a schema version in every message. The schema must tolerate unknown fields so that old firmware and new backends, and the reverse, keep working across a staged rollout. Never reuse a field number for a different meaning. Keep a field registry in the repository with the unit and the meaning of each field.

### 6. Allow a bounded log-level raise

Give the backend a way to raise one device's logging for a limited time, delivered as a command or a config flag: verbose logging for N minutes or until a byte cap, then back to normal automatically. Without the expiry, a forgotten debug switch drains a battery and a data plan. Log that the raise happened and what it cost.

### 7. Test by cutting connectivity

Take a unit, cut connectivity for three days, and exercise the faults you care about: a reset, a fault, a low-battery event, an update attempt. Restore the link and check that nothing was lost, the sequence shows the gap, the ring log and fault record arrived, no buffer overflowed silently, and the data sent after reconnection stayed within the budget. If the buffer fills, the policy for what to drop (oldest first, or keep the faults and drop routine samples) must be written down and observed.

## Hand back

The byte and connection budget with its arithmetic, the field registry, the report schedule, the local log design, the schema and versioning rule, the log-level control, and the results of the three-day test.

## Anti-patterns

**Free-text logs over cellular.** The bill grows and the diagnosis does not.

**A heartbeat with no content.** It says alive, never why it reset.

**Timestamps as heartbeats.** They depend on a clock that may be wrong.

**No expiry on verbose mode.** The battery is the cost.

**Sending every event.** Aggregate on the device.

## Reference files

- `references/telemetry-budget.md` - read at steps 1, 2 and 5: the budget arithmetic with a worked example, a field registry template, the message layout, and the schema evolution rules.
