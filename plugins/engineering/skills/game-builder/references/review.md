# Reviewing an existing game

The checklists for Mode B, by dimension, with the symptom-to-cause tables that turn a complaint into a measurement. The feel floor in `feel.md` is the baseline; failing an item there is a finding by definition.

## Contents

- [1. Feel and controls](#1-feel-and-controls)
- [2. Performance and frame time](#2-performance-and-frame-time)
- [3. Architecture and update order](#3-architecture-and-update-order)
- [4. Content pipeline and tooling](#4-content-pipeline-and-tooling)
- [5. Teaching and onboarding](#5-teaching-and-onboarding)
- [6. Accessibility](#6-accessibility)
- [Measuring before claiming](#measuring-before-claiming)

## 1. Feel and controls

Play first; then check the code for each observation.

- Does anything fire on release? Search the input handling for release or key-up bindings on gameplay actions.
- Is there a jump buffer and coyote time, and are they in the ranges in `feel.md`?
- Is the descent slower than the ascent? Look for a single gravity value with no fall multiplier.
- Is the player driven by a rigid body? It will be the cause of late landings and floating.
- Does every action have a sound and a visible response? List the actions and tick them off.
- Is there hit-stop on hits? Is screen shake driven by a decaying value or triggered at a fixed size?
- Can the player explain every death? Note each unexplained one during play.
- Restart: how many inputs from death to playing again, and how many seconds?

## 2. Performance and frame time

Capture a frame-time histogram over two minutes of play, not an average frame rate. A steady 60 with a 200 ms hitch every eight seconds averages fine and plays terribly.

| Symptom | Likely cause | Confirm by |
| --- | --- | --- |
| Periodic hitch at a regular interval | Allocation in the loop; garbage collection | Memory graph sawtooth aligned with the hitches; allocation profile in the update path |
| Hitch when something spawns | Instantiation or asset load at spawn time | Profile the spawn call; check for a pool |
| Frame time rises with entity count | Per-entity work that should be batched, or O(n²) collision checks | Plot frame time against entity count; check for a broad phase |
| Frame time rises with sprite count but not logic | Draw-call bound: many textures, no atlas, per-sprite material | Draw-call count in the renderer stats; texture switches |
| Spikes in the physics step | Too many active bodies, collision layers not filtered, continuous collision everywhere | Physics profiler; body count; layer matrix |
| Stutter with smooth logic | Simulation tied to render rate, or no interpolation | Read the loop; check for a fixed step and an alpha |
| Slow on one machine only | Resolution-dependent effects, uncapped particles, full-screen shaders | Reproduce at that resolution; count particles |
| Long first frame or level start | Synchronous asset loading | Load profile; move to a boot scene with a progress bar |

Tools by tier: the browser's performance panel and memory graph for tiers 1 and 2; Godot's built-in profiler, monitors tab and `--debug` flags for tier 3; the engine's own profiler for Unity and Unreal. Record the numbers in the finding.

## 3. Architecture and update order

| Smell | What it costs | Fix |
| --- | --- | --- |
| One object owns the player, the enemies, the level and the UI | Every change touches it; nothing can be tested alone | Split by ownership; signals up, calls down |
| Behaviour as nested booleans | Update-order bugs that appear only in specific sequences | An explicit state machine per entity |
| Entities that read each other's internals directly | Changing one breaks another silently | Communicate through events or a shared interface |
| Tuning numbers scattered through the code | Feel cannot be iterated without a search | One tuning object or resource |
| Logic in the render path, or rendering in the update path | Behaviour depends on frame rate | Separate the two; fixed step for one, interpolation for the other |
| Randomness unseeded | Bugs that reproduce sometimes | A seeded generator, seed printed at start |
| Scenes or levels that reference each other by path string | Renaming breaks them at runtime | Registered references, or a level table |
| Save data as a dump of the live object graph | A field rename corrupts every save | A versioned, explicit save schema |

## 4. Content pipeline and tooling

- How is a level, wave or encounter defined? A data file or scene that a designer edits, or code that a programmer edits? The second means content costs a programmer.
- What happens when an asset is renamed or replaced? Broken references at runtime are a pipeline finding.
- Is there a way to jump to any level or state for testing? Without one, every test starts from the title screen.
- Are placeholder assets distinguishable from final ones? A grey rectangle shipped by accident is a real risk.
- Does the build reproduce from a clean checkout, and is the export scripted?

## 5. Teaching and onboarding

- What does the first level ask the player to do, and is the mechanic the only thing to do there?
- Is there tutorial text? Each paragraph is a level that failed to teach.
- Watch a new player if one is available: the first thing they try is what the game taught them.
- Are controls shown when first needed, and available at any time?
- Is difficulty a curve or a wall? Note where deaths cluster in play.

## 6. Accessibility

Check against the toggles in `feel.md`: remappable controls, per-channel volume, screen-shake and flash toggle, reduced motion, colour paired with shape, legible text size, a hold alternative for rapid presses. A game with none of these is not a game with a small gap; it is a game a measurable share of players cannot play.

## Measuring before claiming

A finding carries evidence: the file and line, the profiler number, or the moment in play with what was on screen. When something cannot be measured in the environment available — no profiler, no build, no second player — it goes under "not assessed" with the way to measure it, rather than under findings with a hedge.
