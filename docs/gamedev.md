# Gamedev: start here

The `gamedev` plugin is nine skills, one subagent and one command. This page is the map:
how to size a project so the right amount of each skill's procedure applies, how to read
what a game type needs from the plugin, and what order to run the skills in. It does not
repeat any skill's procedure — every line below points at the section that carries the
detail rather than restating it.

## Pick your scale

Scale here means what the work requires, not a headcount or a budget figure — none of
this repository's skills are sourced to cite one, so none is given here. Read the row
that matches how the project is actually run, not the size anyone would like it to be.

| Signal | Indie / A | AA | AAA |
| --- | --- | --- | --- |
| Team | One small team wearing every hat | Specialised roles, and some outsourcing | Many specialised disciplines and external studios |
| Platforms | Usually one or two, often PC, web or mobile first | Several, including consoles | A simultaneous multi-platform launch |
| Tooling | Engine defaults and off-the-shelf services | Engine defaults plus shared build gates: a CI size check and a devkit capture routine | Custom tooling and pipelines |
| Milestones | Set by the team itself | A publisher's milestones | A submission calendar across every launch platform |
| Who owns QA and certification | The people who build | A producer and a dedicated QA pass | Dedicated certification, localisation and compliance teams |
| After launch | Whatever the team can sustain | A patch cadence a publisher agreed to | A dedicated live-ops team |

Where a number would help — a device's memory ceiling, a store's size cap, a platform's
required frame rate — the skill that owns that decision says "check your platform
holder's current requirements" rather than a figure that goes stale. Read that skill's
own table before committing to one.

A project can sit at different tiers for different disciplines: a two-person team
shipping to one console still runs `game-certification` at something close to the AA
weight, because the platform holder's process does not shrink for a small team. Read the
signal, not the team photo.

## Pick your game type

The plugin has no per-genre skill; genre changes which sections of the nine skills carry
the risk, not which skill applies. Six types come up often enough to name directly:

| Type | Where the risk sits |
| --- | --- |
| Mobile casual / free-to-play | `game-balance`'s economy-and-progression target and its telemetry-first discipline; `game-certification`'s privacy and paid-random-item declarations |
| 2D or small single-player (platformer, puzzle, roguelike) | `game-builder`'s core loop and feel floor; often light enough to skip `game-netcode` entirely, and `game-save-system` too unless there is meta-progression to persist, as many roguelikes have |
| Narrative / story-driven | `game-design-doc`'s user flow and states-and-transitions sections, where branching lives; `game-level-design`'s beat chart for pacing |
| Competitive multiplayer and live service | `game-netcode`'s authority model, chosen from genre and player count before any code exists; `game-balance`'s win-rate-by-skill-band reading |
| Open world / large 3D | `game-level-design`'s streaming and occlusion seams; `game-performance`'s frame budget under a full scene; `game-save-system`'s save-anywhere-versus-checkpoint cadence |
| VR / XR | `game-performance`'s frame budget table, which fixes a 72 to 90 fps floor for comfort rather than a target chosen for looks; `game-builder`'s feel floor and `game-design-doc`'s acceptance criteria both need the comfort requirement stated as a number |

A rollback authority model is specifically for fighting games and small-count reaction
games — `game-netcode`'s authority table names it, and it is the wrong choice for
anything else on this list.

## The route

`/level` runs six of the nine skills in order for one feature or level:
`game-design-doc` → `game-level-design` → `game-builder` → `game-balance` →
`game-performance` → `game-assets`, each with a stop condition, each handing the next
one something specific. `game-netcode` and `game-save-system` are not stages in that
chain — they are decided *before* stage 3 fixes an authority model or a save format by
accident, whenever the feature touches multiplayer or persistent state. `game-certification`
is not a stage either; it owns the submission gate once a build is ready to ship, and its
calendar runs alongside the whole chain rather than after it. `frame-capture-reader`
is not a stage of its own — it is the subagent `game-performance` hands a large capture
to at its step 4, so the capture never enters the main conversation.

| Scale | How to run the chain |
| --- | --- |
| Indie / A | Run `/level` per feature, but say out loud what is being skipped rather than silently thinning it. Skip `game-netcode` and `game-save-system` outright when the design has no multiplayer and no persistence. Run `game-assets`' step 1 and step 4 — the budget and the LFS decision — at project start even when the numbers are informal; that skill's own anti-patterns warn against treating size as an end-of-project task and against adding LFS once the history is already large, so the full measured audit can wait for a build worth measuring but the two decisions cannot. `game-certification` still applies in full for any console or store target; the platform's process does not shrink for a small team. |
| AA | Run the full six-stage chain per feature, with a producer and QA reading the hand-off between stages rather than the one person who built it. `game-netcode` and `game-save-system` are named at `game-design-doc` step 7 and settled before `game-builder` starts, not discovered afterwards. `game-certification`'s calendar is built from the publisher's milestones and checked at step 1 of that skill before the schedule is promised to anyone. |
| AAA | The chain runs per feature inside each discipline, and several run in parallel across teams and external studios — the hand-off at each stage is a real deliverable between people who do not sit together, not a note to self. `frame-capture-reader` is the normal way `game-performance` reads a capture, because a capture from a AAA build is large enough that reading it inline is not an option. `game-certification` runs continuously against a submission calendar for a simultaneous multi-platform launch, and localisation, compliance and live-ops are separate teams reading the same design doc. |

## Game type to skill matrix

Where the risk concentrates for each type, in the order the route above runs:

| Game type | Skills carrying the most risk | Why |
| --- | --- | --- |
| Mobile casual / F2P | `game-balance`, `game-certification` | The economy corridor is the game's business model, and this genre carries the heaviest paid-random-item and data declarations at cert |
| 2D / small single-player | `game-builder` | The feel floor and the grey-box loop are almost the whole game; the other eight skills apply lightly or not at all |
| Narrative / story-driven | `game-design-doc`, `game-level-design` | Branching state lives in the spec's states-and-transitions section, and pacing is a beat chart, not a difficulty curve |
| Competitive multiplayer / live service | `game-netcode`, `game-balance` | The authority model has to be right from the first line of code, and balance is read from telemetry by skill band rather than by feel |
| Open world / large 3D | `game-level-design`, `game-performance` | Streaming seams are a layout decision made while the macro-structure can still move, and the frame budget has to hold under a full open scene, not a test level |
| VR / XR | `game-performance`, `game-builder` | The frame budget is a comfort requirement, not a preference, and the feel floor has to be met at that fixed rate rather than tuned down to reach it |

## Not covered yet

Two gaps this survey found, named rather than filled with an invented skill:

- **A concept or greenlight stage before `game-design-doc`.** Nothing in this plugin
  helps decide whether to build the game at all — a pitch, a feasibility read, a
  greenlight decision. `game-design-doc` starts from an idea already chosen; getting
  from nothing to that idea is not here.
- **Live ops after launch.** Nothing in this plugin covers running a live game once it
  has shipped — a content and season cadence, ongoing economy tuning as a planned
  calendar rather than a single patch, or community management. `game-balance` covers
  changing one number with evidence; it does not cover planning what changes next
  quarter.
