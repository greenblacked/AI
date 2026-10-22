---
name: physics-glitch-triage
description: "Diagnose and fix physics glitches by classifying the symptom first: tunnelling (fast thin object, small collider, large step), jitter (mixed simulation and render timing, platform parenting), exploding or unstable stacks (spawn overlap, extreme mass ratios, solver iterations, scaled bodies), launch artefacts after teleport or load, and frame-rate dependence. Fixes with continuous collision on the one body, fixed step, interpolation and interpolated camera follow, verifies at forced 15 fps and 144 fps and in slow motion, and keeps a regression scene. Use for \"the ball goes through the wall\", \"characters jitter on moving platforms\", \"physics explodes at low frame rate\", \"ragdoll flings\", \"objects vibrate when stacked\". Not for loop structure and feel (game-builder), physics cost (game-performance), or cross-peer determinism (game-desync-forensics)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Physics Glitch Triage

The work is done when the glitch is classified, the fix is applied at the source of the cause, the reproducing scene passes at 15 fps, at the target rate and at a high rate, and that scene is kept to run before every release.

The usual failure is a tweak that moves the symptom. Someone raises solver iterations for jitter that was a timing problem, or thickens a wall for tunnelling that was a teleport leaving a velocity behind. Physics symptoms look alike (the thing does something wrong near the physics) but each class has a different cause and a different fix, so name the class first.

## Scope

Use for: objects passing through colliders, visible shaking, stacks that vibrate or explode, bodies launched at huge speed, and physics that behaves differently at different frame rates.

Do not use for: how the game loop is structured or how the controls feel (`game-builder`), the cost of simulating many bodies (`game-performance`), or machines disagreeing about the result in a networked game (`game-desync-forensics`).

## Workflow

### 1. Reproduce at the extremes

Build a small scene that shows the glitch, then run it with the frame rate forced to 15 and to 144, and in slow motion. Most engines expose these: a target frame rate or max FPS setting, a time scale, and the fixed timestep value. A glitch that changes with frame rate is a timing problem; one that does not is geometry, mass or solver settings. Log the fixed step, the render frame time and the speed of the body at the moment it fails. Read `references/symptom-to-fix.md` for the matrix and the engine settings by name.

### 2. Classify

| Symptom | Class | First check |
| --- | --- | --- |
| Passes through a wall, sometimes | Tunnelling | Speed per step against collider thickness |
| Shakes against a moving object | Jitter | Where the body moves and where the camera reads |
| Pile vibrates or flies apart | Instability | Overlaps at spawn, mass ratios, scale |
| Flung at huge speed after teleport, load or respawn | Launch artefact | Velocity and sleep state at the moment of change |
| Works at 60, breaks at 20 or 144 | Frame-rate dependence | Is any physics work in the variable update |

### 3. Tunnelling

A body moves further in one step than the thickness of what it hits, so no overlap is ever detected. The causes are a fast object, a thin or small collider, and a large step. Fix in order of cost:

1. Turn on continuous collision detection for that body only. It is costly, so do not enable it globally.
2. Raise the substep count, or shorten the fixed step, if the whole scene needs it.
3. Thicken the wall collider or use a separate thicker collider for physics than for rendering. A thin visual wall can have a deep collider.
4. Cap the maximum speed of the body, since a limit makes the worst case bounded.

Verify by throwing the fastest object in the game at the thinnest wall at the lowest supported frame rate, many times from different angles.

### 4. Jitter

Jitter is almost always mixed timing: bodies moved at render rate while physics runs at a fixed rate, or the camera following the raw physics position. Check, in order:

1. The physics step is fixed, not variable, and the engine's fixed update is the only place physics bodies are moved or have forces applied.
2. Rendering interpolates the body's transform between the last two physics states, so motion is smooth at any render rate. Enable the engine's rigidbody interpolation, or interpolate yourself.
3. The camera follows the interpolated position, not the physics position, and its update runs after the object it follows.
4. A character on a moving platform is moved by the platform's motion in the same step and the same order, not parented with a transform that the physics then fights. Decide which owns the movement.

Fix whichever applies and re-test at 15 and 144 fps. If it still shakes, then look at contact softness and solver settings, not before.

### 5. Explosions and unstable stacks

Instability comes from the solver being asked for something impossible. Look for:

- Colliders overlapping at spawn, which the solver resolves with a large push. Fix the spawn position, not the push.
- Extreme mass ratios between touching bodies; keep them under roughly 10 to 1, and chain light bodies through intermediates when you need the contrast.
- Too few solver iterations for a tall stack, or joints under strain. Raise iterations for that body or scene, not the whole game, after the overlaps and masses are fixed.
- Scale applied to a body or a collider, including non-uniform scale on a parent, which many engines handle badly. Scale the mesh and set the collider size explicitly, and keep units realistic: metres and kilograms of plausible size, not a hundred times too large.

### 6. Launch artefacts

After a teleport, a level load, a respawn or an unpause, a body may keep its old velocity, accumulated forces or a sleeping state that wakes violently. Reset linear and angular velocity, clear forces, and set the sleep state deliberately when moving a body by script. For ragdolls, initialise from the animated pose and velocities and ensure joint limits are set before enabling.

### 7. Keep the regression scene

Save the minimal reproducing scene in the project with a short note on the failure it guards. Run it at 15 fps, the target frame rate and 144 fps in the pre-release checklist, and assert a measurable outcome: the ball stayed inside the box, the stack stayed within a small displacement after a few seconds, nothing exceeded a velocity limit.

If the complaint is that two machines get different results from the same inputs, that is outside this skill: use `game-desync-forensics`.

## Hand back

The class, the reproducing scene and the settings it ran under; the root cause found; the change made and why the cheaper alternatives were rejected; results at 15 fps, target and high frame rate; and where the regression scene lives and when it runs.

## Anti-patterns

**Raising solver iterations first.** It costs everywhere and fixes only one cause.

**Moving rigidbodies in the render update.** It fights the solver and produces jitter at some frame rates only.

**Global continuous collision.** It is expensive; scope it to the bodies that need it.

**Testing at one frame rate.** A fix that only holds at 60 is not a fix.

## References

- `references/symptom-to-fix.md` - read at steps 1 to 6: the symptom matrix, engine settings by name for Unity, Godot and Unreal, and a pre-release scene checklist.
