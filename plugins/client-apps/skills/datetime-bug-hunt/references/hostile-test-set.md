# Hostile test set

The fixed cases every date fix is proven against, with concrete values and what each
should assert. Read this at step 6, when writing the tests.

The dates below were computed from the IANA zone database for 2026. Zone rules change by
government decision, so confirm each value against the zone data your runtime ships
before relying on it, and prefer computing the transition in the test from the library
over hard-coding it where the library allows.

## Contents

- [The cases](#the-cases)
- [Pinning the zone in a test](#pinning-the-zone-in-a-test)
- [Running the set in CI](#running-the-set-in-ci)

## The cases

| # | Case | Concrete value | Assert |
| --- | --- | --- | --- |
| 1 | DST gap | `America/New_York` 2026-03-08 02:30 does not exist (02:00 jumps to 03:00). `Europe/Berlin` 2026-03-29 02:30 does not exist. | The chosen gap policy: usually resolves to 03:30 local; or the input is rejected with a message |
| 2 | DST overlap | `America/New_York` 2026-11-01 01:30 happens twice, at 05:30Z and 06:30Z. `Europe/Berlin` 2026-10-25 02:30 happens twice, at 00:30Z and 01:30Z. | The chosen overlap policy, and that a daily recurrence still fires once at 01:30 local |
| 3 | Missing midnight | `America/Havana` 2026-03-08 jumps from 23:59:59 the night before to 01:00; `America/Santiago` 2026-09-06 likewise | "Start of day" is 01:00, not an exception or the previous day; a day-range query still covers the whole day |
| 4 | Recurrence across a change | Daily 09:00 `Europe/Berlin` from 2026-03-27 to 2026-03-31 | Every occurrence is 09:00 local; the UTC times shift from 08:00Z to 07:00Z |
| 5 | Day length | 2026-03-29 in `Europe/Berlin` is 23 hours; 2026-10-25 is 25 hours | "Events on this day" range and any per-day duration totals |
| 6 | Far east | `Pacific/Kiritimati` (UTC+14, no DST) | The instant 2026-03-29T10:30Z is already 30 March there |
| 7 | Far west | `Etc/GMT+12` (UTC-12; the POSIX sign is inverted) | The same instant is still 28 March there, so one instant spans three dates |
| 8 | Fractional offset | `Asia/Kathmandu` (UTC+05:45); `Australia/Lord_Howe`, whose DST shift is 30 minutes (2026-10-04 02:00–02:29 does not exist) | No code assumes whole-hour offsets or a one-hour DST shift |
| 9 | Leap day | `2028-02-29` as a birthday or due date | Round-trips unchanged through every layer; displays as 29 February in every test zone |
| 10 | Leap day plus a year | `2028-02-29` plus one year | The product's chosen rule (java.time and Temporal's default constrain to 2029-02-28); anniversaries and ages agree with it |
| 11 | Device zone mismatch | Device in `Pacific/Auckland`, user profile in `America/Los_Angeles`, test runner in `Asia/Kolkata` | Each screen renders in the zone it claims to; "today" and "overdue" are computed in the stated zone |
| 12 | Date-only round trip | A user in `America/Los_Angeles` enters 2026-03-29 | The API receives `"2026-03-29"` and the same user, and a user in `Pacific/Kiritimati`, both see 29 March |

Case 12 is the one that catches the commonest bug in the whole class. Write it first.

## Pinning the zone in a test

Inject the clock and the zone wherever the code allows: a test that passes a zone as an
argument cannot be broken by the machine it runs on. Where code reads the process
default, set it per test and restore it afterwards.

| Runtime | Inject | Process default |
| --- | --- | --- |
| Node, Jest, Vitest | Pass a zone string to `Intl.DateTimeFormat` or the date library | Start the runner with `TZ=Pacific/Auckland`; set it before any `Date` is created |
| JVM, Android unit tests | `Clock.fixed(instant, zoneId)` and an explicit `ZoneId` | `-Duser.timezone=...`, or `TimeZone.setDefault(...)` restored in teardown |
| Android emulator | Inject as above | Start the emulator with `-timezone America/New_York` |
| Swift, XCTest | A `Calendar` and `TimeZone` passed in, and a `now` closure | `NSTimeZone.default = TimeZone(identifier: ...)!`, restored in teardown |
| Python | `ZoneInfo` passed in, and a clock function | `os.environ["TZ"] = ...` then `time.tzset()` (Unix only) |

A test that asserts on formatted output also depends on the locale. Pin it too, or assert
on the structured value rather than the string.

## Running the set in CI

- Run the whole suite at least once in a zone with DST and a large offset —
  `Pacific/Auckland` or `America/Los_Angeles` — not only in UTC, which most CI runners
  default to.
- Revert the fix locally and confirm at least one case fails. A test set that passes
  with the bug present is not proving the fix.
- Keep the set in one shared fixture so the next date bug is tested against the same
  cases rather than a fresh hand-picked date.
