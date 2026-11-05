# Layout checks

Read at step 3 of the skill, once a screen has anchors and sizes written down.

## The capture matrix

Capture each screen at the corners of the envelope from step 1, not in between. Between the corners, layouts degrade smoothly; at the corners they break.

| Capture | What it exposes |
| --- | --- |
| Smallest display, largest text scale | Clipping, overlap, controls pushed off screen |
| Largest display, smallest text scale | Elements stranded far from the action, text below the stated minimum |
| Safe-area adjustment at its limit | Anchors that ignore the adjustment and sit on the screen edge |
| Narrowest and widest aspect ratio you support | Anchors that assume one shape |

Capture on the actual device or the closest emulation you have. A resized desktop window does not reproduce a handheld's pixel density or a television's overscan, so treat a desktop capture as a first pass and say so in the spec.

## Overlap and clipping check

For each capture, list every element with its bounds, then check three things.

1. No element's bounds extend past the safe area, except a background that is meant to bleed.
2. No two elements' bounds intersect unless the spec says one sits on the other.
3. Every text element shows its full string, or truncates by a rule the spec names. Silent clipping is a failure; an ellipsis with the full text available on focus is a decision.

If the engine can dump element rectangles, compare rectangles rather than eyeballing. Otherwise mark the capture with the rectangles by hand for the failing screens only.

## When a screen does not fit

Order of preference: reflow (stack instead of row, wrap instead of line), then rank demotion (move an on-demand item behind a button), then scrolling with a controller route (a scrolling list is a focus-graph node and needs edges), and last a smaller minimum text size, which needs a written reason because it is the one that costs players. Shrinking the text-scale range to make the capture pass removes the setting players rely on and is not a fix.
