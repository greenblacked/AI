# The four profiles

The stages never change. A profile is the role running them; the depth is a separate choice, light or full, made for each slice and written in the frame. Say which profile you are running and at what depth — a run that mixes profiles by accident is the failure this file exists to prevent.

Each profile has its own skill with the full procedure. Read this file to choose one; read the skill for how to run it.

| Profile | The role running the stages | Stages it owns | Skill |
| --- | --- | --- | --- |
| Solo | one person | all six | `solo-development` |
| Developer | one developer inside a team | Frame, Architect, Make, Yield; hands Inspect and Launch | `developer-workflow` |
| QA | the QA role | Inspect in depth, including the go/no-go; pushes acceptance back into Frame and Architect | `qa-workflow` |
| Team | the whole team | all six, each with a named owner and a handoff contract between each | `team-workflow` |

- **Solo** — the missing second opinion is the problem; the stage agents replace it. Read `solo-development`.
- **Developer** — the ticket is not a frame, and review is not a formality. Read `developer-workflow`.
- **QA** — testability is decided at Frame and Architect, and a repeated defect becomes a check. Read `qa-workflow`.
- **Team** — ownership without a handoff is where work stalls. Read `team-workflow`.

## Depth: light or full

- **Light** — each artifact is a line or a paragraph, and the stage agents act as the second reader. A tiny slice, a copy edit, a fix with an obvious cause.
- **Full** — each artifact is written out as `references/stages.md` describes it. A schema or public interface change, a slice with users waiting, anything hard to roll back.

Depth belongs to the slice, not to the person. A solo developer usually runs light and a team usually runs full, and either may choose the other for one slice. Write the choice in the frame so it can be challenged. Depth never changes which stages run or which may be waived; that is the `Waivable` line in the stage reference.

## Choosing

- One person, no team: **solo**.
- A developer with reviewers and a release owner: **developer**.
- The person accountable for acceptance and the go/no-go: **QA**.
- Setting up or fixing the process for several people: **team**.

A team running light depth for a slice is a decision; say so in the frame so it can be challenged. The stage definitions themselves are in `references/stages.md`; the way each profile runs them is in the skill named above.
