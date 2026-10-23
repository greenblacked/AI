---
name: datetime-bug-hunt
description: "Fix off-by-one-day, wrong-hour and daylight-saving bugs in apps and their APIs. Classify each temporal value as an instant, a local wall-clock time or a calendar date; store instants in UTC, wall-clock times with an IANA zone name rather than an offset, and dates as dates, never midnight timestamps; expand recurrence in the event's own zone; then prove the fix against one fixed hostile set: DST gap and overlap, UTC+14 and UTC-12, a leap day, and a device zone unlike the user's. Use when someone says \"the birthday shows a day early\", \"the reminder fired an hour late after the clocks changed\", \"dates are wrong for users in Australia\" or \"what type should this timestamp be\". Not for the endpoint's shape (api-design), column types for a new table (schema-design), translated date formats and calendars (locale-edge-sweep), or a bug not about time (debugging)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Datetime Bug Hunt

Done means every temporal value on the path has a named class, is stored and sent in the
form that class needs, and the fix passes the same hostile test set that would have
caught the original bug — not one hand-picked date that happens to work.

Almost every "off by one day" bug is a calendar date that was turned into a timestamp at
midnight somewhere along the way. Midnight UTC on 29 March is still 28 March in New York,
so a birthday stored as `2026-03-29T00:00:00Z` renders a day early for half the planet.
Almost every "off by one hour" bug is a future local time stored as an instant or as a
fixed offset, computed before a DST rule or a government changed what that offset means.
Neither shows up in tests run on a laptop in the developer's own zone on an ordinary
Tuesday, which is why the test set below is fixed rather than chosen per bug.

## Scope

Use for: a date or time that is wrong for some users, some days of the year, or after a
clock change; deciding how to store, send and compute dates, times and recurring events
in a client and its API; reviewing date handling before it ships.

Do not use for: the resource and error shape of an endpoint (`api-design`); choosing
column types and keys for a new table (`schema-design`), though step 2's classification
tells that skill which type each column needs; month names, calendars and date formats
in other languages (`locale-edge-sweep`); a failure that turns out not to involve time at
all (`debugging`).

## Hard gates

1. No fix before every value on the failing path has a class from step 1.
2. No future local time stored as a UTC instant or as a numeric offset alone.
3. No date-only value carried as a timestamp anywhere between input and display.
4. The fix is proven against the full hostile set in step 6, with the device zone set
   explicitly in the test, not inherited from the machine running it.

## Workflow

### 1. Classify every temporal value on the path

Trace the value from where it is entered to where it is shown — form, client model,
request body, API, database, back out, formatter — and give it exactly one class:

| Class | Meaning | Examples | Store and send as |
| --- | --- | --- | --- |
| Instant | A moment that happened or will happen, the same everywhere | `created_at`, payment time, log line, token expiry | UTC: an RFC 3339 string with `Z`, or epoch milliseconds |
| Local wall-clock time | A time people will read off a clock in a place | Meeting at 09:00 in Berlin, store opening hours, alarm at 07:00 | Local date-time plus an IANA zone name such as `Europe/Berlin` |
| Calendar date | A day, not a moment | Birthday, due date, holiday, hotel check-in day | `YYYY-MM-DD` string or a date type with no time and no zone |

A value that changes class partway along the path is the bug, nearly every time. Write
the class beside each field before reading any formatting code.

*Gate:* every field on the path has a class, and any disagreement between layers is
written down as the candidate cause.

### 2. Fix the representation at each layer

- **Instants** are UTC everywhere except the final formatter, which converts to the
  display zone. Never store "local now".
- **Wall-clock times** keep the zone name, not an offset. `+01:00` is a fact about one
  moment; `Europe/Berlin` is a rule that knows the offset changes in summer, and that
  governments change rules — most of Mexico dropped DST in 2022, and every stored offset
  for a future meeting there became wrong overnight. Compute the instant from local time
  and zone as late as possible.
- **Calendar dates** stay strings or date types end to end. In JavaScript,
  `new Date("2026-03-29")` parses as midnight UTC while `new Date("2026-03-29T00:00")`
  parses as local midnight; both are timestamps, and both shift the day for someone.
  Parse a date-only string into a date type, or keep it as a string.

`references/type-map.md` gives the type to use for each class in JavaScript, Java and
Kotlin, Swift, Python, PostgreSQL and JSON, with each platform's known traps. Read it
before choosing a type.

*Gate:* the API contract says, per field, which class it is and its wire format.

### 3. Decide what "the user's zone" means before formatting

There are at least three zones in play: the device's current zone, the zone in the
user's profile, and the zone the event belongs to. A traveller in Tokyo looking at a
London meeting wants London time labelled as such, or Tokyo time labelled as such —
never an unlabelled conversion. Server code that computes "today" in its own zone (often
UTC) gets the wrong day for anyone far enough from it near midnight.

*Gate:* each screen that shows a time names which zone it renders in, and anything that
computes "today", "this week" or "overdue" names the zone it computes in.

### 4. Compute recurrence and ranges in the event's zone

"Every day at 09:00 in Berlin" is a rule in local time. Adding 86,400 seconds to the
previous occurrence moves it to 08:00 or 10:00 after a clock change. Add calendar days in
the zone instead: `ZonedDateTime.plusDays(1)`, Temporal's `zdt.add({ days: 1 })`, or
`Calendar.date(byAdding: .day, value: 1, to:)` with the calendar's `timeZone` set, all
keep the wall-clock time; adding a fixed duration does not.

For "everything on 29 March", query the half-open range from the start of that day in
the zone to the start of the next day in the zone. A local day can be 23 or 25 hours
long, and in a zone whose clocks change at midnight the day does not start at 00:00 at
all.

*Gate:* no recurrence or day-range code adds a fixed number of seconds to step a day.

### 5. Choose the gap and overlap policy explicitly

A local time inside a spring-forward gap does not exist; one inside a fall-back overlap
happens twice. Each library has a default — java.time moves a gap time later by the gap's
length and picks the earlier offset in an overlap; Temporal's `disambiguation` option
defaults to `'compatible'` with the same behaviour and also offers `'earlier'`, `'later'`
and `'reject'`; Python's `zoneinfo` uses the `fold` attribute. Pick the policy the
product wants (an alarm at 02:30 on a gap day usually fires at 03:30; a billing cut-off
probably wants the first occurrence) and write it down so the test in step 6 asserts it.

### 6. Prove the fix against the hostile set

Run the affected code against every case below, with the zone set by the test rather
than inherited from the machine:

1. A wall-clock time inside a DST gap, and one inside a DST overlap.
2. A zone that changes its clocks at midnight, so local midnight is missing that day.
3. `Pacific/Kiritimati` (UTC+14) and `Etc/GMT+12` (UTC-12 — the POSIX sign is
   inverted, which is itself a trap), so a date is checked at both edges of the world.
4. A half-hour or 45-minute zone such as `Asia/Kolkata` or `Asia/Kathmandu`.
5. 29 February, and "one year after 29 February".
6. A device zone different from the user's profile zone, and a test runner whose own
   zone is neither.

`references/hostile-test-set.md` has concrete 2026 values for each case, how to pin the
zone per runtime and test framework, and the assertion each case should make. Read it
when writing the tests.

*Gate:* the test suite runs the set in CI, on a runner whose zone is not UTC, and fails
on the original bug when the fix is reverted.

## Anti-patterns

**Storing everything as UTC "to be safe".** Correct for instants, wrong for the other two
classes: a future 09:00 meeting stored as UTC becomes 08:00 or 10:00 when the rules move,
and a birthday stored as a UTC midnight is a day early west of Greenwich.

**Fixing the display by adding or subtracting the offset.** It cancels the bug for the
developer's zone on the developer's date and moves it everywhere else. Fix the class, not
the arithmetic.

**`YYYY` in a format pattern.** In Java's `DateTimeFormatter`, ICU and Apple's
`DateFormatter`, `Y` is the week-based year, so the last days of December can print next
year. Use `yyyy` (or `uuuu` in java.time).

**A fixed-format parser without a fixed locale.** On Apple platforms a `DateFormatter`
parsing a wire format needs `en_US_POSIX` as its locale, or a user's 12-hour or
non-Gregorian calendar setting changes what it parses.

**Trusting the test machine's zone.** A suite that passes in UTC proves nothing about
anyone else. Pin the zone per test and run at least once in a zone with DST.

## Output format

```markdown
## Symptom
[What is wrong, for whom, on which dates; the exact value seen and expected.]

## Classification
| Field | Class | Representation at each layer | Where it changed class |

## Cause
[The layer and line where the value was converted wrongly.]

## Fix
[Representation change per layer, the zone each computation now uses, the gap/overlap
policy chosen.]

## Proof
[Hostile-set cases run, the runner's zone, and confirmation the tests fail with the fix
reverted.]
```

## Reference files

- `references/type-map.md` — read at step 2, when choosing types: the type for each class
  in JavaScript, Java and Kotlin, Swift, Python, PostgreSQL and JSON, and each platform's
  known traps.
- `references/hostile-test-set.md` — read at step 6, when writing tests: concrete 2026
  values for every hostile case, how to pin the zone per runtime, and what each case
  should assert.
