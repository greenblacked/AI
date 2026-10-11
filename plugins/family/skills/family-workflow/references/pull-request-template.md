# Pull request template and stage labels

## Contents

- The template
- Stage labels
- Creating the labels
- Using them

A pull request is where a slice meets a reviewer who was not in the thread. The template makes the pull request carry the six artifacts as links and one-line answers, so the reviewer judges the change against its frame and not against the author's account of it. The long form of each artifact stays in `docs/slices/<name>/`; see `references/slice-folder.md`.

## The template

Copy this to `.github/pull_request_template.md`. Replace `<name>` with the slice name in the link, and delete a comment once its section is filled.

```markdown
## Frame

Problem:

Success criterion:

Frame: docs/slices/<name>/frame.md

<!-- The problem and the criterion in one line each. The link is the full frame. -->

## Decision

<!-- The approach in one or two sentences, the alternative that lost, and the hard-to-reverse decision. Link docs/slices/<name>/decision.md. If Architect was waived, say so here with the reason and the risk. -->

## Plan steps

<!-- The ordered steps from docs/slices/<name>/plan.md, one line each with its proof. One commit per step where the plan allows. -->

1.

## Inspect

<!-- One line per success criterion from the frame. Link docs/slices/<name>/inspect.md. -->

- Holds:
- Fails:
- Not assessed:

Go/no-go owner:
Go/no-go verdict: GO | NO-GO

## Launch

<!-- Link docs/slices/<name>/launch.md. If Launch was waived, say so here with the reason and the risk. -->

Path:
Signal:
Rollback:

## Yield

<!-- Filled after release, by editing the description or in a comment. Link docs/slices/<name>/yield.md. -->

Measured:
Next slice:
```

## Stage labels

One label per stage, in the FAMILY page's day-theme colours, so a pull request's label says which stage is open on it.

| Label | Colour | Meaning |
| --- | --- | --- |
| `family:frame` | `#b42318` | The problem and the success criterion are being settled |
| `family:architect` | `#a14a06` | The approach and the hard-to-reverse decision are being settled |
| `family:make` | `#25713a` | The plan is being built |
| `family:inspect` | `#0b6680` | The change is being checked against its frame |
| `family:launch` | `#3348c2` | The release path, signal and rollback are being settled |
| `family:yield` | `#7a35b5` | The outcome is being measured |

## Creating the labels

Run this once per repository, with the GitHub CLI authenticated and the repository as the working directory. `--force` updates a label that already exists, so running it again is safe.

```bash
set -Eeuo pipefail

gh label create "family:frame" --color b42318 --description "FAMILY stage: Frame" --force
gh label create "family:architect" --color a14a06 --description "FAMILY stage: Architect" --force
gh label create "family:make" --color 25713a --description "FAMILY stage: Make" --force
gh label create "family:inspect" --color 0b6680 --description "FAMILY stage: Inspect" --force
gh label create "family:launch" --color 3348c2 --description "FAMILY stage: Launch" --force
gh label create "family:yield" --color 7a35b5 --description "FAMILY stage: Yield" --force
```

## Using them

- Put one stage label on a pull request at a time and move it when the gate passes, so the label is the current stage and not a history.
- A pull request with no `family:yield` label after release is a slice whose Yield has not happened; the label is the prompt to fill `docs/slices/<name>/yield.md` and the template's last section.
- The labels name stages, not verdicts. A `FIX` or `DIVERGED` is routed by `family-relay` and recorded in the stage's file; the label stays on the stage that returned it.
