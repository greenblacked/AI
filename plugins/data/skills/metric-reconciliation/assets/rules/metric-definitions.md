---
paths:
  - "models/**/*.sql"
  - "models/**/*.yml"
  - "metrics/**/*.yml"
---

# Defining a metric

Keep each metric defined once, because two definitions with one name get compared again
and disagree again. The reasoning is in the `metric-reconciliation` skill; this rule only
holds the line.

- Give every definition one named owner, a version, the grain, the day boundary and time
  zone, the currency or units, and the inclusion and dedupe rules. Fill in
  `metric-definition.md` from the skill's templates when the metric has no card yet.
- Before adding a metric, search `models/` and `metrics/` for its name and its numerator.
  If a definition exists, change that one.
- A change that adds a second definition of an existing metric renames or retires the
  duplicate in the same change, and says which readers it moved.
- Leave a field blank and say so rather than guessing it.
