---
description: Run a level or feature from idea to reviewable through the gamedev skills in order — spec the scope, lay out the space against fixed player metrics, grey-box the loop in it, tune the curve, measure the frame cost on the target device, then size what it adds to the build — with a gate between each stage rather than one pass that does all six badly.
argument-hint: [what to build, for example "a timed escape level for the flooded district"]
allowed-tools: Skill, Agent(frame-capture-reader), Read, Grep, Glob, Write, Edit
---

Take this through the chain: $ARGUMENTS

Six stages, each owned by a skill that already exists. Run them in order and do not
collapse them into one pass. Every stage consumes what the stage before it produced, and
a stage run before its input exists produces work that is thrown away — tuning the
numbers for a loop nobody has played is the expensive version of that, because the
numbers get re-derived the moment the loop changes.

At each stage, say what you are handing to the next one. If a stage hits its stop
condition, stop the chain there and report — a stage that was skipped is not a stage that
passed, and reporting it as one is how a level reaches review with no frame budget behind
it.

Read each skill's own "Scale and game type" section before deciding how heavily to run
its stage — what a jam entry can skip, a AAA submission cannot.

## 1. Specify — `game-design-doc`

Write out of scope before scope. Mark every statement as a decision, an assumption, a
recommendation or an open question, and make the acceptance criteria something a stranger
could fail the build on.

**Stop if** the ask is too vague to spec. Name what is missing and ask for it. Do not
invent requirements to keep moving: an invented requirement is indistinguishable from a
decided one three weeks later, when it is code and somebody is defending it.

**Hands on** the must-have list, the acceptance criteria, and the open questions that
the layout is allowed to answer.

## 2. Lay it out — `game-level-design`

Fix the player metrics before any geometry exists — standing and crouching height, step
height, jump height and distance, sprint speed, cover height, door width, and the
blockout grid — and make every dimension in the blockout a multiple of them. Then chart
the pacing: every segment sorted into explore, combat, choreo or puzzle, intensity
plotted over time, and no category repeating back to back without a written reason.
Build the wayfinding cues into the blockmesh and watch someone walk it there, before art
makes the layout expensive to change. Settle where the streaming and occlusion seams
fall while the macro-structure can still move.

**Stop if** the metrics are not fixed and cannot be measured yet, because the character
controller does not exist. Say so and take the smallest possible detour through stage 3
to get a controller worth measuring — a layout built to invented metrics is a layout
that gets rebuilt.

**Hands on** the metrics table, the blockmesh, the beat chart with its reasons written
on it, and what the playtest at blockmesh stage showed about where players went.

## 3. Build — `game-builder`

Grey-box the loop inside that layout. Coloured rectangles, real input, real failure —
the mechanic playable before anything is pretty, because art on a loop that is not fun
only makes the loop expensive to cut. Meet the feel floor before calling the stage done: input acts on press,
a fixed-timestep simulation, failure that reads on screen, restart in one key.

**Stop if** the loop is not fun in grey boxes. Say so and go back to stage 1 rather than
continuing on the assumption that the art pass will rescue it. If the loop is fine and
the space around it is not — one route, nowhere to go in a fight, players lost — that is
stage 2 rather than stage 1.

**Hands on** a playable build in the laid-out space, the parameters that are deliberately
left open for tuning, and anything in the spec or the layout that turned out to be wrong
once it was playable.

## 4. Tune — `game-balance`

Decide what balanced means for this feature before moving a number — a difficulty curve
that rises, an economy that does not collapse, a spread of viable approaches — then
change one thing per playtest and leave a window to read it.

**Stop if** the playtests cannot produce signal: too few sessions to separate a trend
from noise, or several changes in one build so nothing can be attributed to anything.
Fix the test before reading the numbers.

**Hands on** the settled numbers, the ones still moving, and the playtest evidence behind
each change.

## 5. Cost it — `game-performance`

Convert the target frame rate into a per-frame millisecond budget and measure against it
on the hardware the game ships to, from a real build on the device. Judge the 1% low and
the 99th percentile rather than an average, and prove whether the frame is CPU-bound or
GPU-bound before changing anything.

Where the capture is large — a Unity Profiler export, an Unreal Insights trace, a
platform capture — hand it to `frame-capture-reader` instead of reading it here. It
returns the bound with its evidence and the hot frames, and the capture never enters this
context.

**Stop if** the only numbers available come from the editor or a desktop. A measurement
from the wrong machine is not a measurement, and the budget it appears to clear is the
wrong budget.

**Hands on** the feature's frame cost against the budget, which side of the frame it
lands on, and anything it made worse elsewhere.

## 6. Size it — `game-assets`

Apply import settings at the folder level so a new asset is correct by default, choose
per-platform texture compression rather than shipping what imported, and measure what
this feature adds to the build and to runtime memory.

**Stop if** the feature's assets push the build past a store limit or a device memory
ceiling. That is a scope conversation to take back to stage 1, not an import setting to
tighten until it fits.

**Hands on** the build size delta, the memory footprint on the target device, and the
import presets that were added.

## What comes after, and what runs alongside

None of these is a stage in this chain. Each is cheap now and expensive later, which
is why they are named here rather than discovered at submission.

- **Shipping to a console or a store**: `game-certification` owns the submission gate,
  and its calendar — ratings, platform accounts, storefront lead time — is not something
  this chain can compress.
- **The feature touches persistent state**: progress, unlocks, checkpoints, currency or
  inventory all mean `game-save-system` should decide the compatibility promise and the
  format before stage 3 fixes it by whatever the build happened to serialise.
- **The feature touches multiplayer**: `game-netcode` should choose the authority model
  before stage 3 assumes one by default — `game-builder`'s own anti-patterns name a
  netcode model decided late as the rewrite it becomes.

## Finish

Report one block per stage: what it produced, what it decided, what it left open. Name
any stage that stopped and what stopped it. Then give the one thing a reviewer should
play first, and the one number they should not take on trust.
