---
name: npc-behaviour-debugging
description: "Find out why a computer-controlled character is stuck, stupid or twitchy from recorded decisions instead of guessing. Builds a per-agent debug view (goal, state, last transitions with reasons, believed perception facts, path), reproduces with a pinned seed and a recorded scenario, classifies the fault as navigation, perception, decision or execution, then fixes by class: navmesh drawn at the agent's real radius, hysteresis for flip-flopping, a stuck detector that logs state and recovers. Keeps the scenario as a regression test. Use for \"the enemy gets stuck on the doorway\", \"the AI flips between two states\", \"companion won't follow\", \"navmesh gaps\", \"behaviour tree does the wrong thing sometimes\". Not for enemy stats (game-balance), AI cost per frame (game-performance), crashes (debugging), or layout-placed navmesh seams (game-level-design)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# NPC Behaviour Debugging

The work is done when the faulty behaviour is reproduced on demand, the cause is named as one of four classes with the recorded evidence that shows it, the fix is in place, and the scenario that reproduced it runs as a regression test.

The usual failure is editing the behaviour tree or state machine on a theory. The character looks like it has a decision bug, so the conditions get rewritten, and three days later it turns out the navmesh had a gap the width of a doorframe. AI misbehaviour is hard because the cause is invisible: the agent's beliefs, goals and paths are not on screen. Make them visible first, then change logic.

## Scope

Use for: an agent that is stuck, oscillating, ignoring targets, following badly, taking absurd routes or failing sometimes and not always.

Do not use for: tuning enemy health, damage and difficulty (`game-balance`), the per-frame CPU cost of AI (`game-performance`), a crash or hang (`debugging`), or deciding where navigation seams go in a level layout (`game-level-design`).

## Workflow

### 1. Make the agent's mind visible

Build a debug view that can be toggled per agent, in the running game and ideally in recorded playback. Show:

- Current goal and the active behaviour or state, and for a behaviour tree the active branch.
- The last N transitions (start with 20), each with the frame or time, the from and to states and the reason: which condition fired.
- The perception facts it believes: what it sees, what it hears, what it remembers and how old each memory is, with the position it believes the target is at drawn as a marker beside the real one.
- The path it is following, the next waypoint, its target, its velocity and the distance moved over the last second.

Write the same data to a ring buffer that dumps on demand, so a tester can attach it to a bug report. Read `references/debug-view-and-classes.md` for the layout and field list.

### 2. Reproduce deterministically

An AI bug that appears one run in five is unfixable until it appears every run. Pin the random seed that the AI uses (give AI its own random stream, apart from effects), record the scenario: starting positions, the player's inputs or a scripted stand-in, the level state and the build. Replay it from the recording and confirm the same mistake occurs at the same moment. If it does not, something nondeterministic is feeding the AI, such as frame-rate-dependent timing, unordered iteration over perceived targets, or a physics result; find that before going further.

### 3. Classify the fault

Use the debug view to place the fault in one class:

| Class | Fingerprint in the recording | Typical causes |
| --- | --- | --- |
| Navigation | The path is wrong, absent or blocked; the agent presses against geometry | Navmesh hole, agent radius larger than a gap, missing off-mesh link (jump, door, ladder), dynamic obstacle not carving, stale path |
| Perception | The decision is right for what it believes and wrong for the world | Stale memory, target remembered at an old position, sight cone or range misconfigured, sound not registered, team filter wrong |
| Decision | The beliefs are right and the chosen action is wrong, or it changes every frame | Conflicting conditions, no hysteresis so two states flip, missing priorities, a state with no exit |
| Execution | The decision is right and the body does not complete it | Animation not finishing or not triggering, root motion fighting the controller, movement blocked by a collider, action interrupted |

Work in this order of cheapness: look at the transitions list for rapid alternation (decision), at the belief markers for a mismatch with the world (perception), at the path for gaps (navigation), then at whether the action's completion event arrives (execution).

### 4. Fix by class

Navigation. Debug-draw the navmesh and overlay the agent's real radius and height; do not trust the editor view built with a different agent profile. Find where the mesh is missing or narrower than the agent, then fix the geometry or the bake settings and rebake. Add off-mesh links for jumps, doors and ladders. Check that dynamic obstacles update the mesh or are avoided locally, and that a path is recomputed when it becomes blocked.

Perception. Make memory expire and make the age visible. Compare what the agent believes with the world and find the source of the difference: a missed update, a wrong filter or an event never delivered.

Decision, oscillation. Two states flipping every frame means their conditions are both true or both false near a boundary. Add hysteresis (enter at one threshold, leave at another), a minimum time in state, or a cooldown before returning. Give conflicting conditions an explicit priority instead of relying on the order they were written. Confirm every state has an exit and that a lower priority state cannot starve a higher one forever.

Execution. Check the completion signal. If an action waits for an animation event, make sure the event fires on every path, including interruption, and add a timeout so a missed event cannot hold the agent forever.

### 5. Add a stuck detector

Whatever the cause, an agent that stops making progress should be noticed and recovered. Measure progress against the goal, not against speed: an agent can move constantly and make none. If it has made less than a small distance of progress toward its goal over N seconds (start with 3 to 5), log the full debug state, then run a recovery: repath, try a different approach point, step sideways, or as a last resort teleport to the nearest valid mesh point out of sight. The log is the real value; it turns a tester's "it got stuck somewhere" into a bug report with a cause. Count recoveries per build and treat a non-zero count in a test pass as a bug.

### 6. Keep the scenario

Save the recorded scenario as a regression test that runs headless where the engine allows, asserts the outcome (reached the goal, did not transition more than a few times, was not stuck) and runs before every release. Adopt two rules for new behaviour: every state has an exit, and every condition has a priority.

## Hand back

The recorded scenario and how to run it; the class of fault with the debug evidence (transition list, belief mismatch, path view); the fix and the reasoning; the stuck detector's thresholds and recovery steps; and the test that now guards it. If the cause is not found, hand back what the evidence rules out.

## Anti-patterns

**Rewriting the tree before looking.** The cause is usually not in the tree.

**Trusting the editor's navmesh preview.** It may use a different agent profile from the one in game.

**Fixing oscillation with a delay everywhere.** A global delay makes every character sluggish; add hysteresis where the flip occurs.

**A teleport as the whole stuck handler.** It hides the geometry fault and ships it.

## References

- `references/debug-view-and-classes.md` - read at steps 1 and 3: the debug view's field list, the transition log format, a worked classification and the regression test shape.
