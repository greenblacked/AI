# What each hop receives

## Contents

- The rule
- Per hop
- When a report has no Handoff section
- Fresh context for the independent stages

## The rule

Each hop gets the previous artifact and only the previous report's `Handoff` section. The artifact is the evidence; the handoff is the few lines that say what the next stage must answer first. A summary of the report adds the previous stage's opinion, which the next stage cannot tell apart from the facts.

## Per hop

| Hop | Receives | Asks first |
| --- | --- | --- |
| request to framer | The request in the person's words, known constraints, who the users are | What is the problem, in one or two sentences |
| framer to architect | The frame | Does the approach fit the success criterion and the constraints |
| architect to maker | The frame and the approach note | What order keeps the tree working after each step |
| maker to build | The plan, whole | Which step is first, and what is its proof (see `plan-drift-gate`) |
| build to maker, check | The diff, one commit per step, and the plan | Does each step match its files and change |
| maker to inspector | The diff, the frame's success criterion, the commands to run | Does each success criterion hold, fail or go unassessed |
| inspector to launcher | The change, the success criterion, the inspection result with residual findings | Go or no-go, asked of the Inspect owner before launcher starts |
| launcher to yielder | The success criterion, the evidence of the outcome, the inspection and launch findings | What did the criterion measure |
| yielder to framer | The retro's next slice | What is the problem this slice addresses |

On `DIVERGED`, architect receives the frame, the plan, the divergences section and the step each belongs to. It does not receive the builder's explanation of why: the builder's reasons are an argument for the diff.

## When a report has no Handoff section

Pass its open-questions or not-assessed block verbatim next to the artifact, and add one line naming the question the next stage answers first. Do not rewrite either into prose. If a stage routinely omits the section, ask for it in the next brief rather than reconstructing it.

## Fresh context for the independent stages

Inspector gets a fresh delegation on every round, and so does the maker check. A resumed stage is judging its own earlier verdict as much as the new artifact.
