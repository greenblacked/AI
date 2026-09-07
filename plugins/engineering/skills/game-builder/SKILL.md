---
name: game-builder
description: "Design and build a playable game scaled to the brief — a one-file browser prototype, a jam entry in Phaser, a small finished game in Godot or the engine already in use — or review one that exists and fix what makes it unfun, slow or unmaintainable. Building picks the lightest engine, presents 2-3 concept directions before code, gets the core loop playable in grey boxes first, then meets a game-feel floor: input on press, a fixed-timestep loop, readable failure, restart in a second. Reviewing covers feel, frame time, architecture and content, ranked by impact. Use whenever the user wants a game, a prototype, a jam entry or a mechanic tried out, or says a game feels floaty or lifeless or drops frames — \"make me a platformer\", \"snake in one file\", \"add juice\". Not for a reliability game day, a gamified product feature, a game's backend API or servers, or a general question about engines."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(npm:*), Bash(npx:*), Bash(node:*), Bash(godot:*), Bash(git:*), WebFetch
---

# Game Builder

Build games where the core loop is fun before anything else exists, and where the finished thing responds to the player the instant they press a key — and, where a game already exists, find the one thing costing it players and fix that rather than everything.

Two failure modes bracket the build side. One is a project with a main menu, a settings screen, a save system and an asset pipeline in which nobody has yet played the mechanic, because the mechanic was going to be added once the framework was ready. The other is a mechanic that works and feels dead: the jump fires on key release, the character floats because the physics engine is driving it, a death happens with no explanation, and nothing on screen or in the speakers confirms that a button did anything. This skill exists to avoid both: gate the concept before writing code, get the loop playable in coloured rectangles, tune feel against numbers rather than adjectives, and only then build the things around it.

## Two modes

Decide which one applies before doing anything else, and say which was chosen.

- **Mode A — Build.** Nothing exists yet, or the user wants a prototype, a jam entry, or a game built from a design. Follow the build workflow.
- **Mode B — Improve.** A game already exists and the user wants it reviewed, made to feel better, made faster, restructured, or finished. Skip to the improve workflow.

A game that "needs a redesign" starts in Mode B — play it first, because the existing build holds the tuning, the content and the list of things not to repeat — and moves into Mode A step A3 once the problem is named. Say when the handover happens.

## Mode A: Build a new game

Steps A1 and A3 are gates. Do not write project code before the user has chosen a concept direction, and do not build anything that is not the core loop before the loop has been played. Rebuilding menus around a mechanic that turned out not to be fun is the most common way a small game is never finished.

### Step A1: Intake

Ask in one batch, and ask why as well as what. The reason changes the answer: someone asking for Unity for a jam entry they will play in the browser is describing familiarity, not a requirement, and a single HTML file will be playable an hour sooner with no build step to break on the final night.

Ask about:

- **The reference and the twist.** "Like X but Y" is the fastest brief there is. Which game is it closest to, and what is the one thing that makes this one different?
- **Scope class.** A mechanic test, a jam entry, a vertical slice, or a small complete game. Each has a different definition of done, and a jam entry that aims at "complete game" ships nothing.
- **Platform and input.** Browser, desktop, mobile, controller. Touch changes the design, not just the bindings.
- **Engine constraint.** Something already in use, something the user wants to learn, or no preference. A stated preference wins; "no preference" routes by tier below.
- **Assets.** Art, audio or music that already exists, or placeholder throughout. Placeholder is the default and it is not a compromise — see A4.
- **Players.** Single player, local multiplayer, or networked. Networked multiplies the work by a factor the user should hear before choosing it.
- **Time.** A weekend, a month, open-ended. The budget decides how many of the directions in A3 are honest.
- **Anything fixed.** A theme, a deadline, a design document, an existing codebase. Fixed constraints win over this skill's preferences.

When the user has already answered most of this, confirm the gaps only and state assumptions for anything minor.

### Step A2: Route to the lightest engine that fits

The tier decides the stack, the layout and how long the first playable takes. Choose the lowest tier that satisfies the brief; every step up adds tooling, a build step and an export pipeline that someone maintains.

| Tier | Fits when | Build as |
| --- | --- | --- |
| 1 — Single file | One mechanic, one screen, browser, no external assets | One HTML file, canvas 2D, no dependencies, playable by opening it |
| 2 — Browser game | 2D, several scenes, sprites and audio, a web or itch.io target | Phaser 3 via Vite, an `assets/` folder, a scene per screen |
| 3 — Engine project | 3D, real physics, tilemaps or animation tooling, desktop targets | Godot 4 with GDScript by default; Unity or Unreal only when already in use |
| 4 — Networked | Real-time multiplayer | Tier 3 plus an authoritative server and a netcode model chosen by genre |

Announce the tier and the one-line reason before building. If the brief sits between two tiers, choose the lower one and say what would push it up. Godot is the tier 3 default because its scenes and scripts are plain text — readable in a diff, editable without the editor open — and it exports to the web, which keeps the playtest loop short.

For tier 2 and above, read `references/engines.md` before writing project files. For tier 4, read its netcode section before agreeing to the scope at all.

### Step A3: Present concept directions, then stop

Produce **two or three genuinely different directions**, not one idea with three names. Each direction gets:

- **Name and hook** — one sentence that would make someone want to play it
- **Core loop** — the verb the player repeats, described as thirty seconds of play
- **Signature** — the single thing this game would be remembered by
- **Feel target** — a named game whose controls this should feel like, so tuning has a reference
- **First playable** — exactly what exists after the first build, in grey boxes
- **Trade-off** — what this direction is worse at, honestly

Then stop and ask which one to build. Do not build all three, and do not start on the one that seems best.

Before presenting, check each direction against the brief: if it is the generic version of its genre, replace it. Two strong distinct directions beat three where one is filler.

### Step A4: Build the core loop first, in grey boxes

Build in this order, and play after each line:

1. The loop skeleton — a fixed timestep for simulation, rendering interpolated between steps, input read once per step. The pattern for each tier is in `references/game-loop.md`; read it before writing the loop, because a loop that ties simulation to frame rate is the one bug that cannot be tuned away later.
2. Player input and movement.
3. The one mechanic from the chosen direction.
4. The failure condition, and restart in under a second.
5. Score or progress, whatever tells the player it is going somewhere.

Nothing else yet. No menu, no settings, no save, no art. Every one of those is built around a loop that has not been played, and each one makes the loop more expensive to change.

Placeholder art is coloured rectangles with a label. Placeholder audio is a generated blip per action rather than silence, because feedback is part of the mechanic and a silent prototype tests the wrong thing. Put every tuning number — speeds, gravity, timings, spawn rates — in one block at the top of the file or one exported resource, so the next step is edits to one place rather than a hunt through the code. Seed the random number generator and print the seed, so a bug can be replayed and a level can be reproduced.

### Step A5: Play it, then tune feel against numbers

Play the first build for five minutes before changing anything, and write down where confusion, frustration or boredom happened and how long it took to reach the first moment of fun. That note is the design document now.

Then meet the feel floor in `references/feel.md`. Read it at this step; it carries the starting values — coyote time, jump buffering, hit-stop duration, camera lookahead — that turn "floaty" and "unresponsive" into specific edits. In summary: actions fire on press, never on release; every player action has a visible and audible response; a death is explicable from what was on screen; restart is one key and under a second; there is no state the player cannot leave.

Tune one number at a time and play after each change. A jump that feels wrong is usually one of gravity, apex hang, or buffer length, and changing all three at once teaches nothing.

### Step A6: Then, and only then, the rest

With the loop played and tuned, build outward in the order that adds the most play per hour:

- **Content.** Levels or waves that teach the mechanic through design rather than text: first in safety, then under pressure, then combined with something else. A tutorial screen is what a level failed to do.
- **The frame around the game.** Title, pause, game over, restart. Keep each to one screen.
- **Art and audio pass.** Replace placeholders in order of how long the player looks at each thing. The player character first; the background last.
- **Settings.** Volume, remappable controls, a screen-shake and flash toggle, and reduced motion. These are the accessibility floor and they cost an hour if done now and a week if done after the input code has spread.
- **Persistence.** Only if the scope class calls for it. A jam entry does not need a save system.

### Step A7: Export and publish, only if wanted

Ask before producing a build pipeline. Someone who wanted a prototype does not want a release workflow. When they do, `references/engines.md` has the export commands per tier and the publishing steps for itch.io and static hosting, plus the asset licensing check: every third-party asset has a licence that permits the use, and attributions live in a file that ships with the game.

### Step A8: Hand off

```markdown
## What this is
[The concept, the tier and why, the scope class and what "done" meant.]

## Play it
[Exact steps to run it locally, and the controls.]

## How it is built
[The loop, where the tuning numbers live, how a level or wave is defined, each file with a one-line purpose.]

## What is placeholder
[Every asset or system standing in for a real one, so nobody ships a grey rectangle by accident.]

## Tuning notes
[The current feel values and what each was tuned against, so the next person can change them with intent.]

## Known issues and next
[What was verified, what was not, and the next three things worth building.]
```

## Mode B: Improve an existing game

The output is a ranked set of findings the user can act on, not everything that could be better. A review with forty undifferentiated items is read once and closed.

### Step B1: Play it before reading it

Establish what is available — a playable build, the repository, profiler access — and be explicit about what each allows. Then play for ten minutes before opening a file, writing down every moment of confusion, every unexplained death, every input that felt late. Code review finds what is wrong with the code; play finds what is wrong with the game, and the second list is the one the user is paying for.

Never infer a finding from something not seen or measured. "Probably allocating in the update loop" is not a finding; a profiler capture showing a garbage-collection pause every few seconds is.

### Step B2: Agree the dimensions

Do not audit everything. Ask what the user is worried about and propose a starting set from it. "It feels bad" starts with feel and controls; "it stutters" starts with performance; "I cannot add a level without breaking three others" starts with architecture and content pipeline. The dimensions, with what each covers, are in `references/review.md`:

1. Feel and controls
2. Performance and frame time
3. Architecture and update order
4. Content pipeline and tooling
5. Teaching and onboarding
6. Accessibility

### Step B3: Audit

Work through the agreed dimensions with the checklists and the symptom tables in `references/review.md`. The feel floor in `references/feel.md` is the baseline standard: a game failing an item there is a finding by definition.

Measure rather than read. Frame-time histograms, not "seems to drop frames"; a count of bodies in the physics step, not "probably too many". Record each finding with its evidence — the file and line, the profiler number, the moment in play where it happened.

### Step B4: Report, ranked

Rank by impact on the player against effort to fix, and lead with what to do first.

```markdown
## Summary
[3-4 sentences: overall state, the single most important thing, what was and was not assessed.]

## Fix first
[High impact, low effort. Usually 3-6 items.]

## Findings by dimension
### [Dimension]
**[Severity] — [One-line finding]**
- Evidence: [file:line, measured value, moment in play]
- Impact: [what this costs the player]
- Fix: [the specific change, with the starting number where one applies]
- Effort: [S / M / L]

## Deferred
[Real findings not worth acting on now, with the reason.]

## Not assessed
[What could not be checked and why, with the way to check it.]
```

Severity means: **High** — players quit or cannot progress. **Medium** — real friction, no quits. **Low** — worth doing when the file is open anyway.

### Step B5: Implement, on request

Ask which findings to act on. Work in batches by dimension, so each can be played and reverted on its own. After each batch, play again and report the before and after — a frame-time number for performance, and a described play moment for feel. Where a fix changes the design rather than the tuning, hand over to step A3 and present directions rather than redesigning unilaterally.

## Anti-patterns

**Menus before the loop.** The most expensive mistake available here. Every screen built around an unplayed mechanic is rebuilt when the mechanic changes.

**Choosing the engine before the game.** An engine is a consequence of the tier, and the tier is a consequence of the brief. A mechanic test in a full engine spends the first day on project setup.

**A physics engine driving the player.** Rigid-body jumps float and land late. Platformer and action characters want a kinematic controller with hand-tuned curves; use the physics engine for the things that are supposed to feel physical.

**Frame-rate-dependent logic.** Multiplying by delta time in a variable-step loop still drifts, and a game tuned on a fast machine plays differently on a slow one. Fix the timestep and interpolate the render.

**Firing on release.** A jump bound to key-up adds the whole press duration to the input latency. Everything fires on press.

**The unexplained death.** If the player cannot say what killed them, they blame the game and stop. Telegraph before harm; show the cause after.

**Tutorial text.** A wall of instructions is a level that failed to teach. Design the first level so the mechanic is the only thing to do.

**Random without a seed.** A bug that reproduces once in twenty runs is a bug nobody fixes.

**Waiting for art.** A prototype in grey boxes is a real prototype. A game blocked on assets is a game nobody has played.

**Scope from the design document.** A forty-feature document describes the game after a year. A jam entry is one mechanic, three levels and an ending screen.

**Juice everywhere.** Screen shake on every hit is noise by the third one. Feedback scales with importance, and the biggest moment keeps the biggest effect.

**Netcode last.** Multiplayer added to a single-player codebase is a rewrite. Decide it at A1 and build the authority model in from the first step, or scope it out.

## References

- `references/game-loop.md` — read before writing the loop in A4: the fixed-timestep pattern per tier, input edges and buffering, state machines, pooling, seeded randomness.
- `references/feel.md` — read at A5 and during any feel review: the feel floor, the starting numbers for jumps, hit-stop and cameras, and the self-playtest protocol.
- `references/engines.md` — read for tier 2 and above before writing project files, and for netcode, export and publishing.
- `references/review.md` — read in Mode B: the checklists per dimension and the symptom-to-cause tables for performance and architecture.
