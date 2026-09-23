# The risk register, and finding the one question

Read this at step 3, after the pitch is written and feasibility has been read against it. Everything here is about finding the single assumption that most needs testing, and then sizing a prototype to test only that.

## Contents

- [Building the register](#building-the-register)
- [Scoring an assumption](#scoring-an-assumption)
- [Picking the one question](#picking-the-one-question)
- [Sizing the prototype to the question](#sizing-the-prototype-to-the-question)
- [Worked examples by genre](#worked-examples-by-genre)
- [Why not a vertical slice](#why-not-a-vertical-slice)

## Building the register

List every statement the pitch depends on being true, one per row, in the form "if this is false, the pitch does not work". Pull them from all four parts of the pitch and from the feasibility read: the fantasy landing with players, the target player actually preferring this to what they already play, each comparable's borrowed dimension working the way it does in its source game, and each feasibility axis that scored weakly.

Write assumptions as falsifiable statements, not as hopes. "Players will find the mechanic fun" is not falsifiable as written; "players complete a fifteen-minute session without being told the controls" is. A register full of hopes cannot be scored, because nothing on it can turn out to be wrong in a way anyone would notice.

## Scoring an assumption

For each row, score two things independently:

- **Probability of being wrong.** Not "how confident am I" stated as a feeling, but what evidence exists either way — has this team, or any team, done this before; does a comparable game's postmortem say anything about it; has anyone tested even informally.
- **Cost if wrong.** What breaks if this assumption fails. Some assumptions being wrong means a design tweak; others mean the entire pitch has no game inside it. A cheap mechanic tuning number scores low here even if it is likely to need adjustment; a core technical dependency scores high even if the team is fairly confident about it, because confidence and cost are different axes.

Multiply, or simply rank by the combination — precision here is not the point, separation is. The register's job is to make the worst combination visible, not to produce a defensible number.

## Picking the one question

Take the single row with the worst combination of probability and cost, and that is the prototype's job. Resist the pull toward the row that is easiest, most fun, or most flattering to test instead — a team drawn to prototype the art direction when the register says the netcode is the real risk is choosing comfort over information, and it is the single most common way this step goes wrong.

If two rows tie for worst, that is worth naming rather than averaging away: it usually means the pitch is making two independent risky bets at once, and the honest response is often to descope one of them before prototyping, not to build a prototype that tries to answer both and answers neither cleanly.

## Sizing the prototype to the question

The prototype is the smallest thing that could make the chosen assumption false, built in whatever form answers that fastest — not the smallest thing that looks like the eventual game. A prototype sized to the question is usually smaller, uglier and faster to build than anyone on the team expects, and that is the signal it is sized correctly rather than under-scoped.

Name explicitly what the prototype will not include, and revisit that list if the build starts growing toward polish — scope creep toward a demo is the usual way a correctly sized prototype turns back into an expensive vertical slice by accident, one reasonable-sounding addition at a time.

## Worked examples by genre

| Pitch's core new idea | Likely riskiest question | What actually gets built |
| --- | --- | --- |
| A new movement mechanic in an otherwise familiar platformer | Is the mechanic fun on its own, with no level design dressing it up | One grey-box room, the mechanic, nothing else — no art, no enemies, no progression |
| A social deduction game for a new platform's input model | Can the platform's input express the core interaction at all | The interaction alone, tested with real input hardware, no game loop around it |
| A four-player networked round-based game from a team with no netcode experience | Does the networking model hold up at the target player count and round length | Two to four boxes talking over a real network connection, no gameplay content, just the sync |
| A narrative game whose pitch rests on an emotional beat | Does the beat land for someone who has not been in the room while it was written | The single scene carrying the beat, shown to someone outside the team, nothing before or after it |
| A roguelike whose pitch rests on build variety | Does the run-to-run variance actually feel different, or do runs converge on one dominant strategy | A handful of runs through the core loop with placeholder content standing in for the eventual build pool |
| A mobile F2P game whose pitch rests on a specific monetisation hook | Will the target player actually engage with the hook at all, before any economy is tuned | A landing page, a handful of player interviews, or a paper-prototype economy — sometimes no code at all |

## Why not a vertical slice

A vertical slice answers "can this team produce content at this quality bar, from front to back". That is a real question, but it is almost never the riskiest one on a fresh pitch's register, because production capability is usually the thing the team has the most direct evidence about already — from their last project, their reel, their portfolio. The riskiest row is usually something the team has never done before, which a vertical slice does not stress-test at all: it dresses the safest assumption in the most expensive clothes.

A vertical slice is also slow to build precisely because it is trying to look finished, which means the team spends its prototype budget on art, polish and integration before it has any evidence the core bet pays off. If the riskiest question turns out to be a no, the vertical slice's cost is sunk for nothing; a prototype sized to the actual question is cheap enough that a no-go there is a cheap lesson rather than a wasted milestone.
