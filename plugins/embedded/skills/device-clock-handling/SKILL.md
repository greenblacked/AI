---
name: device-clock-handling
description: "Get time right on devices whose clocks drift or wrap: keep two clocks, a monotonic tick since boot that drives every timeout and interval and wall-clock UTC used only for timestamps; stamp records with boot id plus monotonic time and backfill wall time once synced; compare ticks with unsigned subtraction and test by starting the counter ten seconds before the wrap; budget drift (20 ppm is about 1.7 seconds a day, an uncalibrated RC can be percent-level) and set a resync policy; sanity-check large time jumps; plan for 32-bit time_t in 2038. Use for \"timestamps are 1970 after reboot\", \"RTC drifts a minute a week\", \"timeouts break after 49 days\", \"how do we timestamp offline data\". Not for time-zone bugs in application code (debugging), a Linux host's chrony or NTP daemon (time-sync-repair), certificate lifetimes (device-trust-anchors), wake failures (sleep-wake-bug-hunt)."
allowed-tools: Read, Glob, Grep
---

# Device Clock Handling

Time handling is done when no timeout depends on wall-clock time, every stored record can be placed in real time after the fact, and the code was run across each counter wrap on a bench rather than reasoned about.

The usual failure is a single clock asked to do two jobs. Wall-clock time is set by a sync, so it jumps; a timeout built on it fires early, never, or all at once when the sync lands. A tick counter never jumps but means nothing to a person reading a log. Devices also lose time in ways servers do not: the RTC resets on power loss, the oscillator drifts, and the first sync may be minutes or days after boot. Keeping the two clocks separate and recording enough to join them later resolves most of it.

## Scope

Use for: timestamps wrong after reboot, drifting clocks, timeouts failing after long uptime, stamping data collected while offline, resync policy, and the 2038 limit.

Do not use for: time zones and daylight saving in application code, which is a different problem from device clocks and is `debugging`; the chrony or NTP daemon on a Linux host, which is `time-sync-repair`; the validity period of certificates and how to keep trust anchors current, which is `device-trust-anchors`; a device that fails to wake from sleep, which is `sleep-wake-bug-hunt`.

## Workflow

### 1. Inventory the clocks

List every time source on the device: the core tick (SysTick or a hardware timer), the RTC and its crystal or RC source, any battery or supercapacitor backup, and the sources that can set time (network time, cellular network time, GNSS, a host). For each, write down the width of its counter, the rate, what survives a reset and what survives power loss. Many bugs are visible in this table before any code is read.

### 2. Separate monotonic from wall time

- Monotonic: ticks since boot. It never goes backwards and never jumps. Every timeout, retry interval, debounce and rate limit uses it, and only it.
- Wall time: UTC, used for timestamps and for nothing that decides behaviour. Store and transmit UTC; apply local time zones at the display, never on the device unless the product needs it.

Search the code for places that read wall time to decide whether something has elapsed. Each is a defect that fires on the next sync.

### 3. Stamp records so they can be fixed later

When wall time is not yet known, a record carries a boot id (a counter in non-volatile storage incremented at each start, or a random value) and the monotonic time within that boot. When a sync arrives, compute the offset for the current boot, `utc_at_boot = utc_now - monotonic_now`, store it against that boot id, and let the device or the backend turn earlier records of the same boot into UTC. Records from boots that never saw a sync keep their boot-relative stamp and are ordered by boot id; mark them as estimated, not exact. Read `references/offline-timestamps.md` for the record layout and the backfill procedure.

### 4. Handle wrap on every counter

A 32-bit millisecond counter wraps after 2^32 ms, which is about 49.7 days. A 16-bit counter at 32768 Hz wraps every 2 seconds and a 24-bit SysTick wraps quickly at core clock rates, so extend narrow counters in the overflow interrupt or by reading them often enough.

- Compare with unsigned subtraction: `(uint32_t)(now - start) >= interval`. This is correct across a wrap as long as the interval is under half the range.
- Never store a deadline as `start + interval` and compare it with `>=`.
- Test it: start the counter ten seconds before the wrap in a build or a test hook, and run every timer-driven path across it. A wrap that was not exercised is a wrap that has not been checked. Run it for each counter width in the inventory.

### 5. Budget drift and set a resync policy

Drift in parts per million converts to time: 20 ppm is 20 microseconds per second, about 1.7 seconds per day, about a minute a month. An uncalibrated internal RC oscillator can be off by a percent or more, which is minutes per day, and it moves with temperature. Decide the accuracy the product needs, compute how long the clock can free-run before it is outside that, and set a resync interval shorter than that. Where the crystal's temperature curve matters, calibrate against a sync and store the correction. Record the time since last sync and the last measured error so the backend can see a clock going bad.

### 6. Sync safely

Time can come from network time (SNTP or NTP), cellular network time (NITZ, where the carrier provides it), GNSS, or a paired host. Rank the sources and say which wins. Before applying any sync:

- Reject a time earlier than the firmware's build date, which cannot be right.
- Treat a large step as suspect. Apply small corrections by slewing or in a single step, and require two agreeing readings, or a confirmation from a second source, before accepting a jump beyond the policy limit.
- Never let a sync move the monotonic clock. Only the offset between the two changes.
- Account for leap-second handling: GNSS time runs ahead of UTC by a whole number of leap seconds; use the offset the receiver supplies.

### 7. Plan the long dates

A signed 32-bit `time_t` overflows on 19 January 2038. Use a 64-bit time type for stored and exchanged timestamps, check any library the build links, and check on-wire and on-flash formats that store seconds in 32 bits. Certificate validation uses this clock: a device with a wrong clock rejects valid certificates or accepts expired ones, so the sync must be able to complete without a validated connection or use a trusted time source. `device-trust-anchors` covers the certificate side.

### 8. Verify

Run these on the bench before calling it done:

1. Power-cycle with no network and check records carry boot id and monotonic stamps.
2. Supply a sync after several records exist and check they backfill correctly.
3. Run a timer test across each counter wrap.
4. Inject a bad sync (far past, far future) and check it is rejected.
5. Let the clock free-run for the drift budget and check resync brings it back.

## Hand back

The clock inventory, the rules for each clock, the record format, the drift budget and resync interval, the sync acceptance rules, and the results of the verification list.

## Anti-patterns

**Timeouts from wall time.** They fire when the clock is corrected.

**`start + interval` deadlines.** They break at the wrap.

**Accepting any sync.** One bad server date puts every record in 2099.

**Local time on the device.** Daylight saving rules change; UTC does not.

## Reference files

- `references/offline-timestamps.md` - read at steps 3 and 6: the record layout with boot id, the offset backfill, handling of boots that never synced, and a sync acceptance table.
