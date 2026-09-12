---
name: game-balance
description: "Tune a game's numbers against evidence rather than taste, and run playtests that produce signal. Names what balanced means for this game before changing anything — near-equal win rates for a symmetric competitive game, a rising difficulty curve for a single-player one, a spread of viable builds for a roguelike — then instruments win rate by skill band, pick rate against win rate, time-to-kill and where players stop, checks the sample is big enough to act on, kills dominant strategies with a cost curve, and ships one change per patch with a window to read it. Use this skill whenever someone says a weapon, unit, deck, class or build is overpowered or useless, asks whether a difficulty curve is right, wants win-rate or pick-rate numbers interpreted, or is running a playtest. Not for building a game or tuning its feel, its frame budget, its netcode, or server capacity."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(python3:*)
---

# Game Balance

Every number that changes, changes for a written reason, against a target somebody chose in advance, with enough observations behind it that the next patch can tell whether it worked.

Balance is a measurement problem before it is a design problem, and almost every balance pass that makes a game worse went wrong before the first number moved. Either the target was wrong — fairness imposed on a game whose appeal is asymmetry, or an even win rate demanded of a single-player campaign — or the reading was wrong: forty matches of noise treated as a trend, two skill bands averaged into a number describing neither, four nerfs shipped together so the next reading cannot attribute anything. This skill exists to put those three in order: decide what balanced means, measure until the measurement means something, then change one thing.

## Scope

Use for: deciding what balanced means for a specific game, designing the telemetry that would show it, reading win-rate and pick-rate data, sizing and sequencing balance changes, difficulty and economy curves, dominant-strategy and dead-content checks, and running playtests that produce evidence rather than opinions.

Do not use for: building a game or a prototype, or tuning how it feels to control — that is `game-builder`. Frame budget and performance, netcode and latency, and server-side capacity or telemetry are each someone else's job; a 200 ms hit that does not register is a netcode problem no damage number fixes.

## Workflow

### 1. Name the target before touching a number

Say what balanced means for this game, in one sentence, and write it where the patch note will go. The wrong target is the most common cause of a balance pass that makes the game worse, and it is invisible afterwards because every individual change looked reasonable.

| Game shape | Balanced means | The reading that says so |
| --- | --- | --- |
| Symmetric competitive | Near-equal win rates at equal skill | Win rate per faction per skill band, inside a stated band |
| Asymmetric competitive | Everything is best at something and nothing is best at everything | Pick rate against win rate per option, plus presence rate where bans exist |
| Single-player campaign | A difficulty curve — rising demand with rest, not fairness | Completion and death rate per encounter, attempts-to-clear distribution |
| Roguelike or build game | A spread of viable builds, not identical ones | How many distinct builds clear above a stated success floor |
| Co-op or PvE | The group is threatened and no single role is mandatory | Clear rate per composition, and whether any role appears in every clear |
| Economy or progression | Earning and spending stay in a corridor across the play span | Currency per hour against sinks, over a player's lifetime rather than a session |

Then fix the acceptable band in the same breath — "no faction outside 48 to 52 per cent in the top skill band over a season" — before you look at the data. A band drawn after the fact is drawn around whatever you already wanted to nerf.

Two targets that look like balance and are not. A roguelike whose builds are evened out has had its reason to be replayed removed; the goal is that many builds can win, not that they win equally. A single-player game does not want fairness at all — it wants the player to lose in the places the design chose.

### 2. Instrument before you tune

Without telemetry the first deliverable is an event schema, not a nerf. Say that plainly rather than guessing from feel; a guess shipped as a patch is indistinguishable afterwards from a measurement, and it poisons the next reading.

The minimum set:

- **Win rate** by option, by skill band, and by patch version.
- **Pick rate**, alongside ban rate where the game has bans, because presence is pick plus ban.
- **Time-to-kill** and match length, as distributions rather than means — a bimodal TTK is two games wearing one costume.
- **Economy curves**: resource earned and spent per unit of time, per option.
- **Progression drop-off**: the encounter, level or run number where players stop and do not come back.

Every event carries the patch version, a match identifier, a hashed player identifier, the skill band at the time, the option's identity, and the outcome. Patch version is the one people forget, and without it a before-and-after comparison is impossible — which is the entire job.

Read `references/telemetry.md` at this step for the event schema, the metric definitions, and the traps that make an honest-looking number wrong.

### 3. Read the data before forming an opinion

**Pick rate against win rate, as two axes.** Each quadrant is a different problem with a different fix, and treating them as one is how a healthy niche option gets nerfed out of the game.

| | High win rate | Low win rate |
| --- | --- | --- |
| **High pick rate** | Genuinely too strong. Chosen often and winning when chosen. Nerf candidate. | A trap. Attractive, taught by the UI or the fantasy, and losing. Buff or stop advertising it. |
| **Low pick rate** | Usually a selection effect, not power: the few who pick it are specialists or pick it only when it already suits. Compare their win rate on everything else before acting. | Dead content. A buff or a new job, never a nerf. |

**Split by skill band, always.** An option can be weak in casual play and dominant at the top, and the average describes neither. Nerfing on the average punishes the majority for something only the top band can do; ignoring the top band lets one option define the competitive game. Decide which band the target applies to, in step 1.

**Check the sample before you believe it.** Near a 50 per cent win rate, the 95 per cent margin on `n` observations is about `100 / √n` percentage points.

| Observations | Margin | Means |
| --- | --- | --- |
| 40 | ±16 | Nothing is measurable |
| 100 | ±10 | Only a landslide shows |
| 400 | ±5 | A 5-point gap is at the edge of visible |
| 1,100 | ±3 | A 3-point gap is visible |
| 10,000 | ±1 | Fine tuning is possible |

Worked: 22 wins in 40 matches is 55 per cent, and the margin is 100/√40 = ±15.8 points, so the true rate is somewhere between about 39 and 71 per cent. Two results the other way make it 20 of 40 and the signal is gone entirely. To call a 5-point deviation real you need about (100/5)² = 400 matches; for 3 points, about (100/3)² = 1,100.

Three corrections to that rule, all of which make the requirement larger:

- Comparing two options against each other, rather than one against 50 per cent, needs roughly twice as many observations per side.
- Splitting by skill band divides the sample. 1,200 matches across five bands is 240 each, a margin of ±6.5 points — so a per-band read needs a total several times larger, and the top band is always the thinnest part of it.
- Checking thirty options at 95 per cent confidence produces about 30 × 0.05 = 1.5 false alarms every patch. Something will look significant. Require a larger margin when you are scanning rather than testing a specific suspicion.

### 4. Check for dominance before tuning the number

If option A is at least as good as option B everywhere — every cost, every matchup, every stage of the game — then B is dead content whatever its win rate says, and a 5 per cent buff moves nothing. B needs a different job, not a bigger number. This check is arithmetic on the design, not on the telemetry, and it can be done before a single match is played.

The same check across a cost curve: plot each option's power against its cost and expect a rising line with diminishing returns, because a player fields fewer expensive things and flexibility has value. Fit the line to options with healthy pick rates only; fitting it to everything lets dead content drag the curve down to meet it.

Read `references/cost-curves.md` before proposing a cost or power change, for how to fit the curve, the vanilla test, and why cheap units win by default in any game where numbers compound.

### 5. Change one thing, size it, and give it a window

One change per option per patch. Two simultaneous nerfs make the next reading uninterpretable — the win rate moved four points and nothing on the sheet says which change did it, so the next patch is guesswork built on guesswork. Where a whole category is out of line, that is one change to the category, not six changes to six members.

Size the change small. Until you have a house conversion factor, halve the change you first thought of: an overcorrection produces a second patch, and two patches in opposite directions cost more trust than one patch that did too little. Build the factor by recording, for every patch, the size of the change and the win-rate movement it produced; after five patches the table tells you what a 5 per cent cooldown change is worth in this game.

Write the prediction before shipping: "this should move the top-band win rate from 56 to about 52 per cent within 1,500 matches". A patch with no written prediction cannot turn out to be wrong, so it teaches nothing.

Then give it a window. Discard the first days after release — novelty inflates pick rate and depresses win rate while everyone tries the new thing badly — and collect until the count reaches what step 3 demands before reading. If the game does not produce that many matches in a sensible window, that is the real finding: the game cannot support tuning at that precision, and the change has to be large enough to see or not worth making.

Decide the nerf-or-buff policy once and hold it. Buffing everything around an outlier reads as generous and compounds into power creep, shorter time-to-kill and a harder game to balance every season. Nerfing the outlier holds the ceiling and annoys precisely the players who liked it. Both are defensible; alternating between them without a policy is not.

### 6. Playtest for what telemetry cannot see

Telemetry says what happened and never why. The player who stopped at level four is a number; the reason they stopped is a thing you have to watch someone do.

Watch, do not ask. What players say they want and what they do diverge, reliably and in a known direction: they ask for the thing that just killed them to be weaker, and they report the parts they remember rather than the parts that decided the session. The protocol is in `references/playtesting.md` — read it before scheduling a session, because the recruiting and the room setup are decided in advance and cannot be fixed afterwards.

The short version: sit beside and slightly behind, out of their eyeline. Say nothing while they play, including when they are stuck and especially when they ask a question — the game will not be there to answer it either. Record time to first input, time to first death, time to the moment they visibly understand, every question asked aloud, and every point where they did something the design did not anticipate. Afterwards, ask what they were trying to do at a specific moment and what they expected to happen, not whether they enjoyed it or what should be added.

A first-session test and a retention test are different instruments. The first measures comprehension and hook, takes one sitting, and burns the tester — nobody has a first session twice. The second measures whether the loop survives repetition, needs days rather than hours, and its only honest metric is whether they came back unprompted.

Five testers find most comprehension problems. No number of testers you can fit in a room finds a balance problem; that is what step 2 is for.

### 7. Write the decision down

Per change, in the tracker or the patch note:

```markdown
## [Option] — [the change in one line]
- Target: [what balanced means here, and the band from step 1]
- Observation: [the metric, the value, n, and the margin]
- Read: [which quadrant, which skill band, what was ruled out]
- Change: [the one number, old to new]
- Prediction: [the metric, the expected value, and the window in matches or days]
- Result: [filled in after the window, including "no measurable effect"]
```

The result line is the one that compounds. A balance team that fills it in has a conversion factor after a season; one that does not is guessing from scratch every patch.

## Anti-patterns

**Balancing off the forum.** Losing is memorable and winning is not, so complaints are a record of what killed people, not of what is strong. The player who was beaten by a thing posts; the player quietly winning with it does not. Use the forum to generate hypotheses and the telemetry to test them.

**Nerfing the loudest thing.** The loudest thing is usually the most visible one — a flashy execution, a long stun, a card with a memorable name. Visibility and strength are not the same axis, and the correlation between them is weak enough to be worthless.

**Tuning for the top 0.1 per cent.** A combo that requires frame-perfect input in a game whose players do not play at that level is a balance problem for about forty people and a fun problem for everyone else. Tune the band where the players are, and handle the top band with the rules the top band plays under.

**The simultaneous patch.** Four changes, one reading, no attribution. The next patch inherits the ambiguity and doubles it.

**Nerfing a low-pick, high-win option.** Its win rate is contaminated by who picks it. Compare those players' win rate on everything else first: if they are up ten points across the board, the option is not the cause.

**The average across skill bands.** A unit weak in casual play and dominant at the top averages to fine, and the average describes no player who exists.

**Reading the first weekend.** Novelty moves every metric in a known direction for a few days. A patch read on day one is read on the least representative data the patch will ever produce.

**Balancing a game nobody has played enough.** Before there is volume, the honest work is dominance checks and comprehension playtests. A win rate over internal testing is forty matches of noise with a spreadsheet around it.

**Asking players what to change.** Players are expert witnesses to their own experience and poor designers of the fix. "This feels unfair" is data; "reduce its damage by 15" is not.

## References

- `references/telemetry.md` — read at step 2 and step 3: the event schema, the metric definitions, the two-axis read in full, skill bands, and the traps that make an honest number wrong.
- `references/playtesting.md` — read before scheduling a session: recruiting, room setup, the silence rule, what to record, the questions worth asking afterwards, and the first-session versus retention distinction.
- `references/cost-curves.md` — read at step 4 before proposing a cost or power change: fitting the curve, the vanilla test, dominance and role checks, and why cheap options win by default.
