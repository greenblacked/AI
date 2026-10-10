# The round protocol

## Contents

- The inspector brief
- What the report must contain
- The fix packet
- The finding ledger
- Ending a round

## The inspector brief

Each round, a new inspector context gets:

- **The success criteria**, copied from the frame, one per line. The inspector checks intent, not only tests.
- **The change**: the diff or the changed paths, and the base it is measured against.
- **The commands** the repository has for checking, if any, and the **Author** line: "repository owner", or the named contributor.
- **The rule**: it reads and reports, and does not fix. An inspector that can write fixes what it was asked to assess, and the assessment is lost.

It does not get a previous round's report, findings or verdict. Independence is the point: an inspector told what the last one found looks for that, and finds nothing else.

## What the report must contain

This is the `inspector` agent's own return block; the brief does not ask for a different shape.

```text
PASS | FIX | STOP

### Criteria
- <success criterion> — HOLDS | FAILS | NOT ASSESSED — evidence: <locator> — check run: <command, or "read only">
  (for FAILS also: consequence: <...> — fix: <smallest>)
### Checks run
### Observations (hand to code-review)
### Not assessed
```

`PASS` needs every criterion to hold with evidence. A criterion the inspector could not check, including a check it was not allowed to run on a change the owner did not write, is `NOT ASSESSED` and is named in the report. A report that implies full coverage when it did not have it is worse than a short one.

`FIX` means at least one criterion fails or is not assessed: the failures are for the builder, the gaps for the owner to run. Observations are unranked defects outside the criteria. Severity-ranked review of the diff, with nits named as nits, is `code-review`; use it for the Inspect pass on the diff.

## The fix packet

Build it from the `FAILS` lines, one packet entry per line, taking the fix from the line itself. The builder receives three lines for each and nothing else:

```text
Problem:   <the failure and its consequence, one sentence>
Evidence:  <the line's evidence locator, which the builder can open>
Fix:       <the line's fix: smallest change that would make the criterion hold>
```

The fixer runs on a mid tier. It applies the fix and reports what it changed. It does not receive the criteria list, the observations or the rest of the report, so it has no room to widen the change.

## The finding ledger

The coordinator, not the inspector, keeps this across rounds:

```text
| Round | Criterion | Locator | Finding (short) | Outcome of the fix |
```

One row per `FAILS` line per round. It is how a repeat is seen, since no inspector remembers the one before.

## Ending a round

- `PASS`: stop and hand the report to the Inspect owner for the go/no-go.
- `FIX` with new `FAILS` lines only: send the fix packet, then start a new inspector. Criteria that were `NOT ASSESSED` go to the owner to run.
- `FIX` with a `FAILS` line already in the ledger: halt; see the recurrence reference.
- `STOP`: the inspector could not do its job (no checkout it may read, no criteria). Bring it to the person who owns the slice; do not start another round on the same inputs.
