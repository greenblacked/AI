---
name: developer-workflow
description: "Run FAMILY as a developer: own Frame, Architect, Make and Yield in depth, and hand Inspect and Launch to someone independent rather than marking your own work. Covers the developer's loop through the stages, what to hand a reviewer, and what to expect back. Use this skill whenever a developer is choosing how to work through a feature. Triggers include a developer's day-to-day process, a feature from ticket to review, preparing a change for review, or \"how should I work as a developer\" — including phrasings like \"my workflow for a feature\" or \"what do I do before I ask for review\". Do not use it for the stage definitions themselves (family-workflow), a solo developer (solo-development), a QA role (qa-workflow), or a whole team's process (team-workflow)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*)
---

# Developer workflow

A developer's run of FAMILY is finished when the frame and the architecture are decided well enough to build, the change is built in reviewable steps, and Inspect and Launch were handed to someone independent with what they need to judge it.

The failure is that a developer treats the stages they own as obvious and the stages they hand off as someone else's problem. Frame and Architect get skipped because the ticket "already says what to do", so the change is built on a problem nobody checked. Inspect becomes "it works on my machine", because the author read their own diff. Launch becomes a merge, because the release is the platform's job. Each stage has an owner for a reason; a developer owns four of them and hands two, and the handoff is part of the work, not the end of it.

## Scope

Use for: a developer working a feature or a fix inside a team, from the ticket to the review, and the handoff to the reviewer and the release owner.

Do not use for: the stage definitions themselves, which are `family-workflow`; a solo developer with no team to hand off to, which is `solo-development`; the QA role, which is `qa-workflow`; or setting up the whole team's process, which is `team-workflow`.

## What the developer owns

| Stage | Owned or handed | What it means here | Agent and what it gets |
| --- | --- | --- | --- |
| Frame | Owned | Read the ticket, fill the gaps in the problem and the success criterion | `framer`: the ticket and what you know of the users |
| Architect | Owned | Decide the approach and record the hard-to-reverse choice | `architect`: the frame |
| Make | Owned | Plan the steps with `maker`, then build them in small commits | `maker`: the frame and the design note |
| Inspect | Handed | Give `inspector` and `code-review` the frame and the diff, not a summary; the Inspect owner returns the go/no-go | `inspector`: the success criterion and the diff; `code-review`: the diff |
| Launch | Handed | Get the launch plan from `launcher`, then give the release owner the plan, not the diff | `launcher`: the go/no-go, the change and the deploy target |
| Yield | Owned | Write the retro; the reviewer's findings are part of the input | `yielder`: the success criterion and the measurement |

Read `references/dev-loop.md` for the loop, what a good handoff to review contains, and what to do with what comes back.

## Workflow

### 1. Turn the ticket into a frame

A ticket is a request, not a frame. Hand it to `framer` and add the problem, the user and the observable success criterion, and name the smallest slice. If the ticket already says all four, say so and move on; if it does not, ask before building. Record the depth for this slice, light or full, in the frame.

### 2. Decide the approach before the first commit

Give `architect` the frame, and name the approach, the boundary and the one hard-to-reverse decision. For most slices this is a paragraph; for a schema or a public interface it is an ADR. Hand the interface detail to `api-design` or `schema-design` rather than inventing it in the build.

### 3. Plan the change, then build it

Give `maker` the frame and the design note and take back ordered steps, each with its proof. Then build in those steps, one purpose per commit, keeping the tree working. A step that turns out not to work is a signal to return to Architect, not to improvise. Before review, have `maker` check the diff against the plan.

### 4. Hand the change to review properly

The handoff is the frame's success criterion, the plan, and the diff — not "please review". Give `inspector` the criterion and the diff for evidence on each criterion, and `code-review` the diff for severity-ranked findings. Name what you are unsure about. A reviewer who knows the intent reviews the change; a reviewer given only a diff reviews the diff. Ask the Inspect owner — QA where QA is present, otherwise your reviewer — for the go/no-go that closes Inspect; it is not yours to give.

### 5. Fix findings, then hand the launch

Address the reviewer's findings, then get the launch plan from `launcher` before asking the release owner: give it the go/no-go with its residual defects, the change and the deploy target. Pass the plan to the release owner: the path, the signal, the rollback. The developer usually does not own the release, but owns telling the owner what to watch.

### 6. Yield

Give `yielder` the success criterion and the measurement, then write the short retro. What did the frame get right, what did the approach miss, and what is the next slice. A developer who never yields keeps making the same architectural mistake.

## Anti-patterns

**The ticket is the frame.** Building exactly what the ticket says without checking the problem, so a wrong request is delivered perfectly.

**Architecture in the first commit.** Discovering the approach while writing code, so the boundary and the interfaces are whatever the first file happened to need.

**One big commit.** The whole slice in one commit, unreviewable and unrevertible, usually with a message like "implement feature".

**"Please review".** A handoff with no frame, no plan and no stated uncertainty, which produces a review of the diff's style rather than its correctness.

**Review as a formality.** Merging on approval without addressing the findings, so the review costs a round trip and changes nothing.

**The merge as launch.** No signal, no rollback, and the release owner finds out from the deploy, not from you.

## References

- `references/dev-loop.md`: read for the loop, what to put in a review handoff, how to work with `maker`'s plan, and what to do with findings and a failed launch.
