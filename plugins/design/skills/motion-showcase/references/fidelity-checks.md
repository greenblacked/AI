# Measuring faithfulness

Read this when placing exported layers, when proving the still, and when checking recorded
frames before encoding. The ffmpeg commands were run with ffmpeg, checked with 7.0.2, on a small fixture. Only
the overflow-mask run has its output quoted; the other commands were run to confirm they
execute, and no figure here is a threshold to reuse.

## Contents

- Placement cases
- Fixing the bar first
- Comparing the still
- Reading a difference image
- Overflow masks
- Seam, silent beat and rest
- The contact sheet
- What was not exercised

## Placement cases

An exported layer is right only if it sits where the source drew it. These cases go wrong
under a plain export and a plain placement, grouped by what misleads you.

| What misleads | Case | What to do |
| --- | --- | --- |
| The box is not the visible area | A shadow or glow reaches past its shape | Export with room for the effect and place by the effect's bounds. |
| | A stroke sits mostly outside its shape | Take the layer's true box from the stroke geometry. |
| | An arc is a slice of a full circle | Place by the whole circle's box and clip to the arc. |
| Nothing exports | A zero-width stroke has no area | Rebuild it as a line in the design's own style. |
| | A child of a component instance exports empty | Export the parent instance instead. |
| Weight and reach | A blurred, rotated blob carries no fine detail | Store it small and scale it up; the blur hides the loss. |
| | A pattern is larger than the surface showing it | Crop to that surface before inlining, or the page bloats and the pattern spills. |
| Tangled layers | Blur applied through a mask | Blur inside the mask's shape, or it bleeds past the edge. |
| | A photo is baked into a bigger layer | Export the photo alone and cover its slot with a placeholder until it arrives. |
| | Several joined surfaces share a shadow | That shadow belongs to their union, not to each surface; map its blur to the matching CSS shadow blur. |

Keep the source stacking order, skip hidden layers, and draw a frame's strokes above the
content it clips.

## Fixing the bar first

Write the bar into the pre-build statement before measuring anything, and leave it alone
afterwards. Use a looser bar for text-heavy containers than flat ones, since glyph edges
are where small rendering differences turn into noise. A container that misses may be
retested once with a stronger blur; a second miss means fix the container. The figure
comes from the user's design or the project's standard.

## Comparing the still

Render the still at the reference's scale and compare both after the same light blur, so
antialiasing noise does not dominate. Set `BLUR` as the bar allows. Overall:

```bash
BLUR=1
ffmpeg -hide_banner -i still.png -i reference.png \
  -lavfi "[0:v]gblur=sigma=$BLUR[a];[1:v]gblur=sigma=$BLUR[b];[a][b]psnr" -f null -
```

Per container, crop the same box from both before blurring. `W`, `H`, `X` and `Y` are the
container's bounds in output pixels:

```bash
ffmpeg -hide_banner -i still.png -i reference.png \
  -lavfi "[0:v]crop=$W:$H:$X:$Y,gblur=sigma=$BLUR[a];[1:v]crop=$W:$H:$X:$Y,gblur=sigma=$BLUR[b];[a][b]psnr" -f null -
```

Run it for every container and report the lowest as the worst surface.

## Reading a difference image

A single number cannot say where the error is. Amplify the blurred difference and look:

```bash
GAIN=8
ffmpeg -hide_banner -y -i still.png -i reference.png \
  -lavfi "[0:v][1:v]blend=all_mode=difference,gblur=sigma=2,lutrgb=r='clip(val*$GAIN,0,255)':g='clip(val*$GAIN,0,255)':b='clip(val*$GAIN,0,255)'" \
  -frames:v 1 diff.png
```

Look for shapes: a glow in the wrong place, a stacking error, a missing stroke, a shifted
shadow. Faint scatter along edges is sub-pixel offset and not worth chasing.

## Overflow masks

Build the mask from the real container shapes, radii included, grown by the statement's
margin so edge antialiasing does not fail the check. Paint it black over both frames and
compare what remains. Run it on every frame, not a sample, since a leak can last three
frames. The script below masks a fixture's two moving regions and compares its first frame
with the frame at the peak of the motion. `drawbox` covers rectangles only; a rounded
container needs a mask drawn from its node data, which was not tried here.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
# Container boxes grown by a few pixels so antialiasing at the edge cannot fail the check.
TRAVEL="drawbox=x=15:y=195:w=590:h=90:color=black:t=fill"
BAR="drawbox=x=15:y=365:w=590:h=30:color=black:t=fill"
compare() {   # compare <mask filters or null> <a.png> <b.png>
  ffmpeg -hide_banner -i "$2" -i "$3" \
    -lavfi "[0:v]$1[a];[1:v]$1[b];[a][b]psnr" -f null - 2>&1 | grep -o 'PSNR.*'
}
echo "full mask:   $(compare "$TRAVEL,$BAR" frames/f000.png frames/f030.png)"
echo "no mask:     $(compare null frames/f000.png frames/f030.png)"
echo "short mask:  $(compare "drawbox=x=15:y=195:w=300:h=90:color=black:t=fill,$BAR" frames/f000.png frames/f030.png)"
```

It printed:

```text
full mask:   PSNR r:inf g:inf b:inf average:inf min:inf max:inf
no mask:     PSNR r:12.323369 g:13.226914 b:17.145028 average:13.787094 min:13.787094 max:13.787094
short mask:  PSNR r:16.335694 g:20.116961 b:22.322342 average:18.878095 min:18.878095 max:18.878095
```

The full mask passes, the unmasked comparison shows the motion exists, and a mask that is
too short lets the moving block leak into the comparison and fails it, so a leak is not
hidden.

What each frame is compared with depends on the layout. Outside the joined surfaces of an
app frame, every frame equals the empty first frame. Outside separate cards, every
job-phase frame equals the still.

## Seam, silent beat and rest

Each is one comparison between two frames, and the passing result is `inf`:

```bash
ffmpeg -hide_banner -i a.png -i b.png -lavfi psnr -f null -
```

- **Seam.** `a` is the window's first frame and `b` the frame one cycle later. Test several
  frames, because a seam can close at the first and still drift at the sixth.
- **Silent beat.** `a` is a frame captured before start and `b` is each frame in the beat.
  A difference means a script-driven value was not reset.
- **Rest.** `a` is the still at the capture scale and `b` the last frame before the fade
  back.

## The contact sheet

Tile key moments to judge the whole loop at a glance. `STEP` is how many frames apart to
sample and `COLS` by `ROWS` the grid; once the cycle is known, pick frames from the real
beats instead of an even spacing.

```bash
FPS=60 STEP=10 TILE_W=240 COLS=3 ROWS=2
ffmpeg -hide_banner -y -framerate "$FPS" -start_number 0 -i frames/f%03d.png \
  -vf "select='not(mod(n,$STEP))',scale=$TILE_W:-1,tile=${COLS}x${ROWS}" -frames:v 1 sheet.png
```

Look for content past a container's edge, a ghost of the previous cycle, something that
pops in instead of arriving, and jobs too small to read at tile size.

## What was not exercised

Masks with rounded corners drawn from real node data, container bounds taken from a
design tool's export, and a similarity check on a photo backdrop.
