# Offline timestamps

## Contents

- Record layout
- Backfill procedure
- Boots that never synced
- Sync acceptance table
- Drift worked example

## Record layout

Each stored record carries:

| Field | Meaning |
| --- | --- |
| `boot_id` | Counter in non-volatile storage, incremented once per start. Wraps only after a lifetime. |
| `mono_ms` | Monotonic milliseconds since this boot, 64-bit or extended so it does not wrap in the record. |
| `utc` | Seconds since the Unix epoch, 64-bit, or absent when unknown. |
| `utc_quality` | Exact (taken just after a sync), estimated (backfilled by offset), or unknown. |

Keep the device-side counter that increments `boot_id` in a place that survives power loss and does not wear a cell out: see `flash-storage-durability` for counters on flash.

## Backfill procedure

1. On each sync, compute `offset = utc_now - mono_now` for the current boot and store `(boot_id, offset, source, time_of_sync)`.
2. For every record of that boot with unknown `utc`, set `utc = offset + mono`, and mark quality estimated.
3. Records written after the sync take UTC directly.
4. If the backend does the backfill, send the offset table with the records and keep both stamps; the raw stamp is the evidence if the sync turns out to be wrong.

The error in a backfilled record is the drift between the record and the sync, so state it: a record 6 hours before a sync on a 20 ppm clock is off by about 0.4 seconds.

## Boots that never synced

A boot that ended without a sync has records with a boot id and monotonic time only. Order them within the boot exactly. Place the boot in real time by bracketing: it started after the end of the previous boot's last known UTC and ended before the next boot's first sync. Report the interval instead of a point, and mark records as bracketed. If the RTC survived the power loss on a backup supply, use it as an estimate, labelled as such.

## Sync acceptance table

| Condition | Action |
| --- | --- |
| Earlier than the firmware build date | Reject; log the source and value |
| No current estimate (cold boot, no backup clock) | Accept the first reading that passes the build-date check, marked estimated, and replace it when a second reading from the same or another source agrees; do not hold, or the device never acquires time |
| Within the allowed step (the policy limit) of the current estimate (when one exists) | Accept |
| Beyond the limit, one source | Hold; ask a second source or wait for a second reading |
| Beyond the limit, two sources agree | Accept; log the size of the step |
| Source unavailable | Free-run; increase the uncertainty with time since last sync |

## Drift worked example

At 20 ppm the clock gains or loses 20 microseconds per second:

- 86,400 seconds in a day gives 1.728 seconds per day.
- Over 30 days that is about 52 seconds.

If the product needs one second accuracy, resync at least daily. If it needs one minute, monthly is enough on a crystal that is held within 20 ppm over temperature. For a 1 per cent RC, the same day gives 864 seconds, so a per-day sync is not enough for any accuracy under a quarter of an hour.
