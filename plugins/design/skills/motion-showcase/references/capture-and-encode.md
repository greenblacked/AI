# Recording and exporting

Read this when the still has passed and you are about to record frames, and again before
encoding. Everything shown as output was produced by exactly the code printed beside it:
a small fixture page (a block and a bar on a one-second loop), ffmpeg, checked with 7.0.2,
and the browser automation library's 1.56.1 release. What was not exercised is listed at
the end.

## Contents

- The page and its loop clock
- The recorder
- What the logging printed
- The seam comparison
- Making the files
- Trimming a heavy GIF
- What was not exercised

## The page and its loop clock

Every time-based value is a pure function of loop time `t` in milliseconds, with the
cycle length held in one constant. In capture mode there is no animation-frame loop: the
page exposes a start hook and a tick hook and the recorder calls them. The page below is
the one that was run, including the `raf` mode that exists only to be compared against.

```html
<!doctype html>
<html><head><meta charset="utf-8"><style>
html, body { margin: 0; background: navy; }
#stage { position: relative; width: 643px; height: 419px; overflow: hidden; background: navy; }
#block { position: absolute; left: 20px; top: 200px; width: 80px; height: 80px; background: orange; border-radius: 12px; }
#bar { position: absolute; left: 20px; top: 370px; width: 580px; height: 20px; background: skyblue; transform-origin: 0 50%; transform: scaleX(0); }
</style></head><body><div id="stage"><div id="block"></div><div id="bar"></div></div>
<script>
const CYCLE = 1000;   // ms; the real cycle length comes from the build
const block = document.getElementById('block');
const bar = document.getElementById('bar');

// Every animated value is a pure function of loop time t, so frame N and frame N + one cycle agree.
function render(t) {
  const p = (t % CYCLE) / CYCLE;
  const s = Math.sin(Math.PI * p) ** 2;
  block.style.transform = 'translateX(' + (500 * s).toFixed(3) + 'px)';
  bar.style.transform = 'scaleX(' + s.toFixed(4) + ')';
}
render(0);

const mode = location.hash.slice(1) || 'loop';
let t0 = null;
function frame(ts) {                  // zero is the first animation-frame timestamp
  if (t0 === null) t0 = ts;
  render(ts - t0);
  requestAnimationFrame(frame);
}
if (mode === 'capture') {
  // The recorder owns time: no animation-frame loop, loop time comes from the controlled clock.
  window.__start = () => { t0 = Date.now(); render(0); };
  window.__tick = () => { const t = Date.now() - t0; render(t); return t; };
} else if (mode === 'raf') {
  // The variant compared against: same render, but time comes from animation-frame timestamps.
  window.__start = () => requestAnimationFrame(frame);
  window.__tick = () => null;
} else {
  requestAnimationFrame(frame);       // loop mode, for review in a normal browser
}
</script></body></html>
```

Under the fake clock `Date.now()` is the clock the recorder controls, so reading it in the
tick is what ties loop time to each step.

## The recorder

Run it with `node`; the script is not pre-approved, so it prompts. If the automation
library is installed globally, point `NODE_PATH` at its `node_modules`. The constants at
the top come from the intake: the stage size times the scale factor, the frame rate and
the cycle length. The viewport here is odd on purpose, to exercise the even-dimension crop
in the MP4 step. In a real build, size the viewport to the stage and pick the scale factor
that gives the deliverable its pixels.

```js
const { chromium } = require('playwright');
const fs = require('fs');

const WIDTH = 643, HEIGHT = 419;   // stage size times the scale factor; odd on purpose here
const SCALE = 1;
const FPS = 60;
const CYCLE_MS = 1000;
const SETTLE = 3, EXTRA = 6;       // frames before the window, and past it for the seam check
const CYCLE_FRAMES = FPS * CYCLE_MS / 1000;

const [, , mode, outDir] = process.argv;
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: SCALE });
  await page.clock.install({ time: 0 });
  const url = 'file://' + __dirname + '/page.html#' + mode;
  await page.goto(url);
  await page.clock.pauseAt(1000);
  const shot = (name) => page.screenshot({ path: outDir + '/' + name + '.png' });

  for (let i = 0; i < SETTLE; i++) { await page.clock.runFor(17); await shot('pre' + i); }
  await page.evaluate(() => window.__start());

  let prev = 0;
  for (let i = 0; i < CYCLE_FRAMES + EXTRA; i++) {
    const target = Math.round(i * 1000 / FPS);   // rounded running total: no drift over a cycle
    if (target > prev) await page.clock.runFor(target - prev);
    prev = target;
    const t = await page.evaluate(() => window.__tick());
    await shot('f' + String(i).padStart(3, '0'));
    if (i < 2 || i === CYCLE_FRAMES - 1 || i === CYCLE_FRAMES) {
      console.log('frame', i, 'target', target, 'loop time', t);
    }
  }
  await browser.close();
})();
```

## What the logging printed

`node capture.js capture frames-capture` printed:

```text
frame 0 target 0 loop time 0
frame 1 target 17 loop time 17
frame 59 target 983 loop time 983
frame 60 target 1000 loop time 1000
```

Loop time equals the rounded target at every logged frame, and frame 60 lands on exactly
one cycle. `node capture.js raf frames-raf` printed `loop time null` on the same four
lines, because that mode has no tick; it is there only for the comparison below.

## The seam comparison

Frame 0 and frame 60 are the same moment of the loop, so they must match. Compare two
frames with:

```bash
ffmpeg -hide_banner -i a.png -i b.png -lavfi psnr -f null -
```

The two runs differ only in where loop time comes from. In the `raf` variant of the page
above, zero is the first animation-frame timestamp; in capture mode it is the controlled
clock inside the tick. Output of the PSNR line (min and max equal the average on a single
frame pair, so the table shows the average):

```text
capture  f000 vs f060: average:inf
capture  f001 vs f061: average:inf
capture  f005 vs f065: average:inf
raf      f000 vs f060: average:44.807868
raf      f001 vs f061: average:44.807868
raf      f005 vs f065: average:27.471154
```

`inf` means identical. The animation-frame variant never closed the seam on this fixture.
The reason inside the browser was not isolated; the claim is the comparison itself. The
frames before the start also matched frame 0 exactly in capture mode (`pre0`, `pre1` and
`pre2` each printed `average:inf` against `f000`).

## Making the files

Use only the window's frames: one cycle. `-t` on the input takes exactly one cycle of
them for the GIFs, and `-frames:v` does the same for the MP4. Every value in the
script comes from the intake; the numbers are the fixture's. For the compact GIF, pick the
chain that suits the frame:

- Frame fills the canvas: scale to cover, then crop the excess (`small-cover`).
- Content with empty borders: crop to the content at the required aspect ratio plus a
  margin, then scale (`small-crop`).
- Content fills the frame and the backdrop is one flat colour: scale to fit and pad with
  that colour (`small-pad`). Set `PAGE_BG` to the design's own flat backdrop. When a photo
  sits behind the interface, crop instead, since padding invents a border.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
# Every value below comes from the intake; the numbers shown are the fixture's.
FPS=60                    # capture rate
CYCLE_FRAMES=60           # frames in one cycle
CYCLE_S=1                 # the same cycle in seconds
GIF_FPS=20
WEB_WIDTH=400             # website GIF width
SMALL_W=480 SMALL_H=300   # the small GIF's required size
PAGE_BG=navy              # the design's own flat background, for the pad variant
CROP_W=600 CROP_H=375 CROP_X=10 CROP_Y=20   # content bounds plus a margin
IN="frames/f%03d.png"

ffmpeg -hide_banner -loglevel error -y -framerate "$FPS" -start_number 0 -i "$IN" \
  -frames:v "$CYCLE_FRAMES" -vf "crop=floor(iw/2)*2:floor(ih/2)*2" \
  -pix_fmt yuv420p -c:v libx264 -crf 18 -preset slow \
  -r "$FPS" -movflags +faststart loop.mp4

gif() {   # gif <name> <filter chain>: two passes, same chain in both
  ffmpeg -hide_banner -loglevel error -y -framerate "$FPS" -start_number 0 -t "$CYCLE_S" -i "$IN" \
    -vf "$2,palettegen=stats_mode=full" "$1-pal.png"
  ffmpeg -hide_banner -loglevel error -y -framerate "$FPS" -start_number 0 -t "$CYCLE_S" -i "$IN" -i "$1-pal.png" \
    -lavfi "$2 [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5" -loop 0 "$1.gif"
}

gif web "fps=$GIF_FPS,scale=$WEB_WIDTH:-2:flags=lanczos"
gif small-cover "fps=$GIF_FPS,scale=$SMALL_W:$SMALL_H:force_original_aspect_ratio=increase,crop=$SMALL_W:$SMALL_H"
gif small-crop "fps=$GIF_FPS,crop=$CROP_W:$CROP_H:$CROP_X:$CROP_Y,scale=$SMALL_W:$SMALL_H:flags=lanczos"
gif small-pad "fps=$GIF_FPS,scale=$SMALL_W:$SMALL_H:force_original_aspect_ratio=decrease,pad=$SMALL_W:$SMALL_H:-1:-1:color=$PAGE_BG"
```

Output, from `ffmpeg -i` on each file after the script ran on the frames from capture
mode:

```text
loop.mp4         Duration: 00:00:01.00  Video: h264 (High), yuv420p(progressive), 642x418, 60 fps
web.gif          Duration: 00:00:01.00  Video: gif, bgra, 400x260, 20 fps
small-cover.gif  Duration: 00:00:01.00  Video: gif, bgra, 480x300, 20 fps
small-crop.gif   Duration: 00:00:01.00  Video: gif, bgra, 480x300, 20 fps
small-pad.gif    Duration: 00:00:01.00  Video: gif, bgra, 480x300, 20 fps
```

The 643 by 419 frames became 642 by 418 through the even-dimension crop. Each GIF holds
20 frames. File sizes on the fixture were 10908 bytes for the MP4 and between 23951 and
30108 bytes for the GIFs; a real design with detail will be far heavier, so these show
the shape of the output and not a target. The CRF value is the one the run used and not a
recommendation; judge the result by eye.

## Trimming a heavy GIF

Lower the frame rate or the colour count before the size, for example a smaller
`GIF_FPS` or `palettegen=max_colors=128`. Keep ordered dithering whenever a photo is in
frame, because flat banding on a photo shows more than the extra bytes do.

## What was not exercised

A design tool's API or real design exports, an encoder other than ffmpeg, a site build,
CSS animations or transitions under the fake clock, a photo backdrop, and frame sizes
beyond the small fixture. Treat those parts of the workflow as guidance to check on first
use. In particular, if a page also uses CSS animations, run the seam check on it rather
than assuming the clock reaches them.
