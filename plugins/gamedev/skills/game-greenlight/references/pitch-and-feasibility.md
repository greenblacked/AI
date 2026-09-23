# The pitch, and reading feasibility against it

Read this at steps 1 and 2, before a risk register exists. The pitch has to be written down in a form specific enough to be wrong before feasibility can be read against it honestly — a vague pitch is feasible for whatever the reader imagines, which is not the same as feasible for what is actually being proposed.

## Contents

- [The four-part pitch](#the-four-part-pitch)
- [What each part protects against](#what-each-part-protects-against)
- [The feasibility matrix](#the-feasibility-matrix)
- [A worked read](#a-worked-read)
- [What feasibility is not](#what-feasibility-is-not)

## The four-part pitch

One page, no more, in this order:

1. **The fantasy, in one sentence.** What the player gets to feel or be, stated as an experience rather than a feature list — "you are the last engineer keeping a dying ship alive", not "a survival crafting game with a ship system". A fantasy that takes a paragraph to state is usually two ideas competing for the same pitch.
2. **The target player, and why them.** Name who this is for and what they currently play instead, specifically enough that a stranger could recognise that player in a room. "Everyone" is not a target player; it is the absence of one, and it is usually a sign the fantasy in part one was never actually decided.
3. **Three comparables**, each in the shape "plays like X, but Y" — a known game for the loop, and the one dimension this pitch changes. Three rather than one, because a single comparable reads as a clone and a single comparable also hides which dimension is actually new. Three comparables that share no dimension in common usually means the pitch has not decided what game it is.
4. **Why this team, why now.** The specific capability, timing or unfair advantage that makes this team's version worth building rather than someone else's — a technology just became available, the team shipped something adjacent, a market shifted. A pitch with no answer here is not disqualified, but it is the one honest sentence that gets skipped most often and is missed most when the feasibility read turns up thin on the team axis.

## What each part protects against

The fantasy line stops the team from discovering three sentences into pre-production that the programmer and the artist have been building different games. The target player line stops the pitch from being judged against an imaginary audience of everyone, which is the audience every idea sounds good to. The three comparables force the pitch to say what it actually is, rather than relying on adjectives — "innovative", "fun", "different" — that a feasibility read cannot act on. The why-now line is the one that catches an idea that was feasible eighteen months ago and has since been made moot by a competitor, a platform change, or a technology that is no longer scarce.

## The feasibility matrix

Read each axis independently before combining them. A pitch that fails badly on one axis is not rescued by scoring well on the other four — the axis that fails worst is the one the greenlight decision has to answer, and it is often the same one the riskiest-question step in the next reference picks up.

| Axis | Read it against | A pitch that fails here looks like |
| --- | --- | --- |
| Team | Who on the team has shipped this genre, this scope, or this technology before — not who is willing to learn it | Everyone on the team is learning the genre and the technology at the same time, on the only project the team can afford to fail |
| Time | The actual deadline, whether external (a publisher milestone, a platform window) or self-imposed, and what fraction of it the prototype alone would consume | A prototype budgeted at a third or more of the total schedule, leaving no time to build the game the prototype proves is worth building |
| Money | What a no-go costs against what a go costs, stated in whatever the team's actual currency is — runway, a publisher's advance, unpaid overtime | Nobody has said out loud what happens to the team if this is a no-go, so the no-go option is not actually available |
| Platform | Whether the target platform's real constraints — input method, screen size, store policy, certification requirements — shaped the fantasy, or whether the fantasy was designed first and a platform assumed afterward | A touch-first mechanic pitched for a platform whose control scheme cannot express it, discovered after the prototype is built rather than before |
| Technical risk | Whether any piece of the pitch — netcode at a stated player count, procedural generation at a stated quality, a simulation at a stated scale — has been built by anyone on this team before, on any project | The pitch depends on a technology nobody on the team has built, and the plan does not mention de-risking it before the rest of the prototype is built around it |

## A worked read

Pitch: a four-player, sixty-second round battle-royale-lite for mobile, pitched by a three-person team that has shipped two single-player puzzle games and never a networked game.

- **Team.** Fails. Nobody has built netcode of any kind. This is not disqualifying on its own, but it means the technical-risk axis below is not a guess, it is the central bet of the whole pitch.
- **Time.** A six-week self-imposed deadline before the team's savings run out. A prototype that spends more than a week or two of that on the core loop leaves no time to build anything the prototype justifies.
- **Money.** Explicit: a no-go means the team returns to contract work for six months and tries again. Written down, so the team can actually choose it rather than avoid naming it.
- **Platform.** Mobile touch input for a genre usually built for a controller or mouse-and-keyboard aim model. Untested, and worth naming as a second technical risk rather than assuming touch aiming will feel fine.
- **Technical risk.** The one that decides the pitch. Four-player real-time networking at a low round length is exactly the kind of thing that looks simple in a pitch deck and consumes months in practice.

Read together, this pitch's riskiest question is not "is the loop fun" — it is "can this team get four phones talking to each other with acceptable latency at all". The next reference, `prototype-question.md`, picks up from here and shows how that reading turns into a prototype scope.

## What feasibility is not

Feasibility is not a vote on whether the idea is good. A brilliant idea can be infeasible for this team at this time, and a mediocre idea can be entirely feasible — feasibility answers "can we", not "should we", and the two get conflated most often when a team wants an idea to be true. Keep the feasibility read and the fantasy's appeal in separate columns; a pitch deck that blends them into one score is usually hiding a weak feasibility read behind an exciting fantasy.
