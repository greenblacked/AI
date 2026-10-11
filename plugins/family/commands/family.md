---
description: Start a FAMILY slice - validate the slice name, have framer frame the request, write its frame.md and the five other stage files as empty templates under docs/slices, then print the verdict and the next hop.
argument-hint: '[slice-name] [request]'
allowed-tools: Agent(family:framer), Write, Glob, Bash(git rev-parse:*)
disable-model-invocation: true
---

Start the Frame stage for one slice and leave a folder the later stages can fill. This
command runs Frame and nothing after it: the accepted slice, the approach and the build
are decisions for the main conversation, and a command that ran them would make those
decisions for it.

`$0` is the slice name. The request is everything in `$ARGUMENTS` after the first word.

## 1. Validate the name before it touches a path

The name becomes a directory, so check it first and build no path from it until it
passes. A valid name is lowercase letters and digits joined by single hyphens, with no
leading or trailing hyphen, at most 48 characters: `export-invoices-csv`. Refuse
anything else, including an empty name, uppercase, spaces, dots, slashes, underscores and
a name starting with a hyphen. Do not clean the name up and continue; a cleaned name is a
different name from the one the person typed. Say what was wrong and show a valid
example, then stop without writing anything.

## 2. Find the folder and check for an existing frame

Run `git rev-parse --show-toplevel` and use its output as the repository root. If it
fails, use the working directory. The slice folder is `docs/slices/` followed by the
validated name, under that root.

Glob the slice folder for the six file names. If `frame.md` exists, stop: say which file,
that this command does not overwrite a frame, and that the person can edit it by hand or move it
aside and run the command again. Do not read it into the framer's brief.

## 3. Have framer frame the request

If the request is empty, skip to step 4 and create every file except `frame.md`. Say that
no frame was made.

Otherwise delegate to `framer`, which the installed plugin names `family:framer`, with the request exactly as typed, in the person's words,
plus any constraint or user the person already named in it. Add nothing of your own: a
paraphrase carries your reading of the request into the frame as a premise. The agent
reads and reports; it does not write, so the file is yours to write.

Read the first line of its report. It must be exactly one of `FRAMED`, `NEEDS INPUT` or
`NOT FRAMED`. A report with no verdict, with a verdict from another stage, or with two
verdicts is a question and not a result: print it, write nothing, and ask the person
whether to run framer again.

## 4. Write the files

Write only files that the Glob in step 2 did not find, and skip an existing one without
comment on its content. Writing a file creates the folder. Write nothing in this step when the
verdict is `NEEDS INPUT` or `NOT FRAMED`: a frame that is not a frame must not sit in
the folder where a retry would be refused, so print the report and go to step 5.

On `FRAMED`, write `frame.md` from the template below. Put the verdict on the `Verdict:`
line and the framer's sections verbatim under the headings of the same name, as `##`
headings. Leave `Owner:` empty and keep the `Profile:` and `Depth:` lines exactly as the
template gives them, options listed: they are the person's choices, and the stage
reference says the depth is written in the frame so it can be challenged.

Then write the other five files as the empty templates below. In all six files, including
`frame.md`, replace `<name>` in the title with the slice name. The first line of each is the stage's first question from the
stage reference; keep it as written.

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

## 5. Print the result and stop

Print, in this order: the verdict word, the paths written and the paths skipped because
they already existed, and the next hop for that verdict. Then stop. Do not start
Architect, and do not offer to.

| Verdict | Next hop |
| --- | --- |
| `FRAMED` | The person accepts or changes the slice, then `architect` takes `frame.md`. If Architect is waived, write the waiver in `decision.md` with the reason and the risk, and the next stage is `maker`. |
| `NEEDS INPUT` | The person answers the open questions, then run this command again with the answers in the request. Nothing was written, so the name is free. |
| `NOT FRAMED` | The person decides whether to restate the request, split it or drop it. Nothing was written. |
| no request given | The folder holds the empty templates. Run this command again with a request to frame it; the files already there are left alone. |

The routing for every later verdict is the `family-relay` skill's table; this command
does not read or apply it.
