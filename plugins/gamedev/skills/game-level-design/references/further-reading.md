# Where the published material is, and what each source is good for

Read this when you want the source rather than the summary — before a decision that will be expensive to reverse, or when someone asks where a number in this skill came from. Every claim this skill makes with a number attached traces back to something in this list.

## The Level Design Book

A continuously maintained online book on level design as a craft. It is the source for two things this skill uses directly: the Quake blockout grid progression of 64, 32, 16 and 8 units as a level moves from massing to detail, and Valve's beat method — the four categories of Explore, Combat, Choreo and Puzzle, plotted as time against intensity.

It is also the clearest published statement that there is no formula for wayfinding, and that playtesting and watching where players go is the only way to know whether a level guides people. Read it when you want the general craft rather than one studio's practice.

## The four GDC talks

Each of these is a studio describing what it actually did, which is why they are cited here by name rather than paraphrased into anonymous best practice.

- **Joel Burgess and Nate Purkeypile, "Skyrim's Modular Approach to Level Design" (GDC 2013).** The documented case for fixing the kit's grid before building with it: a late change to the tile grid meant the existing kit no longer fitted levels already built. Read it before committing to a modular kit, and read it as the evidence for the metrics-first gate — it is the one place where the cost of changing the grid late is demonstrated rather than assumed.
- **David Shaver and Robert Yang, "Invisible Intuition: Blockmesh and Lighting Tips to Guide Players and Set the Mood" (GDC 2018).** The source of the stage gate on wayfinding: build guidance cues into the blockmesh and test them at blockmesh stage, before art. Read it for the specific techniques and for why testing them after art is testing them too late to act on.
- **Kurt Loudy and Jake Campbell, "Embracing Push Forward Combat in DOOM" (GDC 2018).** Arena design as a space problem: vertical routes, multiple ground routes so the player cannot be cornered, and resource placement that rewards moving towards the fight. Read it before building an arena, and note what it is not about — enemy statistics and difficulty are a different discipline.
- **Valve's Half-Life 2 playtesting practice**, described in Valve's own talks and writing: roughly 100 playtesters per chapter, with observation of behaviour rather than collection of opinion. Read it for the scale a studio brought to the problem, and for the absence of any threshold rule in it.

## Valve's developer commentary tracks

The commentary nodes in Half-Life 2, its episodes, Portal and Portal 2 are level design post-mortems delivered in the exact spot they are about. They are unusually valuable because the claim and the geometry are in the same place: a designer explains why a doorway was moved while you stand in the doorway.

Play them with the level open in an editor if you can. Read them for the causal chain from an observed playtest problem to a specific geometric change, which is the part that written post-mortems usually compress out.

## The Valve Developer Community wiki

The source for the Source engine numbers this skill quotes: the 72-unit standing bounding box, the 36-unit crouching box, the 73-unit minimum walkable opening and the 56 by 112 standard door, along with the areaportal documentation behind the windowless-door rule.

It is engine-specific and it is a wiki, so read it for the relationships between the numbers rather than treating the values as portable. The useful part is that the numbers are published and internally consistent, which makes them a good worked example of a metrics table when you are writing your own.

## Boss Keys, and what it is not for

Mark Brown's Boss Keys series is structural analysis of shipped levels — dungeon graphs, lock-and-key dependencies, how a Zelda dungeon branches and rejoins. It is genuinely good, and it is worth being precise about what it teaches.

It teaches reading a level: taking something finished apart and seeing its structure. It does not teach building one, and its graphs are a description of the result rather than a method that produces it. Read it to develop judgement about structure, not as a procedure to follow.

## A note on numbers found elsewhere

Unreal Engine capsule dimensions are the case that comes up most, and community sources disagree with each other with no authoritative document to settle it. The same applies to any figure quoted without a version attached. Measure it in the project, write down the engine version beside it, and treat any number from a forum as a hypothesis about what you will measure.
