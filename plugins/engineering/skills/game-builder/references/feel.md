# Game feel: the floor and the starting numbers

Read this at step A5, and during any Mode B review of feel. "Floaty", "unresponsive" and "lifeless" are each a small set of specific numbers, and this file names them.

## Contents

- [The feel floor](#the-feel-floor)
- [Jump and movement starting values](#jump-and-movement-starting-values)
- [Feedback, in layers](#feedback-in-layers)
- [Readability](#readability)
- [Camera](#camera)
- [Accessibility toggles](#accessibility-toggles)
- [The self-playtest protocol](#the-self-playtest-protocol)

## The feel floor

Non-negotiable regardless of tier or scope class, because each is cheap now and expensive once the input code has spread:

- Every action fires on the pressed edge. Nothing fires on release except a variable-height jump cut.
- Every player action has a visible response in the same frame and an audible one — a placeholder blip counts.
- A death or failure is explicable from what was on screen. Harm is telegraphed before it lands and the cause is visible after.
- Restart is one key, from anywhere, in under a second, and returns to the start of the current attempt rather than the title.
- No state the player cannot leave: no soft locks, no menu without a back, no dialogue without a skip.
- The controls are shown on screen the first time each is needed, and the whole set is one key away at any time.
- The simulation runs at a fixed rate and the render interpolates, so it plays the same on every machine.

## Jump and movement starting values

These are starting points for a 2D platformer or action game at roughly 32-pixel character scale; tune from here, one at a time. A 3D character wants the same shape with different magnitudes.

| Number | Start at | What it fixes when wrong |
| --- | --- | --- |
| Coyote time | 80–120 ms | Jumps that "should have worked" at ledges |
| Jump buffer | 100–150 ms | Presses just before landing that were eaten |
| Variable jump | Cut vertical velocity to 40–50% on early release | One jump height for every situation |
| Apex hang | Gravity × 0.5 within a small velocity band around the apex | A jump with no moment of control at the top |
| Fall gravity | Gravity × 1.5–2.5 once falling | The floaty descent, the single most reported feel complaint |
| Terminal velocity | Set it; 1.5–2× jump velocity is common | Falls that become uncontrollable on long drops |
| Ground acceleration | Reach max speed in 6–10 frames | Sluggish starts, or a character that slides |
| Ground deceleration | Faster than acceleration, 3–6 frames | Overshooting a platform edge |
| Air control | 50–80% of ground acceleration | Committed jumps that feel like a mistake |
| Corner correction | Nudge sideways up to 4–8 px when clipping a ceiling corner | Jumps that clip a corner and die |
| Ledge forgiveness | Snap up when the feet are within 2–4 px of a platform top | Landing on the edge and sliding off |

For a top-down or twin-stick game the equivalents are acceleration, deceleration, and a turn rate; the failure modes are the same sluggish start and the same overshoot.

## Feedback, in layers

Feedback scales with importance. Every action gets the first two layers; only the big moments get all of them.

1. **Anticipation.** A wind-up of a few frames before an attack or a launch. Cheap, and it makes the action readable.
2. **Sound.** One sound per action, and a different one per outcome: swing, hit, miss, kill.
3. **Hit-stop.** Freeze both parties for 40–100 ms on a hit. Longer for heavier hits. Nothing else conveys weight as cheaply.
4. **Screen shake.** Drive it from a trauma value in [0, 1] that decays over time, and shake by trauma squared, so small hits barely move the screen and a big one really does. Add trauma per event rather than triggering a fixed shake; overlapping hits then feel bigger instead of resetting.
5. **Flash and particles.** A white flash on the thing that was hit for one or two frames; particles that burst outward from the impact point rather than from the entity's centre.
6. **Squash and stretch.** Scale the sprite on launch and landing, 10–20%, for two or three frames.

Taken all at once on every event this is noise. The feel test is that the biggest moment in the game still feels biggest.

## Readability

- Telegraph before harm: an attack has a wind-up, a hazard has a warning frame, a projectile is visible for several frames before it can hit.
- Show the cause after: freeze on death for a beat with the killer visible, or replay the last second.
- Keep the player distinct from everything else by silhouette and colour, and never rely on colour alone.
- Enemies read left to right in danger: the thing the player should worry about is the thing that stands out.
- A pickup, a hazard and a decoration should never share a shape.

## Camera

- **Deadzone.** The player moves within a box before the camera follows; no box and every step jitters the world.
- **Lookahead.** Offset toward the facing direction, 10–20% of the viewport, eased over a few hundred milliseconds. The player sees what is coming.
- **Smoothing.** Exponential follow, framerate-independent (use the elapsed time in the exponent). Linear lerp per frame speeds up on fast machines.
- **Bounds.** Clamp to the level; a camera that shows the void reads as a bug.
- **Vertical lag.** Follow vertical movement more slowly than horizontal for jump-heavy games, so the view does not bounce with every hop.

## Accessibility toggles

The floor, built at A6 before the input code spreads:

- Remappable controls, keyboard and controller, with the defaults shown.
- Volume per channel: master, effects, music.
- A screen-shake and flash toggle, and a reduced-motion setting that also slows or removes scrolling backgrounds.
- Colour is never the only signal; pair it with shape or icon.
- Text at a size legible at the target platform's viewing distance, and a hold-to-confirm alternative for any rapid-press requirement.

## The self-playtest protocol

Run it after the first build and after every batch of tuning:

1. Play for five minutes without touching the code.
2. Write down every moment of confusion, frustration or boredom, and what was on screen.
3. Note the time to first fun — the first moment the loop was enjoyable rather than merely working. Over two minutes on a one-mechanic prototype means the mechanic, not the polish, is the problem.
4. Note every death you could not explain.
5. Change one number, play again.

When a second person is available, watch rather than instruct, and write down the first thing they try. It is the thing the game taught them, whether or not it was intended.
