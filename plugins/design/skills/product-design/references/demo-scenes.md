# Demo scenes

Read this at step 7, only when the brief is a scene rather than a still. A scene is a
mock in which one thing happens: a trigger, and its visible effect. This skill stages it;
`motion-showcase` captures, loops and encodes it.

## Contents

- One causal action
- The beats
- The cursor
- Reduced motion
- The time hook
- Handing off to motion-showcase

## One causal action

Write the action as one sentence with a cause and an effect before scripting anything:
"The cursor clicks Retry and the payment row turns to Paid." If the sentence needs an
"and then", it is two scenes. Nothing else moves except ambient state the product itself
shows, such as a blinking caret or a live indicator, and that moves at the product's own
rate.

The effect is the claim from step 1. If the effect is not the claim, the scene is
showing the wrong action.

## The beats

The timings below are starting points for a scene that is read at a glance. Adjust them to
the product's own motion tokens where those exist, and keep the order.

| Beat | What happens | Duration |
| --- | --- | --- |
| Rest | The starting state, still, so the viewer can read it | 0.8 to 1.2 seconds |
| Approach | The cursor travels to the trigger on an eased path | 0.4 to 0.8 seconds |
| Press | The trigger shows its real pressed state | 100 to 200 milliseconds |
| Effect | The change the product really makes, at the product's own transition timing | 200 to 600 milliseconds |
| Hold | The end state, still, long enough to read the result | 1.5 to 2.5 seconds |

The whole scene usually lands between three and five seconds. The hold is the longest beat
because the result is what the viewer should remember. If the effect is a number changing,
let it count or snap the way the product does; do not add a count-up the product lacks.

## The cursor

- Draw a plain arrow or the platform-neutral pointer in CSS or as an inline shape, at a
  size readable in the smallest destination, with a light outline so it shows on both dark
  and light surfaces.
- Move it on a curve with easing in and out, not a straight constant-speed line, which
  reads as mechanical.
- Show the press with the control's own pressed state, not a ripple or ring the product
  does not have.
- On a phone frame, replace the cursor with a touch indicator: a soft circle that appears
  on press and fades with the effect.
- Hide the cursor entirely in the still and the reduced-motion version.

## Reduced motion

Under `prefers-reduced-motion: reduce`, render the end state as a still with no cursor.
The result carries the claim, so the still loses nothing that matters. When the scene
plays in a page, it plays once or loops only within `motion-showcase`'s loop rules, and it
pauses when out of view.

## The time hook

Script every animated value inside one pure function, `render(t)`, where `t` is
milliseconds from the start of the scene. Nothing inside `render` reads a clock: no
`Date.now()`, no `performance.now()`, no `setTimeout`, no `setInterval` and no random
numbers, because the capture steps time frame by frame and must get the same frame for the
same time on every run.

Expose, on the page, the hooks `motion-showcase`'s capture mode calls, in the shape its
tested capture page uses:

- `window.__start`, which records the start time and calls `render(0)`.
- `window.__tick`, which reads `Date.now()`, subtracts the start time, calls `render` with
  the result and returns it. This is the only clock read in the scene: under the
  recorder's fake clock `Date.now()` is the time the recorder controls, which is what ties
  each frame to its step.
- The scene's total duration in milliseconds.
- A still mode that renders the end state with no cursor, for the reduced-motion version
  and for the comparison `motion-showcase` makes before recording.

Outside capture mode, drive `render` from animation-frame timestamps for review in the
browser, so the same function serves both.

Check the function yourself before handing off: calling `render` with the same time twice
gives the same result, and calling it with times out of order gives the same frames as in
order.

## Handing off to motion-showcase

Pass, in one note: the claim sentence, the action sentence, the beat table with the final
timings, the stage size and each deliverable size, whether it should loop, the still for
reduced motion, and the names of the hooks: `render`, `window.__start` and
`window.__tick`. `motion-showcase` owns everything from there: the capture clock, the loop
seam, overflow checks and encoding. Do not record the screen in real time to save the
step; a real-time recording cannot be repeated or checked against itself.

A scene that loops on a page for more than five seconds beside other content needs a
control that lets the user pause, stop or hide it (WCAG 2.2.2, Level A). A GIF has no
such control, so a looping embed ships as video with controls or as a still. Honouring
`prefers-reduced-motion` is good practice, a technique for 2.3.3 at Level AAA, but it
does not satisfy 2.2.2.
