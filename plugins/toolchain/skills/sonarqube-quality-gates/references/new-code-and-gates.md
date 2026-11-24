# New code and gate conditions

Confirm option names and default conditions against the official documentation for the
pinned server; both have changed between releases and differ by edition.

## Contents

- The new-code options
- Conditions worth keeping
- Changing a gate safely

## The new-code options

| Option | New code is | Fits | Cost |
| --- | --- | --- | --- |
| Previous version | Everything since the last version change recorded by an analysis | Release trains with a version bump | Nothing is judged until the version property changes; forgetting to bump it makes new code grow forever |
| Number of days | The last N days | No clear baseline | Old problems age out and stop being reported |
| Reference branch | Whatever differs from the named branch | Trunk-based work, pull requests | The reference branch must exist in the runner's clone and be analysed |
| Specific analysis or date | Everything after a chosen point | Adopting the gate on a legacy project | Must be reset deliberately |

Per-branch or per-project overrides exist in some editions; check before assuming one
setting covers every branch. If new code looks wrong, first rule out a shallow clone (see
the main procedure) before changing the option.

## Conditions worth keeping

Keep conditions on new code that a developer can fix in the change that triggered them:

- No new issues above an agreed severity, or a rating condition on new reliability,
  security and maintainability.
- Security hotspots on new code reviewed, with a named reviewer role.
- Coverage on new code at a threshold the team set deliberately.
- Duplication on new code under a stated limit.

Prefer a gate with few conditions that people believe over one with many that gets
bypassed. A coverage condition applies to the lines that changed, so a small change to an
untested file needs tests for those lines only; say so to the team, since the surprise
produces exclusions.

## Changing a gate safely

1. Copy the built-in gate rather than editing it where the edition allows; built-ins are
   usually read-only or change with upgrades.
2. Assign the new gate to one project first and observe a few analyses.
3. Record the reason for each threshold in the change record, with who agreed.
4. Roll to the remaining projects by group or by the API, then retire the old gate.

A threshold lowered in the same change that fails it is the pattern to refuse; require the
reason and a second approver.
