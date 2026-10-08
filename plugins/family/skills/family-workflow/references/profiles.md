# The four profiles

The stages never change; their depth does. Pick the profile that matches who is doing the work, and say which one you are running — a run that mixes profiles by accident is the failure this file exists to prevent.

## Solo

One person runs all six stages. The depth is light but no stage is skipped.

- **Frame:** a paragraph in the issue, not a page. Problem, user, done, slice.
- **Architect:** the decision in your head, written down only for the hard-to-reverse one.
- **Make:** small commits, each with its test. Plan them as you go.
- **Inspect:** the part a solo developer cannot do is independence. Delegate to `inspector`, and to `code-review` for anything you would rather not have written.
- **Launch:** still all three — a release path, a signal, a rollback. For a small change the rollback is "revert the commit", written down.
- **Yield:** five minutes. What worked, what did not, the next slice.

**Handoff:** each stage to your own next stage. The agents are the second pair of eyes you would otherwise not have.

## Developer

Frame, Architect, Make and Yield in depth; Inspect and Launch handed off.

- **Frame and Architect:** the one-page frame and the design note, reviewed by a peer.
- **Make:** the ordered change plan from `maker`, then the build.
- **Inspect:** handed to a reviewer (`inspector`, `code-review`) and, where the surface changed, `security-review` and `accessibility-audit`. You do not mark your own homework.
- **Launch:** handed to whoever owns the release, using `launcher` and `release-strategy`.
- **Yield:** you write it; the reviewer's findings are part of the input.

**Handoff:** the developer hands a diff and the plan to the inspector, and the inspector's findings back to the developer; the release owner gets the launch plan, not the diff.

## QA

Inspect in depth, and acceptance criteria pushed back into Frame and Architect.

- **Frame:** QA helps write the success criteria and the out-of-scope list, so "done" is testable before anything is built.
- **Architect:** QA reads the design note for testability — can each interface be exercised, each failure mode reached?
- **Make:** QA is a consumer of the change plan; each step's proof should be a test QA would accept.
- **Inspect:** the deep stage. `inspector`, `test-design` for the strategy, `e2e-testing` for the browser path, `accessibility-audit` for WCAG, plus exploratory testing against the frame's success criteria.
- **Launch:** QA owns the go/no-go against the acceptance criteria.
- **Yield:** QA's defects and their classes are the retro's main input, and the reason a class is added to the frame's checklist.

**Handoff:** QA receives the frame and the change plan, and returns findings by severity plus a go/no-go. A defect that repeats becomes a check in Frame, not a comment on the next PR.

## Team

All six stages with named owners and a handoff contract between each.

| Stage | Owner | Hands to |
| --- | --- | --- |
| Frame | product or lead | Architect |
| Architect | tech lead or senior engineer | Make |
| Make | the developer | Inspect |
| Inspect | reviewer and QA | Launch |
| Launch | release or ops owner | Yield |
| Yield | the whole team, on a cadence | Frame |

- **Named owner per stage.** "The team" owns nothing; a person owns each gate.
- **A handoff contract.** Each owner states what they hand on: the artifact, the open question, and who owns it next.
- **Yield on a cadence.** A scheduled retro, not one called when something hurts. `delivery-review` and `postmortem` feed it; `status-update` shares it.
- **The profile is visible.** A team running solo depth on a large slice is a decision, and saying so is what makes it reviewable.

**Handoff:** the artifact moves, not a meeting. The frame, the design note, the change plan, the findings, the launch plan and the retro are each a document with an owner, so a stage that stalls is visible as a missing artifact rather than a missed meeting.
