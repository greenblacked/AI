# Player metrics and the blockout grid

Read this at step 1, before any geometry exists, and again whenever a new engine or a new character controller enters the project. A metrics table is the cheapest document in level design and the one whose absence is most expensive: without it every dimension in the level is a judgement made in a viewport, and every judgement is wrong in a way that only shows up when someone tries to walk through it.

## Contents

- [The checklist](#the-checklist)
- [The Source engine worked example](#the-source-engine-worked-example)
- [Deriving the same numbers in another engine](#deriving-the-same-numbers-in-another-engine)
- [The blockout grid](#the-blockout-grid)
- [What changing the metrics later actually costs](#what-changing-the-metrics-later-actually-costs)
- [Publishing the table](#publishing-the-table)

## The checklist

Fix every one of these before placing geometry. A blank entry is a number someone will invent on the spot.

| Metric | Why the level depends on it |
| --- | --- |
| Standing height | Ceiling heights, every opening, the point at which a space reads as cramped |
| Crouching height | Crawlspaces, cover the player can hide fully behind, low entrances |
| Step height | Whether stairs, debris and kerbs are climbable without a jump input |
| Jump height | Ledges, ceilings the player can reach, what is reachable by accident |
| Jump distance | Gap widths, whether a shortcut exists that the layout did not intend |
| Walk speed | How long a corridor takes, which is how long a quiet beat lasts |
| Sprint speed | Chase distances, whether a retreat route is survivable |
| Camera height | What is visible over cover, and what a landmark has to clear to be seen |
| Cover height | Whether a player standing is exposed and crouching is not |
| Door width | Whether two characters pass, and whether combat can flow through the gap |
| Blockout grid | The unit every dimension above is expressed as a multiple of |

Two of these are frequently forgotten and both cost structure. Camera height is not the same as standing height, and a landmark sized against the wrong one is invisible from where the player actually looks. Step height decides whether a piece of terrain is traversable at all, and a level built without it ends up with informal walls made of eight-unit kerbs.

## The Source engine worked example

These are published on the Valve Developer Community wiki. Cite them for the relationships, not as numbers to paste into another engine.

| Dimension | Value |
| --- | --- |
| Standing bounding box height | 72 units |
| Crouching bounding box height | 36 units |
| Minimum walkable opening | 73 units |
| Standard door | 56 x 112 units |

Three things in that table are worth reading as design, not trivia:

- **Crouching is exactly half standing.** A clean ratio makes every derived dimension checkable by eye: cover at 36 units hides a crouching player completely and a standing one not at all, and that is a fight rule expressed as geometry.
- **The walkable opening is 73, one unit more than the 72-unit box.** The slack is deliberate. A metrics table carries that unit; a screenshot of a doorway does not, and a level built to exactly 72 produces collision snags nobody can explain.
- **The standard door is much larger than the player.** 56 wide by 112 tall against a 72-unit standing height is not realism, it is legibility and flow — a doorway at human proportions reads as a tunnel on screen and becomes a bottleneck in combat.

## Deriving the same numbers in another engine

Measure them; do not look them up. For Unreal in particular, community sources disagree about the default capsule dimensions and there is no single authoritative document that settles it, so a figure recalled from a forum post is a figure that will be wrong in a way nobody notices until a doorway is built to it.

The measurement is mechanical:

1. Place the character controller in an empty scene on a known grid.
2. Read standing and crouching height off the collision capsule or bounding box, not off the mesh — the mesh is art and can overhang.
3. Walk into a staircase of increasing step heights and record the tallest one the controller climbs without a jump.
4. Jump at a wall of increasing ledges and record the highest one gripped; jump across gaps of increasing width and record the widest cleared reliably, not the widest cleared once.
5. Time a run across a known distance for walk and sprint speed, in units per second, and convert into the level's grid unit.
6. Read camera height from the view transform while standing and while crouched.

Record the engine version and the controller settings beside the table. When either changes, the table is provisional again.

## The blockout grid

Pick one unit and make every dimension a multiple of it, then step the grid down as the level's remaining questions get smaller. The Level Design Book documents Quake's progression: 64 for massing, 32 as rooms firm up, 16 as connections resolve, 8 for detail.

| Grid | What is still being decided at this stage |
| --- | --- |
| 64 | Where the rooms are, how many there are, how they connect |
| 32 | Room shapes, the main routes through each |
| 16 | Cover placement, elevation changes, sightlines |
| 8 | Detail geometry, thresholds, trim |

Going to 8 early is the common mistake, and it does not look like a mistake: the level looks more finished at every step. What has happened is that the macro-structure got expensive to move before anyone decided it was right, so the layout stops changing for a reason that has nothing to do with the design.

## What changing the metrics later actually costs

State this precisely, because the imprecise version is the one that gets repeated and it is not supported.

**Documented, for modular kits.** Joel Burgess and Nate Purkeypile, "Skyrim's Modular Approach to Level Design" (GDC 2013), describe a late change to the kit's tile grid meaning the existing kit no longer fitted levels that had already been built with it. When the level is assembled from snapping pieces, the grid is a contract between every piece and every level, and changing it invalidates the contract everywhere at once.

**Generalised, for hand-built levels.** The same mechanism plausibly applies — dimensions derived from a metric all become wrong together when the metric moves — and it is a good reason to fix the metrics first. It is not independently demonstrated in the published sources, and presenting it as documented fact overstates what is known. Say "this is why it is done" rather than "this has been shown".

## Publishing the table

Put the table where the level designers work, not in a design document nobody opens: a text file beside the levels, a wall of the blockout scene built to each dimension, or both. A reference room containing a standing figure, a crouching figure, the standard door, a climbable step, a maximum jump gap and a cover piece is worth more than the numbers alone, because it lets a designer check a space by standing in it.
