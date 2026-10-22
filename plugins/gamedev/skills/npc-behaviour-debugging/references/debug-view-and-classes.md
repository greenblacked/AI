# Debug view and classes

## Contents

debug view fields, transition log format, worked classification, navmesh checks, regression test shape

## Debug view fields

Draw in world space over the agent, and mirror in a panel for the selected agent.

| Item | Why it helps |
| --- | --- |
| Agent id and archetype | Tells a pooled instance from a fresh one |
| Goal | The thing it is trying to achieve now |
| Active state or tree branch | Shows the behaviour that is running |
| Last N transitions | Shows oscillation at a glance |
| Believed target position | A marker apart from the real one exposes stale perception |
| Memory age | A target last seen thirty seconds ago explains aimless wandering |
| Sight cone and hearing range | Misconfigured ranges are common |
| Path polyline and next waypoint | Shows where it thinks it can go |
| Navmesh polygon under the agent | Off the mesh is a distinct failure |
| Velocity and progress over the last second | The base for the stuck detector |
| Pending action and its completion condition | Shows what execution is waiting for |

## Transition log format

One line per transition, kept in a ring buffer per agent:

```text
t=412.36  chase -> attack  reason=distance<2.0
t=412.38  attack -> chase  reason=distance>=2.0
t=412.41  chase -> attack  reason=distance<2.0
```

Three transitions inside a tenth of a second with the same boundary is the signature of missing hysteresis. Log the value that triggered the condition as well as its name, since the number shows how close to the boundary the agent sits.

## Worked classification

Symptom: an enemy runs to a doorway, stops, then walks back.

1. Transition list: calm, no flipping. Not decision.
2. Belief marker: sits on the player, memory age zero. Not perception.
3. Path view: the path ends before the door and the next polygon is missing. Navigation.
4. Navmesh drawn at the agent radius: the doorway is narrower than twice the radius. The editor preview used a smaller profile.
5. Fix: widen the opening or reduce the radius used for that agent type, rebake, and add the doorway as a regression scenario.

Symptom: a companion stands still while the player walks away.

1. Transitions: stuck in `wait` with no exit when the player is beyond a distance. Decision, a state with no exit.
2. Fix: add the exit condition and a priority over `idle`.

## Navmesh checks

- Draw the mesh at the agent's actual radius, height and step height.
- Check gaps near doors, stairs, ledges, narrow bridges and where props were added after the bake.
- Check that links exist for every traversal the animation set can perform.
- Check dynamic obstacles: do they cut the mesh, and how long after they move?
- Check that the agent's start position is on the mesh and that spawns are not inside geometry.

## Regression test shape

- Load the level and the saved scenario.
- Seed the AI random stream.
- Step the simulation at a fixed rate for a fixed time without rendering.
- Assert: the agent reached the goal area, stayed under the allowed number of transitions, and the stuck detector did not fire.
- On failure, dump the debug ring buffer as the test artefact.
