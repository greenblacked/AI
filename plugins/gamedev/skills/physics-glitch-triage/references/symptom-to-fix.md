# Symptom to fix

## Contents

forcing frame rate and time scale, symptom matrix, engine settings, regression scene checklist

## Forcing the conditions

| Goal | Unity | Godot 4 | Unreal |
| --- | --- | --- | --- |
| Force low or high frame rate | `Application.targetFrameRate` with vSync off | `Engine.max_fps` | `t.MaxFPS` console variable |
| Slow motion | `Time.timeScale` | `Engine.time_scale` | `slomo` console command |
| Fixed physics step | `Time.fixedDeltaTime` (Project Settings, Time) | `physics_ticks_per_second` (Project Settings, Physics) | Project Settings, Physics, substepping settings |

Check the documentation for your engine version before relying on a name; these have moved between releases.

## Symptom matrix

| Observation | Likely cause | Fix |
| --- | --- | --- |
| Tunnels only at low frame rate | Step too large | Fixed step, substeps, continuous collision |
| Tunnels at any rate for a very fast body | Speed above thickness per step | Continuous collision, speed cap, thicker collider |
| Object stops short of a wall or sticks | Collider larger than the mesh, or contact offset | Check the collider shape drawn in the debug view |
| Shakes only at some frame rates | Variable update moves bodies | Move in fixed update only; interpolate |
| Camera shakes, object looks fine | Camera reads the physics position | Follow the interpolated transform; order updates |
| Character slides or stutters on a platform | Parenting and physics both moving it | One owner of motion; apply platform velocity |
| Stack vibrates at rest | Low iterations, high mass ratio, soft contacts, scaled bodies | See step 5 of the skill |
| Pile erupts at spawn | Overlapping colliders | Fix spawn positions or spawn staggered |
| Body flung after teleport | Old velocity retained | Reset velocity and forces |
| Ragdoll flings on activation | Initial pose overlaps itself, or joint limits missing | Pose from animation, set limits, activate gradually |
| Behaviour differs between machines only | Not this skill | `game-desync-forensics` if it matters |

## Engine settings by class

Tunnelling

- Unity: set the Rigidbody `collisionDetectionMode` to Continuous or ContinuousDynamic for the body.
- Godot: enable continuous collision detection on the RigidBody.
- Unreal: enable CCD on the body instance, and consider substepping.

Jitter

- Unity: set Rigidbody `interpolation` to Interpolate and move through the Rigidbody in `FixedUpdate`, not the Transform in `Update`.
- Godot: use `_physics_process` for bodies; enable physics interpolation if the version provides it, and take care that cameras read the interpolated transform.
- Unreal: use the physics tick group for movement and attach the camera after it.

Instability

- Unity: the default solver iteration counts are project settings and can be overridden per body.
- Godot and Unreal expose solver iteration settings in project physics settings; check the version.

## Regression scene checklist

- A wall of the thinnest thickness the game uses, with the fastest projectile or vehicle fired at it repeatedly from random angles.
- A moving platform with a character standing still on it, filmed at 15 and 144 fps.
- A tall stack of the common prop sizes left alone for ten seconds.
- A teleport and a respawn test checking the velocity after the move.
- A ragdoll activated on death at speed.
- Each run records pass or fail with numbers: displacement, maximum velocity, count of body-through-wall events.
