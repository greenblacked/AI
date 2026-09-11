# Cost curves and the dominance check

Read this at step 4, before proposing a cost or power change. Everything here is arithmetic on the design rather than on the telemetry, so it can be done before a single match has been played — which makes it the cheapest balance work available and the part most often skipped.

## Contents

- [Dominance comes first](#dominance-comes-first)
- [Fitting the curve](#fitting-the-curve)
- [The vanilla test](#the-vanilla-test)
- [Why cheap options win by default](#why-cheap-options-win-by-default)
- [What a curve does not capture](#what-a-curve-does-not-capture)
- [Reworking dead content](#reworking-dead-content)
- [A worked pass](#a-worked-pass)

## Dominance comes first

Option B is dominated when option A is at least as good on every axis that matters and better on at least one. Axes include cost, raw output, range, speed, what it counters, what counters it, and when in the game it is available.

A dominated option is dead content whatever its win rate says, and the win rate will be misleading because only a few players pick it and they pick it for reasons the data does not carry. No percentage adjustment fixes dominance: a 10 per cent buff to a strictly worse option makes it a strictly worse option with a bigger number, and a 40 per cent buff makes it the dominant one. The fix is a different job — a different range band, a different cost point, a different thing it beats.

Run the check as a table before tuning anything. List every option in a category, one row each, one column per axis, and look for a row that is beaten everywhere. In a category of a dozen options this takes twenty minutes and routinely finds two.

The same check applies to strategies, not only to options: if one opening, build order or line of play is better than every alternative in every situation, the game has one strategy and the others are decoration. That is the most expensive version of the problem, because it is invisible in per-option win rates — everyone is playing the same thing, so nothing looks like an outlier.

## Fitting the curve

For a category with a cost — mana, gold, supply, cooldown, slot — plot cost on one axis and a power score on the other, one point per option.

The power score is whatever the category is bought for, combined in a way you can defend in one sentence. A creature might score as attack plus health; a weapon as damage per second times effective range; a unit as damage per second times effective hit points. The score does not need to be true, it needs to be consistent, because what you read off the chart is the outliers rather than the values.

Fit the line to options with healthy pick rates only. Fitting to everything drags the curve down to meet dead content and then declares the dead content fine.

The shape to expect is rising with diminishing returns: an option costing twice as much should not be twice as strong, because a player fields fewer of them, cannot spend the remainder elsewhere, and loses everything at once when it dies. A perfectly straight line means the expensive options are traps; a line that steepens at the top means the cheap options are.

Points well above the line are what people play, and points well below are what they do not. Before adjusting either, check whether the distance is real or an artefact of a score that ignores something — which is the next section but one.

## The vanilla test

Price the plain version first. In a category where cost `c` buys a baseline `2c` points of stats, a 4-cost option with 8 points of stats is on the curve and everything else about it is the interesting part. Then price the rest as a premium over the baseline: an option with a useful ability should sit below the stat line by roughly what the ability is worth, and an option sitting on the stat line with a free ability is above the curve by definition.

This is the fastest way to find an outlier in a set with many options, because it collapses to one subtraction per row. It also makes cost changes legible: moving an option up a cost step has to be paid for with a step of the baseline, or it is a nerf disguised as a reprice.

Keep the baseline written down. An undocumented baseline drifts upward one design meeting at a time, which is what power creep is.

## Why cheap options win by default

In any game where units fight simultaneously and can concentrate fire, combat strength scales with the square of the number of units, not linearly — this is Lanchester's square law for aimed fire, and it holds well enough in practice to plan around. A force of `N` units with individual effectiveness `e` has strength proportional to `e × N²`.

Work through what that does to a cost curve. With a budget `B`, an option costing `c` buys `B/c` of them, so the force strength is `e × (B/c)²`, and strength per budget is proportional to `e / c²`.

Compare two options that look equally priced on a linear curve. Option A costs 100 with effectiveness 10, and gives 10 / 100² = 0.001. Option B costs 50 with effectiveness 5 — exactly half the stats for exactly half the price — and gives 5 / 50² = 0.002. B is twice as good for the same money, and nothing on a linear cost sheet shows it.

So a linear cost curve hands the game to whatever is cheapest, and every game that does not visibly suffer from this has something bending the curve back:

- **Splash, cleave and area effects** that scale with the number of targets, so massing cheap things becomes a liability.
- **Supply, deck or roster caps** that limit count rather than spend, which makes the per-slot value matter more than the per-cost value.
- **Micro and attention overhead**, since controlling forty units costs the player something the spreadsheet does not model.
- **Per-unit overheads** — population cost, upkeep, build time, deployment slots — that make the cheap option cost more than its price tag.

If your game has none of these, the cost curve has to be superlinear on purpose: expensive options need to be more than proportionally strong, which is the opposite of the diminishing-returns shape most designers reach for. Decide which regime the game is in before tuning, because the two want curves that bend in opposite directions and a pass done under the wrong assumption makes every option worse.

The counterpart holds where numbers do not compound — a one-versus-one fighting game, a card game with a hard board limit, a shooter with fixed team sizes. There, the linear curve is right and the cheap-swarm correction is a bug rather than a feature.

## What a curve does not capture

Before acting on a distance from the line, check whether the score is missing one of these, because each is routinely worth more than the gap you are about to close.

- **Flexibility.** An option usable in every deck, composition or situation is worth more than a specialist with a higher peak, and the curve cannot see it.
- **Tempo and timing.** Two options with equal totals are not equal if one arrives four minutes earlier.
- **Consistency.** A reliable result beats a higher average with a long tail, because players build plans on the floor rather than the mean.
- **Counterplay cost.** An option that forces the opponent to hold a resource in reserve is charging them something it never spends itself.
- **Synergy.** Power measured alone is the wrong measurement for an option that exists to combine. Score it in its intended pair, and note that a synergy piece with a healthy solo score is usually the one that ends up over the line.
- **Information.** Denying or gaining information has a value that no stat line carries.

The practical rule: the curve nominates suspects, and one of the checks above either confirms the suspect or explains it. An option 20 per cent above the line that is also the most flexible thing in its category is not 20 per cent overtuned; it is further above than the chart shows.

## Reworking dead content

An option in the low-pick, low-win quadrant that also fails the dominance check needs a job, not a number. In order of cost:

1. **Reprice.** Move it to a cost point where nothing else competes. Cheapest change, and often enough.
2. **Narrow and sharpen.** Make it clearly the best answer to one specific thing and worse at everything else. A niche option with a purpose beats a mediocre general one.
3. **Change an axis.** Give it a different range band, speed, or timing, so it is no longer on the same line as the option that dominates it.
4. **Remove it.** An option nobody picks is content to maintain, art to update and a row in every balance table. Cutting it is a legitimate outcome, and it is the one nobody proposes.

## A worked pass

A strategy game, eight ground units, budget-limited combat with no supply cap and no area damage.

1. **Dominance table.** Eight rows, columns for cost, damage per second, effective hit points, range, speed, and what it counters. The medium melee unit is beaten by the cheap melee unit on cost per effective hit point and by the heavy on everything else; it is dominated, and no repricing within its band saves it. It goes on the rework list rather than the tuning list.
2. **Score and plot.** Power score is damage per second times effective hit points. The plot is roughly linear against cost.
3. **Apply the square law.** No area damage, no supply cap: the regime is one where strength per budget goes as `e / c²`, so a linear curve means the cheapest unit is strictly the best purchase. That matches a pick rate nobody could explain from the stat sheet.
4. **Decide the fix at the system level.** Either bend the curve superlinearly, or introduce the thing that punishes massing — area damage on one unit, or a per-unit population cost. The second is one change and affects every option consistently, so it goes first, and it is one change with a window rather than eight reprices.
5. **Predict and wait.** Write the expected movement in the cheap unit's pick rate and the count needed to read it, then hold the reprices until the window closes. The system change may make half of them unnecessary, and shipping both makes the reading uninterpretable.
