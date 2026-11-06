---
paths:
  - "docs/slices/**/*.md"
---

# Slice stage files

Loads when a file under `docs/slices/` is read or edited. Each slice folder holds one file per
FAMILY stage, and the next stage's owner opens the file instead of asking for a summary, so the
file has to be where they expect it and say what they expect.

- Use the fixed names: `frame.md`, `decision.md`, `plan.md`, `inspect.md`, `launch.md` and
  `yield.md`. A person, a script and a stage agent all find the same file only if the name
  never varies.
- Line 1 is the stage's `First question` from the `family-workflow` skill's stage list, copied and not reworded.
- The line under the title names the owner, so a stalled stage is a named person.
- A waiver belongs only in `decision.md` (Architect) or `launch.md` (Launch), the two stages
  that list marks `Waivable: yes`. Frame, Make, Inspect and Yield are never waived: do the
  stage, or say in its `Not assessed` section what was not done.
- A waived stage keeps its file, with the reason and the risk. A missing file reads as a
  skipped stage; a waiver reads as a decision.
- `inspect.md` ends with the go/no-go line, answered once by the Inspect owner. `launch.md`
  takes it as input and does not remake it.
- The main agent writes these files from the stage agents' reports; the agents have no
  editing tools, so the file holds what the owner accepted.
