# Writing kill criteria before the prototype exists

Read this at step 5, once the prototype's scope is set and before it is built. A kill criterion is a promise about how the decision will be made, written while nobody yet knows what the prototype will show — which is the only point at which it can be written honestly.

## Contents

- [What makes a criterion real](#what-makes-a-criterion-real)
- [The three outcomes](#the-three-outcomes)
- [Criteria that failed to constrain anything](#criteria-that-failed-to-constrain-anything)
- [Pivot versus an undeclared no-go](#pivot-versus-an-undeclared-no-go)
- [Who signs, and where it lives](#who-signs-and-where-it-lives)

## What makes a criterion real

A criterion is real when a specific, anticipated result would force the team to accept an outcome they do not want. If every plausible result of the prototype can be read as a go by someone motivated to read it that way, the criterion was not a criterion — it was a formality.

Three properties, all required:

- **Observable.** Something that can be measured or clearly seen, not a feeling — "at least six of eight playtesters complete the loop without being told the controls", not "the loop feels intuitive".
- **Set before the data exists.** Written before the prototype is played, ideally before it is built, and changed only with the same visibility the original criterion had — quietly moving the bar after seeing early results is the exact failure this step exists to prevent.
- **Attached to a consequence.** Each of go, no-go and pivot names what happens next, not just what was observed. A criterion with no attached action is a measurement, not a decision.

## The three outcomes

Write all three before the prototype starts, even though writing the no-go criterion is the uncomfortable one and the one most often skipped:

- **Go.** The specific result that means the riskiest assumption held up well enough to proceed to `game-design-doc`. Usually the easiest of the three to write, and the one everyone wants to write first — write it, then make yourself write the other two with equal rigour.
- **No-go.** The specific result that means the assumption failed badly enough that continuing is not defensible. Naming this in advance is what makes a no-go later survive the pull of sunk cost — the team is not being asked to admit the idea was bad, they are honouring a decision they already made while thinking clearly.
- **Pivot.** The specific result that means part of the pitch held and part did not — the fantasy landed but the mechanic did not, or the mechanic works but not for the target player named in step 1. A pivot criterion should say what changes (the mechanic, the platform, the target player) and what does not, so the next pass through step 1 starts from what survived rather than from nothing.

## Criteria that failed to constrain anything

Each of these reads as rigorous and constrains no one:

**"We'll know it when we see it."** Not a criterion. It defers the decision to whoever is most persuasive once the room has already formed opinions, which is the exact failure this whole step exists to prevent.

**"If it's not fun, we'll stop."** Unfalsifiable as written — "fun" has no observer, no threshold and no method. Replace with what fun would look like from the outside: session length without prompting, an unprompted second playthrough, a specific behaviour a playtester was not told to try.

**"We'll ship it if the team still believes in it."** Team belief after weeks spent building the thing is not independent evidence; it is the sunk-cost effect this step exists to route around, restated as a criterion.

**A threshold nobody would actually enforce.** "Less than 20% of testers finish" sounds precise, but if the team has privately agreed they will build the game regardless, the number is theatre. A criterion is only real if a bad result was genuinely allowed to happen — decide, honestly, whether a no-go is actually on the table before writing one that pretends it is.

## Pivot versus an undeclared no-go

A pivot changes one named part of the pitch — the mechanic, the platform, the target player, the technical approach — while keeping the rest, and it returns to step 1 with a revised pitch that says explicitly what changed and why. An undeclared no-go dressed as a pivot changes everything and calls it iteration, which lets a team avoid ever formally saying an idea did not work while quietly starting over.

The test: if the new pitch's fantasy, target player and comparables are all different from the original, it is a no-go followed by a new pitch, not a pivot. Naming it correctly matters because a string of undeclared no-goes reads, from outside the team, as a project that is always about to be great — which is a harder pattern to stop than a single clear no-go.

## Who signs, and where it lives

Write the criteria into whatever document the eventual decision will be read against — the pitch deck for a publisher pitch, the stage-gate document for a formal gate, a short note pinned wherever the team tracks decisions for a self-greenlit project. Name who is agreeing to be bound by it before the prototype starts; a criterion nobody signed is a criterion anyone can disown once the result is unwelcome.
