# Breaking changes that do not look like breaks

Read this when deciding whether a change is breaking, or when a change breaks callers in a
way the diff does not show. The organising question throughout: does a caller who changed
nothing behave differently, fail, or receive a different result after upgrading?

## Contents

- [The silent-break catalogue](#the-silent-break-catalogue)
- [Additive changes that are not additive](#additive-changes-that-are-not-additive)
- [The deprecation sequence](#the-deprecation-sequence)
- [Wording each kind of break](#wording-each-kind-of-break)

## The silent-break catalogue

| Change | Why it breaks a caller | What the entry must say |
| --- | --- | --- |
| A default value moved | An untouched caller that relied on the default gets different behaviour with no signal at all | The old default, the new one, and the explicit setting that restores the old behaviour |
| Validation tightened on an existing field | Input accepted yesterday is rejected today, and the caller's data has not changed | Which inputs are now rejected, and how a caller finds out whether theirs are among them |
| A limit, quota, page size or timeout changed | Callers sized their retries, pagination or batches around the old number | Old and new values, and which client-side setting to revise |
| Ordering became unspecified or changed | Code that relied on incidental ordering now produces different output without erroring | Whether ordering is guaranteed at all now, and the explicit sort to request |
| An error code, class or message changed | Callers branch on error identity whether or not they were told to | The old and new identity, and the stable field to branch on going forward |
| Nullability changed in either direction | A field that was always present becoming optional breaks consumers that do not check | Which field, which direction, and the version from which it applies |
| A numeric type widened or a precision changed | Serialisation into a narrower client type truncates or overflows silently | The new range and precision, and the client types affected |
| Timezone, encoding, locale or rounding behaviour changed | Results differ with no error anywhere in the stack | What now applies, and how to detect the difference in existing stored data |
| An identifier format changed | Callers store, index, compare or length-limit identifiers | The new format and length, and whether existing identifiers remain valid |
| A dependency's transitive behaviour changed | The caller sees the change without any change in your API | Name the dependency and the behaviour, since nothing in your own surface explains it |
| Retry, idempotency or at-least-once semantics changed | Duplicate or dropped effects appear under failure, not under test | The new guarantee, stated exactly, and what a caller must now make idempotent |
| A minimum runtime, platform or database version raised | The upgrade simply fails for somebody who changed nothing | The new floor and what happens below it |
| Permissions or scopes required for an existing operation | Existing credentials stop working for an unchanged call | The new scope, and how to grant it before upgrading |
| Wire or storage format version bumped | Downgrade stops working even when the upgrade succeeds | Whether the format is backward readable, and what this does to rollback |

## Additive changes that are not additive

Adding is safe only when every consumer tolerates the addition. Check each of these before
filing a change as a minor.

- **A new response field** breaks consumers that validate strictly, that deserialise into
  a closed type, or that hash or sign the whole payload.
- **A new enum value** breaks consumers with exhaustive matching, which is most typed
  clients and every switch with no default branch.
- **A new optional request field with a non-neutral default** changes behaviour for
  callers who do not send it, which makes it a default change rather than an addition.
- **A new event type on an existing topic** breaks consumers that fail on unknown types
  rather than skipping them.
- **A new required configuration key**, even with a default, breaks any deployment whose
  configuration is validated against a fixed schema.
- **A new table, column or index** is additive to the application and not to the deploy:
  it has a lock profile, a migration order and a rollback consequence. The sequencing
  belongs to `db-migration`; the notes must still say that an upgrade step exists.

## The deprecation sequence

A deprecation that skips a step becomes a break that was technically announced.

1. **Announce** in the release that introduces the replacement, never later. Name the
   replacement in the same sentence; a deprecation with no replacement is a removal with
   a waiting period.
2. **Warn where it is observed.** A log line at the call site, a response header, a
   compiler or linter warning. A note in a changelog reaches the person reading the
   changelog, who is rarely the person whose code calls the deprecated path.
3. **Give a period stated in versions and in time**, both, because consumers upgrade on
   different clocks. State the version in which it stops working.
4. **Measure usage before removing.** If the deprecated path still carries meaningful
   traffic at the deadline, the choice is to extend deliberately with a new date or to
   remove and accept the breakage — not to remove quietly and find out from support.
5. **Remove in a major**, referencing the version that announced it, so a reader arriving
   late can find the migration without searching.

## Wording each kind of break

- **Lead with the observation, not the cause.** "Requests without a tenant header are now
  rejected with 400" tells a reader whether they are affected. "Refactored header
  validation" does not.
- **Narrow the audience in the first line.** Most readers should be able to rule
  themselves out immediately; the ones who cannot will read the rest carefully.
- **Give before and after.** Two short lines beat a paragraph describing the difference,
  and they survive translation into a reader's own codebase.
- **State the interim behaviour explicitly.** Whether the old path errors, warns or
  silently falls back in this version decides whether the reader can upgrade now and
  migrate later, which is the question they are actually asking.
- **Say when there is no migration.** A removal with no replacement is a legitimate
  outcome and a reader can plan around it; discovering the absence themselves costs a day.
