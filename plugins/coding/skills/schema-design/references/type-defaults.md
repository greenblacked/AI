# Type defaults

Read this when picking a concrete type for a point in time, money, an identifier, or a value that might need retiring. Each row is a default, not a universal rule — the point is that the choice is made on purpose, and that anything version- or engine-specific gets checked against the target's own current documentation rather than assumed.

## Contents

- [Points in time](#points-in-time)
- [Money](#money)
- [Identifiers](#identifiers)
- [Values that may need retiring](#values-that-may-need-retiring)
- [Free text](#free-text)

## Points in time

Use a timezone-aware timestamp type — `timestamptz` in PostgreSQL, `TIMESTAMP` in MySQL, where `TIMESTAMP` is stored and compared in UTC and `DATETIME` carries no timezone at all.

MySQL's `TIMESTAMP` stores seconds since the epoch in a signed 32-bit integer, so it cannot represent a value past `2038-01-19 03:14:07` UTC — the server's own source names this bound `TIMESTAMP_MAX_YEAR` and `TYPE_TIMESTAMP_MAX_VALUE` in `include/my_time.h`. A row that needs a date beyond that — a far-future renewal, expiry or scheduled event — belongs in `DATETIME` instead, kept in UTC by convention, since `DATETIME` itself carries no timezone to enforce that.

A naive timestamp is correct for exactly the timezone the person who wrote the migration was sitting in. It stays invisible as long as every reader and writer share that timezone, and breaks the moment one does not — a nightly batch job that runs at a different offset than the web tier, a user in a second country, a daylight-saving transition that silently duplicates or drops an hour. The fix, once the bug is found, is a full backfill against a column that never recorded which timezone its values meant.

Store and compare in UTC; convert only at display time, in the layer that knows which timezone the reader is in.

## Money

Store an integer count of the currency's minor unit (cents, pence, the smallest denomination the currency actually has) or a fixed-point numeric type with an explicit scale (`numeric(12,2)` in PostgreSQL, `DECIMAL(12,2)` in MySQL). Never a floating-point type.

A float represents most decimal amounts inexactly, and the error is silent until enough transactions accumulate that a reconciliation stops balancing. By the time anyone notices, the fix is a data audit against a column that has been wrong since the day it was created. An integer minor-unit column is exact by construction and the arithmetic is ordinary integer arithmetic; a fixed-point numeric type is exact for the same reason and reads more naturally when a currency's minor unit varies.

Whichever is chosen, store the currency alongside the amount rather than assuming one currency for the whole table — a column that is silently always USD is a decision nobody wrote down.

## Identifiers

Default to a `bigint` identity column as the primary key. It is small, it sorts and indexes cheaply, and every join against it is a plain integer comparison.

Move away from it only when the query list actually requires a client-generated or cross-system identifier — a row created offline before it has a server round trip, or a key that has to merge across systems that do not share a sequence. When that applies, prefer a generation scheme that sorts close to insertion order over one that is fully random. A fully random key scatters inserts across the entire width of the index; once the table is larger than the buffer cache, every insert becomes a cache miss on a page nothing else is touching, and the same scattering fragments range scans that would otherwise read sequentially.

The exact function name and its availability are version- and engine-specific and change over time. Check the target database's own current documentation for what it offers before writing the generator into a migration — do not carry a specific function name forward from a different project or an earlier version without checking it still applies.

## Values that may need retiring

Prefer a lookup table with a foreign key over a native enumerated type whenever a value might need to be removed, renamed, or reordered without a schema migration. Whether an engine's native enum type supports removing or reordering a value, and at what cost, differs by engine and by version — check the target's current documentation before relying on a specific behaviour. A lookup table sidesteps the question entirely: removing a value is a row delete (once nothing references it), adding one is a row insert, and the foreign key gives you the same referential guarantee an enum's implicit closed set of values does.

Reserve a native enum type for a value set you are confident will never need to be edited except by a full migration — an HTTP method, for instance, not a status field a product manager will want to extend next quarter.

## Free text

Use an unbounded text type by default (`text` in PostgreSQL, `TEXT` in MySQL, or a large `VARCHAR` where the engine has no unbounded type). Add a length bound only when it reflects a real business rule — a display name capped for a UI reason, a code with a fixed format — not as a habit inherited from an engine that once made bounded columns cheaper. An arbitrary bound with no business reason behind it is a migration waiting for the day someone's legitimate input is one character too long.
