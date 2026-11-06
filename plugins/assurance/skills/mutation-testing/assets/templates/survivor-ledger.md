# Survivor ledger

One diff-scoped mutation run. Fill in every field; delete the guidance in brackets.

## Scope

- Base revision: [commit or branch]
- Head revision: [commit or branch]
- Mutation tool and version: [name]
- Mutant count: [number]
- Run time: [minutes]

## Survivors

One row per survivor on a changed line.

| Location | Mutator | Verdict | Action | Owner |
| --- | --- | --- | --- | --- |
| [file:line] | [e.g. `>` to `>=`] | [untested branch / missing assertion / equivalent / accepted] | [test added / suppressed with reason / accepted] | [person or team] |

## Results on changed lines

| Status | Count |
| --- | --- |
| Killed | [n] |
| Survived | [n] |
| No coverage | [n] |

## Tests added

| Test | Mutant it kills |
| --- | --- |
| [test name and file] | [location and mutator] |

## Gate

[What CI enforces on changed code, for example the threshold or the rule that a survivor
without a verdict fails, and the scheduled full run if one exists.]
