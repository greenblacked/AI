# Restructurings that cannot land in one commit

## Contents

- [Choosing a strategy](#choosing-a-strategy)
- [Parallel change](#parallel-change)
- [Branch by abstraction](#branch-by-abstraction)
- [Facades and deprecation windows](#facades-and-deprecation-windows)
- [Keeping the trunk green](#keeping-the-trunk-green)
- [Sequencing and stopping](#sequencing-and-stopping)

## Choosing a strategy

| The change | Strategy | Why not the others |
| --- | --- | --- |
| A data shape, a field, a schema or an API contract that readers and writers share | Parallel change: expand, migrate, contract | The three phases are each independently shippable and only the last is irreversible, so a mistake is caught while both shapes still work. |
| Swapping one implementation of a well-bounded capability for another | Branch by abstraction | It keeps one code path in production at a time and makes the switch a configuration change rather than a merge. |
| A rename or move of a widely imported public symbol | A delegating facade with a deprecation window | Doing it in one commit conflicts with every open branch, and the conflict resolution is where other people's changes get reverted. |
| Splitting a module that half the codebase imports | Re-export from the old path, migrate callers, then remove | Callers move on their own schedule, so no single pull request touches two hundred files. |
| A genuine rewrite, where behaviour will differ | None of these — this is not a refactor | Plan it as a migration with an explicit behaviour delta, a rollback and a cutover, not as a cleanup. |

## Parallel change

Three phases, each landing separately.

**Expand.** Add the new shape beside the old. Writers write both; readers still read the old. Nothing depends on the new shape yet, so this phase is risk-free and revertible.

**Migrate.** Move readers to the new shape, a few at a time, each in its own commit. Keep writing both. This is the longest phase and the one that can safely pause — if the work is dropped here, the system still works.

**Contract.** Stop writing the old shape and delete it. Only do this once you can demonstrate no reader remains: search the codebase, check telemetry on the old field's read path, and wait out any client you do not deploy yourself. This is the irreversible phase and it deserves its own review.

For persisted data the same three phases apply, with the migration of existing rows as a separate backfill; a schema column is added nullable, populated, then made required, and the "make it required" step comes after the backfill has completed and been verified.

## Branch by abstraction

1. Introduce an interface in front of the existing implementation, with the existing implementation behind it. Behaviour is unchanged and this lands on its own.
2. Move callers to the interface, in separate commits.
3. Build the new implementation behind the same interface, merged to trunk but not selected — it is dead code until a flag selects it, which is exactly what makes the work incremental.
4. Switch traffic over by flag, starting with a fraction where the system allows it.
5. Delete the old implementation, then the abstraction if it has no other purpose. An interface with one implementer left behind is a cost with no return.

The flag is the rollback. Keep the old path intact and exercised until the new one has run a full business cycle, and give the flag an owner and a removal date, because a permanent flag doubles the paths every future change must consider.

## Facades and deprecation windows

Where a name is widely used, keep it working while the callers move:

- The old name delegates to the new one and does nothing else. No logic in a facade, ever, or the two paths diverge.
- Attach the deprecation mechanism the language offers — a warning, an annotation, a lint rule — so callers find out without being told individually.
- Write the removal date in the deprecation message. A deprecation with no date is permanent, and the codebase accumulates two names for everything.
- For a published API, the window is a release cycle and the removal is a major version.

## Keeping the trunk green

- Merge to trunk at least daily. A branch open for two weeks is accumulating conflicts faster than value, and the conflict resolution is where regressions enter.
- Every intermediate state must be shippable. If the trunk only works once all six commits have landed, the sixth commit is the one that will be reverted for an unrelated reason.
- Do not let a reformatting or import-sorting pass ride along. It expands every diff, buries the substantive lines, and makes `git blame` useless on the file; add the formatting commit to the blame-ignore list.
- Run the suite on every commit, not on the branch tip. A green tip over six red intermediate commits is six broken bisect points.

## Sequencing and stopping

Order the work so each step reduces the cost of the next: rename for accuracy, then extract, then move, then split, then replace conditionals. Doing it in the other order means each step churns lines the previous one already touched, and the review cost is paid twice.

Decide the stopping point before starting, in writing, and record the smells you are deliberately leaving. The failure mode of a large refactor is not doing it badly; it is doing it indefinitely, until a reorganisation or a deadline strands the branch half-applied and the codebase carries both shapes for years.
