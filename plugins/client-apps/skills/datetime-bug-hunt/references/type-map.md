# Type map

Which type holds each temporal class on each platform, and the trap each platform sets.
Read this when choosing a type at step 2.

## Contents

- [The map](#the-map)
- [JavaScript and TypeScript](#javascript-and-typescript)
- [Java and Kotlin, including Android](#java-and-kotlin-including-android)
- [Swift](#swift)
- [Python](#python)
- [PostgreSQL](#postgresql)
- [On the wire](#on-the-wire)

## The map

| Platform | Instant | Local wall-clock time plus zone | Calendar date |
| --- | --- | --- | --- |
| JavaScript with Temporal | `Temporal.Instant` | `Temporal.ZonedDateTime` (or `PlainDateTime` plus a zone string) | `Temporal.PlainDate` |
| JavaScript without Temporal | `Date`, or epoch milliseconds | ISO local string plus IANA zone string, computed with a zone-aware library | `YYYY-MM-DD` string |
| Java, Kotlin (java.time) | `Instant` | `LocalDateTime` plus `ZoneId`, or `ZonedDateTime` | `LocalDate` |
| Kotlin multiplatform | `Instant` (in `kotlin.time` or `kotlinx.datetime`, depending on version) | `LocalDateTime` plus `TimeZone` | `LocalDate` |
| Swift | `Date` | `DateComponents` plus `TimeZone(identifier:)` | `DateComponents` with year, month, day only |
| Python | aware `datetime` in UTC | naive `datetime` plus `zoneinfo.ZoneInfo` name | `date` |
| PostgreSQL | `timestamptz` | `timestamp` (without time zone) plus a `text` zone column | `date` |

## JavaScript and TypeScript

- `Date` is an instant with a local-zone formatter attached. It has no date-only or
  wall-clock form, which is the root of most browser date bugs.
- Date-only ISO strings (`"2026-03-29"`) parse as UTC; date-time strings with no offset
  (`"2026-03-29T09:00"`) parse as local time. The same input with and without a time
  lands on different days for users west of UTC.
- `toISOString()` always prints UTC, so `new Date().toISOString().slice(0, 10)` is
  "today in UTC", not today for the user.
- `Intl.DateTimeFormat` takes a `timeZone` option; pass the zone explicitly whenever the
  zone to render in is not the device's.
- Where the runtime ships Temporal, prefer it: it has a separate type for each class.
  Where it does not, use a polyfill or a library that carries IANA zone rules, and keep
  date-only values as strings until display.

## Java and Kotlin, including Android

- `java.util.Date` and `Calendar` are instants with mutable zone state; avoid them in new
  code.
- On Android below API 26, java.time needs core library desugaring
  (`coreLibraryDesugaringEnabled true` in the Gradle compile options plus the
  `desugar_jdk_libs` dependency).
- `ZonedDateTime.plusDays(1)` keeps the wall-clock time across a DST change;
  `plus(Duration.ofDays(1))` adds exactly 24 hours and does not.
- In a gap, `ZonedDateTime.of(...)` moves the time later by the length of the gap; in an
  overlap it takes the earlier offset, and `withLaterOffsetAtOverlap()` takes the later.
- In `DateTimeFormatter`, `Y` is week-based year and `y` is year of era; `u` is the
  proleptic year.
- The device's zone database updates separately from the app. On an old device a zone
  whose rules changed recently computes the wrong offset; compute safety-critical
  instants on the server.

## Swift

- `Date` is an instant. It has no zone; the zone lives in the `Calendar` or formatter.
- A calendar date is `DateComponents` with only `year`, `month` and `day` set. Converting
  it to a `Date` invents a time and a zone — do that only at display, with the calendar's
  `timeZone` set deliberately.
- `Calendar.current` follows the device and changes when the user travels; use a
  calendar with an explicit `timeZone` for anything tied to a place.
- `DateFormatter` for a wire format needs `locale = Locale(identifier: "en_US_POSIX")`
  and an explicit `timeZone`. `ISO8601DateFormatter` is the simpler choice for RFC 3339
  instants.
- `Calendar.date(byAdding: .day, value: 1, to:)` keeps the wall-clock time; adding
  `86_400` seconds does not.

## Python

- A naive `datetime` has no zone and compares wrongly with an aware one; mixing them
  raises in some operations and silently misleads in others.
- `datetime.utcnow()` returns a naive value and is deprecated from Python 3.12; use
  `datetime.now(timezone.utc)`.
- `zoneinfo.ZoneInfo("Europe/Berlin")` uses the system zone database, or the `tzdata`
  package where there is none (common on Windows and in slim containers).
- `fold=0` selects the first of two overlapping times, `fold=1` the second.
- Arithmetic on an aware `datetime` with a `ZoneInfo` zone is wall-clock arithmetic;
  convert to UTC first when you mean elapsed time.

## PostgreSQL

- `timestamptz` stores an instant (normalised to UTC) and renders it in the session's
  `TimeZone` setting. A client that relies on that rendering inherits the server's zone.
- `timestamp` without time zone stores a wall-clock reading with no zone; pair it with a
  zone-name column for a future local time.
- `date` is a calendar date. Casting `timestamptz` to `date` uses the session zone, so
  the result depends on who is connected.
- `AT TIME ZONE 'Europe/Berlin'` converts in both directions depending on the input
  type; test which one a query is doing.

## On the wire

| Class | Format | Example |
| --- | --- | --- |
| Instant | RFC 3339 with `Z` or an offset, or epoch milliseconds | `"2026-03-29T01:30:00Z"` |
| Local wall-clock time | Local date-time with no offset, plus a zone field | `{"local": "2026-11-01T01:30:00", "zone": "America/New_York"}` |
| Calendar date | ISO 8601 date | `"2028-02-29"` |

Document the class of each field in the API contract. A client that receives
`"2026-03-29T00:00:00Z"` for a birthday cannot know it was meant as a date.
