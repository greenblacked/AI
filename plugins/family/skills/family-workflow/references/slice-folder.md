# The slice folder

## Contents

- Layout
- Naming a slice
- How the files are used
- The templates
- Keeping the command and this file in step

## Layout

One slice gets one folder, `docs/slices/<name>/`, in the repository the slice changes, with one file per stage artifact. The folder is how a handoff stops being a message in a thread: the next stage's owner opens a file instead of asking for a summary.

```text
docs/slices/<name>/
  frame.md       Frame      the one-page frame, with the framer verdict
  decision.md    Architect  the design note and the ADR, or the written waiver
  plan.md        Make       the ordered change plan, one line per step with its proof
  inspect.md     Inspect    criterion-by-criterion evidence and the go/no-go line
  launch.md      Launch     release path, migration, signal, rollback, or the written waiver
  yield.md       Yield      the retro, filled after release
```

The names are fixed so that a person, a script and a stage agent all find the same file. Commit the folder with the change it describes; a frame that lives only in a ticket is gone when the ticket is.

## Naming a slice

A slice name is kebab-case: lowercase letters and digits joined by single hyphens, no leading or trailing hyphen, at most 48 characters. `export-invoices-csv` is a name; `Export Invoices`, `../x` and `a/b` are not.

The rule is strict because the name becomes a path. Anything with a slash, a dot, a space or an uppercase letter is refused rather than cleaned up, since a cleaned-up name is a different name from the one the person typed and the folder would not match the pull request that cites it.

## How the files are used

- The main agent writes the files. The stage agents have no editing tools: they return a report and the main agent puts the artifact in the file, so the file holds what the owner accepted and not what an agent proposed.
- The first line of every file is the stage's `First question` from `stages.md`, copied and not reworded. It is what the stage answers before anything else once the handoff reaches it.
- A stage that is waived keeps its file. Write the waiver in it, with the reason and the risk; only Architect and Launch may be waived. A missing file reads as a skipped stage, a waiver reads as a decision.
- `inspect.md` ends with the go/no-go line, answered once by the Inspect owner. `launch.md` takes it as input and does not remake it.
- `yield.md` stays empty until the release has produced something to measure. An empty `yield.md` on a merged slice is the missing Yield, visible in review.
- Each file names its owner on the line under the title, so a stalled stage is a named person and not a vague one.

## The templates

Headings only; the content comes from the stage, and the section names follow the verdicts and returns of the stage agents so a report can be pasted under the matching heading.

`frame.md`:

```markdown
First question: did the last slice change the problem?

# Frame: <name>

Owner:
Verdict:

## Profile and depth

Profile: solo | developer | QA | team
Depth: light | full

## Problem

## Users

## Success criterion

## Smallest slice

## Out of scope

## Constraints

## Open questions

## Not established
```

`decision.md`:

```markdown
First question: does the approach survive the constraints?

# Decision: <name>

Owner:
Verdict:

## Approach

## Alternatives

## Boundaries

## Interfaces

## Data

## Failure modes

## Hard-to-reverse decision

### ADR

Status:
Context:
Decision:
Consequences:

## Security surface

## Waiver

Reason:
Risk:

## Not assessed
```

`plan.md`:

```markdown
First question: which step can be shown working first?

# Plan: <name>

Owner:
Verdict:

## Steps

1. files, change, proof

## First demonstrable step

## Acceptance check

## Reversible at

## Not assessed
```

`inspect.md`:

```markdown
First question: does the change meet the success criterion?

# Inspect: <name>

Owner:
Verdict:

## Criteria

- criterion, HOLDS | FAILS | NOT ASSESSED, evidence locator, check run

## Checks run

## Findings

## Observations

## Not assessed

## Go/no-go

Go/no-go: GO | NO-GO
Owner:
Residual defects, each with its risk and its owner:
```

`launch.md`:

```markdown
First question: is there a way back?

# Launch: <name>

Owner:
Verdict:

## Release path

## Migration

## Signal

## Rollback

## Communication

## Residual defects shipping

## Gaps blocking launch

## Waiver

Reason:
Risk:

## Not assessed
```

`yield.md`:

```markdown
First question: what did the criterion measure?

# Yield: <name>

Owner:
Verdict:

## Measured

## Keep

## Change

## Next slice

## Cost

## Not assessed
```

## Keeping the command and this file in step

The `/family:family` command writes these files from the same templates, carried in its own body because a command cannot name a path inside another component and rely on it resolving after install. A change to a template here is a change to the command, and the other way round; edit both in one commit. The pull request that carries a slice is described in `references/pull-request-template.md`, which links to `docs/slices/<name>/frame.md`.
