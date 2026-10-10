# The developer loop

## Contents

- The loop, stage by stage
- Filling a ticket into a frame
- Working with the maker's plan
- The review handoff
- What to do with findings
- Handing the launch

## The loop, stage by stage

1. **Frame** — read the ticket, fill the problem, user and success criterion, name the slice; `framer` takes the ticket and returns the frame.
2. **Architect** — `architect` takes the frame; decide the approach, the boundary and the hard-to-reverse choice; hand interface and data detail on.
3. **Make** — plan with `maker`, then build the steps in small commits, one purpose each.
4. **Inspect** — hand the frame, the plan and the diff to `inspector` and `code-review`; the Inspect owner gives the go/no-go.
5. **Launch** — get the launch plan from `launcher`, then hand it to the release owner.
6. **Yield** — `yielder` takes the criterion and the measurement; write the retro, with the findings as part of it.

A developer owns 1, 2, 3 and 6, and hands 4 and 5. The handoffs are not optional; they are what makes the change reviewable and the release safe.

## Filling a ticket into a frame

A ticket usually has one or two of the four. Add the rest:

| The ticket has | Add |
| --- | --- |
| A feature description | The problem it solves and for whom |
| A user story | The observable success criterion |
| A bug report | The reproduction and the expected behaviour |
| A "we should" | The smallest slice that delivers value |

If the ticket already states all four, say so in one line, still hand it to `framer` as the second reader, and build. If it states none, ask before writing code; a wrong frame is the most expensive thing to discover at review.

## Working with the maker's plan

`maker` returns ordered steps, each with the files it touches and a proof. Use it as the commit sequence:

- One step, one commit. If a step needs two commits, it was two steps.
- Run the step's proof before moving on; a step whose proof fails is not done.
- When reality contradicts the plan, stop and return to Architect with the concrete constraint. Do not improvise the architecture in the build.

The plan is also what the reviewer reads. A diff that follows a stated plan is far easier to review than a diff that arrives with only a description.

## The review handoff

Give `inspector` and `code-review` four things:

1. **The frame** — the success criterion, so they review against intent.
2. **The plan** — the steps, so they can see the intended shape.
3. **The diff** — the change itself, not a summary of it. `inspector` returns each success criterion as holding, failing or not assessed, with its evidence; `code-review` returns the findings ranked by severity.
4. **The uncertainty** — what you are unsure about, and where you would look first.

"Please review" is not a handoff. A reviewer without the intent reviews style; a reviewer with it reviews correctness.

## What to do with findings

The go/no-go comes from the Inspect owner, QA where QA is present and otherwise the reviewer, not from you; it is what `launcher` takes as its input.

- Fix the blocking findings and the cheap ones.
- For a finding you disagree with, reply with the reason rather than silently ignoring it.
- A finding you defer becomes a known issue with an owner, not a comment that scrolls away.
- Re-run the checks after fixing; a fix that breaks a test is a new finding.

The review is not a gate to pass but a second reading of the change. A developer who treats it as a formality pays the round trip and gets nothing.

## Handing the launch

The developer usually does not own the release, but owns the launch plan the owner needs. Get it from `launcher` first, giving it the go/no-go, the change and the deploy target; it returns the plan, or the path, signal or rollback that is missing:

- **Path:** how this reaches users.
- **Signal:** what to watch to know it worked.
- **Rollback:** how it comes back, and who decides.
- **Risk:** any residual defect from the go/no-go shipping anyway, named with its risk and owner.

Hand it to the release owner before the merge, not after. A release owner who learns the plan from the deploy cannot prepare for the rollback.
