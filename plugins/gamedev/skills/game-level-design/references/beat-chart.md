# The beat chart

Read this at step 3 and keep it open while charting. This is Valve's beat method as documented in the Level Design Book, and it is the one pacing procedure here that produces something a second person can check. Everything else about pacing is taste; this is an artefact with a failing condition.

## Contents

- [The four categories](#the-four-categories)
- [Plotting the chart](#plotting-the-chart)
- [Assigning intensity without it becoming a vibe](#assigning-intensity-without-it-becoming-a-vibe)
- [A worked chart](#a-worked-chart)
- [The check](#the-check)
- [Failure shapes](#failure-shapes)
- [Charting a level that already exists](#charting-a-level-that-already-exists)

## The four categories

Every segment of the level goes into exactly one of these. A segment that seems to be two is usually two segments.

| Category | The player's activity | Typical examples |
| --- | --- | --- |
| Explore | Moving through space, orienting, finding the route | A traversal sequence, a hub the player reads, a descent with nothing hostile in it |
| Combat | Fighting | An arena, an ambush, a running retreat under fire |
| Choreo | Watching something scripted | A set piece, a collapse, an NPC doing something the player cannot interrupt |
| Puzzle | Solving something | A mechanism, a route that has to be worked out, a physics problem |

Two rules keep the categories honest. First, categorise by what the player is doing, not by what the space contains: a corridor with two enemies in it that the player sprints past is Explore. Second, forcing a choice is the point — a segment that resists categorisation is usually one that has no clear job, and that is a finding rather than a limitation of the method.

## Plotting the chart

Time runs along the horizontal axis; intensity runs from 0 to 100% on the vertical. Each segment is a block on the chart, labelled with its category, spanning the time it takes and drawn at the intensity it reaches.

Use estimated play time for the horizontal, not segment count. A three-minute explore and a twenty-second one are different design objects, and a chart drawn per segment hides the difference precisely where it matters.

## Assigning intensity without it becoming a vibe

Intensity is a judgement, so anchor it rather than arguing about it. Fix two reference points first — the quietest segment in the level and the loudest — put them at their values, and place everything else relative to those two. Then sanity-check each value against something observable:

- **Threat.** Can the player be killed here, and how quickly.
- **Time pressure.** Is there a clock, a collapse, a pursuit.
- **Cognitive load.** How many things does the player have to hold in mind at once.
- **Noise.** How loud is it, visually and audibly.

Two people charting the same level should agree within about 10 percentage points per segment. If they do not, the disagreement is usually about what the segment is for, which is worth more than the number.

## A worked chart

A short level, roughly twelve minutes:

| Segment | Category | Time | Intensity |
| --- | --- | --- | --- |
| Arrival, reading the district from a high walkway | Explore | 0:00-1:30 | 15% |
| First contact, two enemies, open ground with three routes | Combat | 1:30-3:00 | 55% |
| Wading the flooded underpass, one landmark visible ahead | Explore | 3:00-4:30 | 20% |
| Pump mechanism, two valves, no threat | Puzzle | 4:30-6:30 | 35% |
| Water drops, the structure shifts, a route opens | Choreo | 6:30-7:00 | 45% |
| Arena, vertical routes, resources forward of the player | Combat | 7:00-9:30 | 85% |
| Retreat along the drained channel under fire | Combat | 9:30-11:00 | 95% |
| The exit, quiet, the landmark from 3:00 now behind the player | Explore | 11:00-12:00 | 10% |

The two adjacent combats at 7:00 and 9:30 are a deliberate crescendo: the second is a different shape — a retreat rather than a hold — and it climbs rather than repeating. That reason belongs on the chart in writing. Without it the check below fails, and it should.

## The check

**The same category must not repeat back to back without a deliberate, written reason.**

That is the gate. It is checkable by someone who did not build the level, which is what makes it useful. A reason has to say what is different about the second segment, not merely that it is longer or harder: "a second arena fight with more enemies" is the repeat, not an answer to it.

## Failure shapes

Four patterns show up on finished charts often enough to name:

- **The plateau.** Five segments in a row between 60% and 70%. Nothing is a peak because everything is, and players remember none of it.
- **The saw.** Intensity alternating violently every segment, with no sustained climb. Reads as noise rather than rhythm, and the peaks stop landing.
- **The late spike.** A flat first half and everything interesting in the last third. This is the shape that produces "the pacing drags in the second half" as a complaint about the second half, when the fix is in the first.
- **The exploration hole.** Twenty minutes with no Explore segment above a minute. Players never get to orient, and the wayfinding complaints that follow are about pacing, not about signage.

## Charting a level that already exists

The method works backwards, and this is the most common way to use it. Play the level, or watch a recording, and write the segments down with timestamps as they happen — not from the layout in the editor, which will tell you what was intended rather than what occurs.

Chart first, diagnose second. A chart drawn after the diagnosis is a chart drawn to justify it, and the repeated category on it never gets fixed.
