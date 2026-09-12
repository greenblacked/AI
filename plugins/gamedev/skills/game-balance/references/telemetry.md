# Gameplay telemetry: what to collect and how to read it

Read this at step 2 when designing the event schema, and at step 3 before drawing a conclusion from a number. This is gameplay telemetry — what the players and the design did. Server health, traces and error rates are a different discipline and a different skill.

## Contents

- [The event schema](#the-event-schema)
- [The metric set](#the-metric-set)
- [Skill bands](#skill-bands)
- [The two-axis read](#the-two-axis-read)
- [How many observations](#how-many-observations)
- [Traps that make an honest number wrong](#traps-that-make-an-honest-number-wrong)
- [Single-player and roguelike readings](#single-player-and-roguelike-readings)
- [The four views worth building](#the-four-views-worth-building)

## The event schema

Three event families cover almost every balance question. Anything else is added because a specific question needed it, not in case.

| Event | Emitted when | Carries |
| --- | --- | --- |
| `match_end` | A match, run or level attempt finishes | Outcome, duration, mode, map or seed, patch version, one row per participant |
| `participant` | Once per player per match | Hashed player id, skill band at start, option chosen (faction, class, deck, build), final score, outcome |
| `event` | A tuning-relevant moment inside a match | Type (kill, death, purchase, ability use, checkpoint, quit), timestamp offset, actor, target, option, cost |

Every one of them carries the patch version and a monotonic schema version. The patch version is what makes before-and-after possible; the schema version is what stops a silently changed field from making six months of history incomparable.

Hash the player identifier with a per-game salt and keep it stable across matches. Stability is what lets you ask whether the same players who pick a low-pick option are also winning with everything else, which is the single most useful correction in this file. Do not store names, addresses or anything the balance question does not need.

Record the option's identity as an identifier, not a display name. Display names get localised and renamed and the history breaks.

## The metric set

**Win rate.** Wins over decided matches. Report it per option, per skill band, and per patch. Never report it without the count beside it; a win rate with no `n` is an opinion in a table.

**Pick rate.** Matches where the option was chosen over matches where it was available. Availability matters — an option locked behind progression has a pick rate depressed by ownership, not by strength. Where the game has bans, report presence rate as pick plus ban, because a thing banned every match is not weak.

**Time-to-kill.** Report the distribution, not the mean. Two clusters in one TTK histogram means the game plays two different ways and a single balance number describes neither. Track it per patch: a creeping downward TTK is power creep showing up before anyone has named it.

**Economy curves.** Resource earned per minute and spent per minute, by option and by skill band. The band split is the point: an economy that is tight for new players and irrelevant for good ones is two different games, and the fix is usually a floor rather than a rate change.

**Progression drop-off.** For each encounter, level or run number: how many players reached it, how many cleared it, how many attempts the clearers needed, and how many never played again after it. The last column is the one that matters. A hard level with high attempts and high eventual clears is a good level; a hard level that ends sessions is the difficulty curve failing.

**Match length and surrender rate.** A match decided in the first two minutes but played for twenty is a balance problem the win rate cannot see, because the win rate is the same either way.

## Skill bands

Define bands from something the game already computes — rating, rank tier, or, failing both, lifetime matches played bucketed by order of magnitude. Three bands is the minimum useful split and five is usually enough. Fix the boundaries once and keep them, because moving boundaries makes patches incomparable.

Report every headline metric per band and refuse to average them without saying so. The averaged number hides both halves of the two failure modes it exists to catch: an option that is unusable without execution and dominant with it, and an option that beginners win with because opponents do not know the counter.

The top band is always the thinnest. Expect it to need a longer window than every other band for the same margin, and expect it to be the band whose data arrives last.

## The two-axis read

Plot pick rate on one axis and win rate on the other, one point per option, one chart per skill band. The quadrant, not the number, is the finding.

| Quadrant | What it usually is | The wrong move |
| --- | --- | --- |
| High pick, high win | Genuinely overtuned | Buffing everything else, which raises the whole game's power |
| High pick, low win | A trap: attractive, recommended, or the default, and losing | Nerfing it because its pick rate is high |
| Low pick, high win | A selection effect: specialists, or a situational option picked only when it suits | Nerfing it, which deletes the option and teaches players not to specialise |
| Low pick, low win | Dead content | Anything other than a rework or a new job |

The correction for the low-pick quadrant is a player-relative win rate: for each player who used the option, compare their win rate with it against their win rate without it, then average those differences. An option at 56 per cent whose players sit at 55 per cent on everything else has an effect of one point, not six.

Two more axes worth keeping beside these: win rate against match length, which finds options that are strong only in long or short games, and win rate by side or map, which finds the far more common problem of the map being unbalanced rather than the faction.

## How many observations

Near a 50 per cent win rate, the 95 per cent margin on `n` decided matches is about `100 / √n` percentage points, which follows from the standard error of a proportion, `√(p(1−p)/n)`, being close to `0.5/√n` when `p` is near a half, and the 95 per cent interval being about twice that.

To detect a deviation of `d` points from 50 per cent, you need roughly `n ≈ (100/d)²`:

| Deviation to detect | Matches needed |
| --- | --- |
| 10 points | 100 |
| 5 points | 400 |
| 3 points | 1,100 |
| 2 points | 2,500 |
| 1 point | 10,000 |

Worked, both directions. A faction at 55 per cent over 40 matches has a margin of 100/√40 = ±15.8 points, so its true rate is somewhere between 39 and 71 per cent: the observation is consistent with the faction being badly weak. The same 55 per cent over 400 matches has a margin of ±5 points, range 50 to 60, and is worth acting on. The observed number is identical; only the count changed.

Comparing two options against each other rather than one against 50 per cent roughly doubles the requirement per side, because both sides carry error. Splitting by band divides the sample by the number of bands: 1,200 matches over five bands is 240 each, margin ±6.5 points. Scanning many options at once produces false alarms in proportion to how many you scan — thirty options at 95 per cent confidence gives about 1.5 spurious findings per patch — so raise the bar when you are looking for something rather than checking something.

When the game cannot produce the volume, say so rather than tightening the interpretation. A game with 200 matches a week can detect a 10-point problem in a week and a 3-point problem never, and the honest response is to make changes big enough to see.

## Traps that make an honest number wrong

**Mirror matches.** In a symmetric game, a faction's mirror matches sit at exactly 50 per cent by construction and pull the reported rate toward the middle. Exclude them, or state the dilution. Worked: if a fifth of a faction's matches are mirrors and its reported rate is 54 per cent, its non-mirror rate is (54 − 0.2 × 50) / 0.8 = 44 / 0.8 = 55 per cent.

**Survivorship in progression data.** Completion rate for level 20 is computed over players who reached level 20, who are by definition the ones the earlier levels did not stop. Difficulty measured this way always looks like it falls over time. Report per-encounter rates against the cohort that started the game, not the cohort that arrived.

**Novelty.** The first days after a patch have inflated pick rates and depressed win rates for whatever is new, because everyone is playing it badly. Discard the window and say how long it was.

**Concurrent changes.** A patch with a balance change and a matchmaking change in it has no interpretable balance data. This is a scheduling problem, not a statistics problem, and it is solved before the patch ships.

**Aggregation across modes.** Ranked, casual and custom games are different games. Merging them produces a number whose movement tracks the mode mix rather than the balance.

**Bot and abandoned matches.** Drop them explicitly rather than hoping they are rare. An abandoned match is a win in the data and nothing in the design.

## Single-player and roguelike readings

Win rate is meaningless here, so the metric set changes shape.

For a campaign: deaths per encounter against the starting cohort, attempts-to-clear as a distribution, time spent per section, and the quit point. The healthy curve rises with rest between peaks. A flat curve is boring before it is easy, and a spike with a quit cliff behind it is the only genuinely urgent finding on the chart.

For a roguelike or build game: count the builds that clear above a stated success floor, and how distinct they are. Report the share of runs using the most popular build — if one build is in most winning runs, the variety the genre promises is not being delivered, whatever the overall clear rate says. Track clear rate per build against pick rate per build with the same quadrant read as above; the goal is many points above the floor, not all points at the same height.

## The four views worth building

Anything beyond these is built when a question needs it.

1. Win rate by option by skill band, with `n` and margin on every cell, filtered to one patch.
2. The pick-against-win scatter, one chart per band, with the previous patch's positions ghosted behind.
3. Progression drop-off as a funnel against the starting cohort.
4. A patch diff: every metric that moved more than its margin since the last patch, with the changes shipped in that patch listed beside it.
