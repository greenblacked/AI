---
name: game-economy-flow
description: "Model a game's economy before launch as data: every currency and tradeable item written as sources and sinks per hour for each player archetype (new, engaged, grinder or whale), kept in a flow sheet that a script reads rather than a spreadsheet nobody reruns. Gates the design on three checks: no currency ships without a sink or a stock ceiling, net inflow per archetype sits inside a band stated in advance, and time-to-cap is computed for every capped stock. Use when someone asks how much gold, gems or crafting material players will earn, whether a currency will inflate, how long a grind takes, or what the sinks should be. Not for tuning live numbers from telemetry (game-balance), drop-rate proof (loot-odds-verification), live events (game-live-ops), duplication exploits (economy-exploit-response) or real-money pricing (pricing-research)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Game Economy Flow

Every currency and tradeable item has a written source, a written sink or ceiling, and a computed rate for each kind of player, before any of it is built.

An economy usually breaks in one of two ways: a currency with sources and no real sink, which inflates until the number on screen means nothing, or a grind whose length nobody computed, which turns out to be three times what the design document said. Both are arithmetic, and both are visible on paper months before a player finds them. This skill puts the arithmetic in a flow sheet kept as data, so each change to a reward or a price can be rerun against the same gates.

## Scope

Use for: listing currencies, items and timers; modelling sources and sinks per hour per archetype; setting the net-inflow band; computing time-to-cap and time-to-afford; and deciding what sinks or ceilings a currency needs.

Do not use for: tuning a live economy from telemetry, which is `game-balance` (its economy-corridor row is the post-launch reading of what this skill predicts). Proving that drop rates and pity timers match what was published is `loot-odds-verification`. Containing a duplication glitch or currency exploit that is already live is `economy-exploit-response`. Seasonal and event calendars are `game-live-ops`. What to charge real money for is `pricing-research` in the product plugin; this skill treats a premium currency as a currency and stops at the store counter.

## Workflow

### 1. Inventory every stock

List each thing a player can hold in a count: soft currency, premium currency, crafting materials, keys, energy, tradeable items, and any timer-gated resource. For each, write whether it is **capped** (a hard inventory or wallet limit), **decaying**, **tradeable between players**, and **convertible** into another stock. A conversion is both a sink for one stock and a source for another, and it is where most inflation hides.

Anything the player cannot hold in a count (experience, reputation) is still a stock if it gates something; list it.

### 2. Fix the archetypes and their hours

Write three archetypes with hours of play per week, because rates mean nothing without them:

- **New**: first two weeks, tutorial rewards, no knowledge of shortcuts.
- **Engaged**: the median retained player, a few sessions a week.
- **Grinder or whale**: the top few per cent by hours, or by spending where the game sells currency. These two are different people; model both when the game sells currency, and say which you modelled when it does not.

Take the hours from retention targets or comparable titles and mark each as an assumption. An assumed number is fine; an unlabelled one is not, because the telemetry check after launch needs to know which assumptions to test.

### 3. Write the flow sheet as data

For every stock and archetype, record sources and sinks per hour of play. One row per flow, not per stock, so a single reward change is a single edited line. The format is in `references/flow-sheet.md`; read it now for the columns and a worked sheet.

Count a flow only if the code path exists or is specified. A sink in the design document with no implementation is not a sink. A reward that scales with level needs one row per level band, not an average, because an average across bands hides the band where the stock piles up.

### 4. Gate one: every stock has a sink or a ceiling

A currency may ship if, for every archetype, at least one of these holds, and the sheet says which:

- A **sink with demand**: something to buy that the archetype still wants after a month of play, priced so the sink rate can match the source rate. A sink the grinder exhausts in a week is a ceiling the grinder has already reached.
- A **stock ceiling**: a wallet cap, a decay, or a conversion into something that itself has a ceiling.

A currency with neither fails, however modest its inflow looks, because rate times time is unbounded. For tradeable items add the market: who buys, at what price, and what removes the item from the world (consumption, breakage, a transaction fee). An item that only moves between players is not removed by trading.

### 5. Gate two: net inflow inside a stated band

Net inflow per hour is sources minus sinks for the archetype. State the acceptable band for each archetype and currency before reading the result, for example "engaged players end a week within 0 to +10 per cent of what they earned" or "grinders net no more than twice the engaged rate". A band drawn after seeing the numbers is drawn around the numbers.

The sign matters more than the size. Persistently negative means players cannot afford what the game sells and will stop; persistently positive means a stock piles up until the price list is irrelevant. Name which side each stock should lean on and why: soft currency usually leans slightly positive while the player is progressing and flat at the end of the content, a scarce premium currency leans negative on purpose.

Run the sheet with each archetype's hours and check the band holds for all three. It commonly holds for the engaged player and fails for the grinder, which is the finding to act on, not average away.

### 6. Compute time-to-cap and time-to-afford

For each capped stock, time-to-cap is the cap divided by net inflow per hour, converted to calendar time with the archetype's weekly hours. For each important purchase, time-to-afford is price divided by net inflow. Both are in `references/flow-sheet.md` with the script that computes them from the sheet.

Compare the results with the intent written in the design: "a first weapon in about six hours of play" is a claim the number must meet. A cap that is hit in under a session wastes the rewards after it; a cap that is never reached is not a cap. Report the number in hours of play and in calendar days for each archetype.

### 7. Sensitivity and the report

Move each largest source and sink by 20 per cent in the script and see which gate flips. The flows whose change flips a gate are the ones to instrument first; list them as the telemetry the post-launch reading will need, and hand them to `game-balance`.

Write the result in the shape below and keep the sheet beside it in version control, so a change to a reward shows up as a diff of data.

```text
## Stocks
[Each currency and item: capped, decaying, tradeable, convertible.]

## Archetypes
[Hours per week, each marked assumption or measured.]

## Gate one
[Per stock and archetype: the sink or ceiling that holds, or the failure.]

## Gate two
[Band per archetype and stock, net inflow, pass or fail.]

## Time-to-cap and time-to-afford
[Hours of play and calendar days, per archetype.]

## Sensitivity
[Flows that flip a gate at plus or minus 20 per cent; telemetry to add.]
```

## Anti-patterns

**Averaging the archetypes.** A blended player does not exist; the average hides the grinder who breaks the economy and the new player who cannot afford the first purchase.

**Counting a sink that is optional and unwanted.** A cosmetic shop no one opens does not drain anything. Check what the archetype would buy, not what exists.

**Forgetting conversions.** A currency exchange, salvage-to-material recipe or sell-to-vendor price creates inflow in one stock while draining another. Put every conversion in the sheet as two rows.

**Treating a cap as a fix.** A wallet cap stops the number growing; it does not make the surplus useful. Report the share of inflow wasted at the cap.

**Pricing the sink to the average.** If the price is set so the engaged player just affords it, the grinder buys everything in a week. Check the price against the top archetype before settling it.

## References

- `references/flow-sheet.md` — read at steps 3 and 6: the CSV and JSON shapes, a worked sheet, and the script that computes net inflow, time-to-cap and time-to-afford.
