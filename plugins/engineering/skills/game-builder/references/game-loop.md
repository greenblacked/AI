# The game loop and the code around it

Read this before writing the loop skeleton in step A4. The loop is the one piece of a game that cannot be tuned later, because everything else is built on its assumptions.

## Contents

- [Why a fixed timestep](#why-a-fixed-timestep)
- [Tier 1 and 2: the loop in JavaScript](#tier-1-and-2-the-loop-in-javascript)
- [Tier 3: the loop in Godot](#tier-3-the-loop-in-godot)
- [Input: edges and buffering](#input-edges-and-buffering)
- [Game states](#game-states)
- [Tuning in one place](#tuning-in-one-place)
- [Seeded randomness](#seeded-randomness)
- [Pooling](#pooling)

## Why a fixed timestep

Simulating with whatever time elapsed since the last frame makes the game a different game on every machine: a jump reaches a different height at 30 and 144 frames per second, collisions tunnel when a frame is slow, and a replay cannot be reproduced. The fix is to simulate in fixed steps, accumulate real time, run as many steps as the accumulator allows, and render the state interpolated between the last two steps so motion stays smooth at any refresh rate.

Cap the number of steps per frame. Without a cap, a tab that was backgrounded for a minute tries to simulate a minute of play in one frame, the frame takes longer, more time accumulates, and the game never catches up. That is the spiral of death, and the cap turns it into a brief slowdown instead.

## Tier 1 and 2: the loop in JavaScript

```javascript
const STEP = 1 / 60;          // simulation rate, independent of display rate
const MAX_STEPS = 5;          // cap per frame: beyond this the game slows rather than spiralling
let accumulator = 0;
let last = performance.now();

function frame(now) {
  accumulator += Math.min((now - last) / 1000, MAX_STEPS * STEP);
  last = now;
  input.poll();               // read once per frame; steps consume the same snapshot
  let steps = 0;
  while (accumulator >= STEP && steps < MAX_STEPS) {
    state.previous = snapshot(state.current);
    update(state.current, STEP);
    accumulator -= STEP;
    steps += 1;
  }
  render(state.previous, state.current, accumulator / STEP);  // alpha in [0, 1)
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
```

`render` draws each entity at `previous + (current - previous) * alpha`. Only positions and rotations need interpolating; discrete state such as health or animation frame reads from `current`.

Phaser has its own loop. Keep the same discipline inside it: put simulation in a step function called at a fixed rate from `update`, and keep the physics step at a fixed rate by setting `physics.arcade.fps` (or the matter equivalent) rather than letting it follow the display.

## Tier 3: the loop in Godot

Godot already separates the two. `_physics_process(delta)` runs at the fixed rate in project settings (60 by default) and is where simulation, movement and collision belong. `_process(delta)` runs once per rendered frame and is for camera smoothing, interpolation and effects. Enable physics interpolation in project settings so a 60 Hz simulation looks smooth on a 144 Hz display.

```gdscript
extends CharacterBody2D

@export var tuning: PlayerTuning   # a Resource holding every feel number

func _physics_process(delta: float) -> void:
    var wanted := Input.get_axis("move_left", "move_right")
    velocity.x = move_toward(velocity.x, wanted * tuning.max_speed, tuning.accel * delta)
    velocity.y = min(velocity.y + tuning.gravity * delta, tuning.terminal_velocity)
    if _jump_requested() and _can_jump():
        velocity.y = -tuning.jump_velocity
    move_and_slide()
```

Use `CharacterBody2D` or `CharacterBody3D` for the player. `RigidBody` is for things that should behave physically; a player driven by it lands late and floats, and the numbers in `feel.md` cannot be applied to it.

## Input: edges and buffering

Read input once per frame into a snapshot with three views per action: held, pressed this frame, released this frame. Simulation reads the snapshot, never the device, so every step in a frame sees the same input and a replay can feed recorded snapshots back in.

Two buffers make controls feel responsive, and both are in `feel.md` with numbers:

- **Jump buffer.** A press shortly before landing is remembered and fires on landing. Store the time of the last press; on landing, jump if it is within the window.
- **Coyote time.** A press shortly after walking off an edge still jumps. Store the time the character was last grounded; allow the jump if it is within the window.

Actions fire on the pressed edge. Binding anything to release adds the entire press duration to the input latency.

## Game states

A small explicit state machine beats flags. One enum, one current state, and enter and exit hooks per state:

```javascript
const states = {
  title:    { enter() {...}, update(dt) {...}, exit() {...} },
  playing:  { enter() {...}, update(dt) {...}, exit() {...} },
  paused:   { ... },
  gameOver: { ... },
};
function transition(to) { states[current].exit?.(); current = to; states[current].enter?.(); }
```

Entities that have behaviour of their own — an enemy that patrols, chases and attacks — get the same shape. Nested booleans such as `isChasing && !isStunned && canAttack` are where update-order bugs live.

## Tuning in one place

Every number that changes how the game feels lives in one object, resource or file, named for what it does:

```javascript
const TUNING = {
  moveSpeed: 220, accel: 1800, decel: 2400, airControl: 0.6,
  gravity: 1800, apexGravityScale: 0.5, fallGravityScale: 1.8, terminalVelocity: 900,
  jumpVelocity: 620, jumpBufferMs: 120, coyoteMs: 100,
  hitStopMs: 60, shakeTrauma: 0.4,
};
```

In Godot, a `Resource` subclass with `@export` fields does the same and can be edited in the inspector while the game runs. The point is that step A5 becomes edits to one place, and the handoff can list the values.

## Seeded randomness

`Math.random` cannot be seeded, so a bug that depends on the spawn order cannot be replayed. Use a small seeded generator and print the seed at start:

```javascript
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
```

Godot's `RandomNumberGenerator` takes a seed directly. Keep one generator for the simulation and a separate one for cosmetic effects, so adding a particle does not change the next enemy's position.

## Pooling

Creating and destroying objects inside the loop is what causes the periodic hitch a profiler shows as garbage collection. Anything spawned more than a few times a second — bullets, particles, enemies in a wave — comes from a pool: preallocate, mark inactive instead of destroying, reuse the next inactive one. In Godot, instantiate the scene once per pool slot and toggle `visible` and `process_mode` rather than calling `queue_free`.
