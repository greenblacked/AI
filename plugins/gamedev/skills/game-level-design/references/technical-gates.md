# Technical gates that shape a layout

Read this at step 6, and again before the layout is signed off. Both gates below are engine facts that constrain where rooms meet. They are here because retrofitting either one means re-authoring macro-structure: the level does not get a performance problem you can optimise, it gets a shape that has nowhere to put a seam.

## Contents

- [Source engine: an areaportal on every windowless door](#source-engine-an-areaportal-on-every-windowless-door)
- [UE5 World Partition: cell size and loading range](#ue5-world-partition-cell-size-and-loading-range)
- [What this skill owns and what it hands over](#what-this-skill-owns-and-what-it-hands-over)

## Source engine: an areaportal on every windowless door

Attach an areaportal to every door that has no window in it.

The reason this is a layout rule rather than a technical chore is that a door in this engine is two things simultaneously. As gameplay it is a chokepoint: a threshold the designer controls, where the player commits, where an encounter can be gated. As rendering it is a visibility-culling seam: a closed areaportal lets the engine stop drawing everything behind it, which is how a level made of rooms stays affordable.

The consequences for layout fall out of that:

- **A level with no windowless doors has nowhere to put its seams.** An open-plan layout that reads well in a blockout can be one the engine cannot cull, and the fix is not a setting — it is walls and doors that were not in the design.
- **A window in a door removes the seam.** The portal cannot close if the player can see through it, so a design decision about sightlines is also a decision about culling, and the two are usually made by different people at different times.
- **Retrofitting means re-authoring macro-structure.** Adding the chokepoints late changes where rooms meet, which changes routes, which changes the encounters built on those routes. That is why this belongs at blockout and not at optimisation.

Practical check while the level is still boxes: walk the layout and mark every place where the player transitions between two enclosed volumes. Each mark is either a door that can carry a portal, or a place where the design has decided to pay for drawing both volumes at once. Both are acceptable; only one of them being accidental is not.

## UE5 World Partition: cell size and loading range

Two figures to design against, with their provenance marked:

| Setting | Guidance |
| --- | --- |
| Loading range | At least twice the cell size |
| Loading range, fast movement | Three to four times the cell size, for vehicles, flight or anything similarly quick |
| Default cell size | 256 m |

**Provenance.** These are corroborated across community sources rather than read from Epic's primary documentation, which could not be reached when this was written. Treat them as a starting point to verify against the project and the engine version in use, not as a specification. Where a number here disagrees with something measured in the project, the measurement wins.

The layout consequences are what matter here:

- **Fast traversal costs loading range, and loading range costs memory.** A level that lets the player drive or fly across it is asking for a larger range around the player at all times. Deciding late that a vehicle route exists is a streaming decision disguised as a design one.
- **Cell boundaries are seams the player can feel.** A hitch, a pop, or an actor appearing late lands at a boundary. Route the player's high-attention moments — a reveal, a fight, a scripted beat — away from the places where the level is busiest loading.
- **Cell size interacts with how big the level's rooms are.** Spaces much smaller than a cell mean many rooms load together whether or not they are visible; spaces much larger than a cell mean a single room spans several. Neither is wrong, but the relationship should be a decision.

## What this skill owns and what it hands over

This skill owns the layout consequence: where the seams fall, whether the shape of the level gives them somewhere to be, and what changes in the design when the answer is no.

Everything downstream of that belongs to `game-performance` in this plugin — converting the target frame rate into a millisecond budget, capturing frame times from a real build on the target device, proving whether the frame is CPU-bound or GPU-bound, and the optimisation pass itself. Bring that skill a layout whose seams were placed deliberately, and it has something to work with. Bring it one where they were not, and its first finding will be a structural change this skill should have made.
