# Motion vocabulary

Read this before writing an entrance, a job or the cycle. It holds the vocabulary and the
rules. The design, or its system, supplies every duration, distance and curve; name each
once in the build and reuse it.

## Contents

- Entrances, grouped by kind of motion
- Sequencing
- Writing a job
- The showcase cycle
- The site variant

## Entrances, grouped by kind of motion

Choose the kind from what the element is, then pick the row. Nothing starts from a
zero-size point except lines and bars.

| Kind of motion | Fits | Notes |
| --- | --- | --- |
| Rise and sharpen | Cards, headings, body text, figures | Move a short way up while the blur clears. Text staggers by line or word. |
| Slide from the home edge | A top bar, a side rail's items, a bottom sheet | Travel starts at the edge the element hangs on, and a clip keeps it inside its own container. |
| Fade alone | Icons, badges, tints, glows, shadows | Anything with no shape to move gets only opacity. |
| Reveal along its axis | Bar fills, progress tracks, rules, ticks | A wipe or growth from the start edge, as progress would. |
| Sweep around | Rings, dials, arcs | Clockwise from the top, unless the design reads another way. |
| Placeholder, then swap | Photos, avatars, charts with heavy art | A quiet block of the right shape first, then the real image resolves over it. |

## Sequencing

- Containers arrive in reading order. Inside one: header, labels, values, visuals.
- A layer hidden beneath another in the final frame arrives after its cover and leaves
  before it, so it never shows through.
- A placeholder matches the real shape and sits just inside it. Never invent loading lines
  that the finished design lacks.
- Keep the stagger step small and constant. A long step across many items turns the
  entrance into the whole video.
- A joined app frame has nothing to enter: its surfaces are present and opaque from the
  first frame and only the contents arrive. Separate cards arrive themselves, then their
  contents.

## Writing a job

Say it in one sentence before drawing any keyframes. If it takes two sentences, split it
or drop it.

- It begins and ends on the exact design. A helper it introduces, such as a cursor, a
  marker or a tooltip, copies the design's styling and is hidden in the still.
- It changes text only for counters, typed entries and tooltips. A typed entry reveals
  glyph by glyph; find the glyph boundaries from the empty columns in the text image so a
  reveal never slices through a letter.
- A viewer sees something happen on each card soon after the loop starts, early enough
  to know at once that the picture is animated.
- It reads at the smallest deliverable. Enlarge a tiny mover, or outline it.
- Offset the cards in time so attention travels in reading order.
- One job per card, long enough to read and short enough to repeat within the cycle. A
  card with only text gets none.
- Jobs are eased keyframe tracks on the loop clock. Ambient touches layer on top and never
  stand in for a job.

## The showcase cycle

The phases run in this order: entrance, jobs, a short fade back to the empty state, a
silent beat. Lengthen the cycle before cutting a job, because the job is what the viewer
came for.

- The backdrop never fades in any phase.
- In an app frame only the contents fade back; with separate cards the cards fade too.
- Reset script-driven values along with style. The seam check is the test: the first frame
  of the window equals the frame one cycle later.
- If a camera move was requested, the frame returns to rest before the fade back.

## The site variant

A site has no cycle and no fade back.

- The entrance plays once, when enough of the section is in view to be noticed. Use
  `IntersectionObserver`, not a scroll listener, and take the threshold from the site's
  existing reveal.
- Jobs then run on; they pause once the section scrolls out of view and continue on return.
- Stagger only within a section, never across sections, so a section reached by a link
  still plays in full.
- Prose-only sections keep the site's ordinary reveal. A product or dashboard mockup gets
  the entrance alone unless the user agrees to a job.
- Under the reduced-motion preference, show the final still and run no ambient motion.
- Text is live markup built with the site's own components, tokens and fonts.
