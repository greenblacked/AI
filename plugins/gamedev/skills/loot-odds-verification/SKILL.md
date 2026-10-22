---
name: loot-odds-verification
description: "Prove that drop rates, gacha pulls, crate odds and pity timers do what the design and any published odds say. Verifies three layers separately: the table (exact per-item probability and expected value, including conditional tables, modifiers and pity), the code (ten million or more headless draws through the shipped logic, chi-square or exact binomial per item), and the live game (server-logged outcomes with confidence intervals by platform and client version, plus the draws-to-rare tail). Use whenever someone says \"players say the drop rate is lower than stated\", \"test our loot table\", \"how does a pity counter work\", \"do we need to publish odds\" or \"is our random number generator fair\". Not for win rates and cost curves (game-balance), store disclosure forms (game-certification), the design document (game-design-doc), or exploited drops (economy-exploit-response)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Loot Odds Verification

The work is done when, for every item a player can be given by chance, three numbers agree to within stated error: the odds in the design document and any shown to players, the probability computed exactly from the shipped table and rules, and the frequency observed in the live game, with the sample size and p-value written beside each.

The usual failure is testing one layer and believing all three. A designer checks the spreadsheet, the spreadsheet is right, and the build still drops the rare item at 0.8 percent instead of 1 because a bonus modifier is applied after normalisation, or because every client seeds from the same second. Players find this first, by streaks, on a forum, weeks after launch. Each layer fails differently and only its own test sees the failure, so the layers are checked in order and kept separate.

## Scope

Use for: confirming drop rates match the design; building a statistical test for a loot table, crate, gacha banner or pity system; answering "players say the rate is lower than stated"; checking that a random number source is fair; preparing the evidence behind published odds.

Do not use for: whether the win rates, drop rates or prices are good for the game, which is `game-balance`. The store's disclosure forms and review checklist are `game-certification`; this skill produces the numbers those forms quote. Writing the design document is `game-design-doc`. A drop that is being farmed or duplicated is `economy-exploit-response`. This is procedure, not legal advice; what a jurisdiction or platform requires is for the publisher's counsel to confirm.

## Workflow

### 1. Write down what is claimed

List every source of a stated probability: the design document, the in-game odds screen, the store listing, the support articles. Put them in one table beside the item identifiers the code uses. Where two sources disagree, stop; no test can say which is intended. Settle which is the spec, then test against that one.

Record the rules that change the probability beyond the base table: pity and guarantee counters (soft pity ramps the rate, hard pity forces the item), duplicate protection, level or progress gating, event multipliers, premium-currency bonuses, and any table that is rolled conditionally on an earlier roll. Each is a place the headline number stops being the real one.

### 2. Layer one: compute the table exactly

Before simulating anything, compute per-item probability from the data by arithmetic, walking the rules in the order the code applies them. Normalise weights explicitly: a table whose weights sum to 10,000 reads as basis points only if nothing else has been added to it since. For a conditional table, multiply along the path. Report expected value per draw for any numeric reward alongside the per-item probabilities.

For a hard pity of N draws with base rate p, the expected draws to the first rare is `(1 - (1-p)^N) / p`. At p = 0.01 and N = 90 that is about 59.5, not 100, which is the figure players quote when they say "one percent" and the figure that explains why the design document's average cost looks too cheap or too dear. Compute the probability of reaching the item by draw k for the k values players talk about (10, 50, 90) and put them next to the stated odds.

Compare with the claims from step 1 and fix mismatches here. Layer one is free and usually the cheapest place to catch defects; do not start a ten-million-draw run to discover that two weights were swapped. `references/statistics.md` has the formulas, the pity derivation and a script for the exact table.

### 3. Layer two: run the shipped code, headless

Drive the real drop function, not a reimplementation. A Python rewrite of the table tests the Python. Build a headless harness that calls the game's own roll path with the shipped data files, the shipped random number source and the shipped seeding, and records one item identifier per draw. At least ten million draws, because a one-in-a-thousand item then appears around ten thousand times and a deviation of a few percent of its rate becomes visible. For rarer items, size the sample from the rate: the expected count should be well above five for every item tested.

Run it twice, from fresh processes, and once with the seeding path exercised the way the game does it. A shared seed, a seed taken from a one-second clock, or a generator reseeded per session shows up as identical or correlated sequences across runs, which a single long run in one process never reveals. Modulo bias shows up as a small, consistent excess on low-numbered outcomes: a range reduced with `rand() % n` is biased whenever the generator's range is not a multiple of `n`. Also run the same harness for sequences, since pity and streak rules are properties of consecutive draws and a per-draw frequency test cannot see them.

Test each item separately with an exact binomial test (observed count against `n * p`) and the whole table together with a chi-square goodness-of-fit. With dozens of items, some p-value will be small by chance; apply a Bonferroni correction across the items tested and say so. A single p-value of 0.03 across forty items is noise. A p-value below 1e-6 for a headline item is a defect. Report the sample size, the observed rate, the expected rate, the p-value, and the confidence interval for each item.

### 4. Pity, guarantee and persistence tests

Counters are state, and state is where odds go wrong without any random number being involved. Write explicit cases for each of these and run them against a real backend, not a mock:

- The counter survives closing the app, a crash mid-draw, and a server restart.
- It survives platform linking, account merge and a restore from a backup, and it is not reset by switching banner unless the design says so; if it carries across banners, test that too.
- A refunded purchase or a reverted transaction reverses the draw and the counter together, in either order, and a retried request is idempotent: the same request identifier never rolls twice.
- Two simultaneous requests from one account cannot both read the same counter value.
- The counter's displayed value is the stored value.

A pity bug usually costs the player something real and the studio a refund conversation, so these are release gates, not nice-to-haves.

### 5. Randomness lives on the server

Confirm that every roll that affects a paid or scarce outcome happens on the server, with the result sent to the client. A roll made on the client with the outcome reported back is editable by anyone with a memory editor, and no statistical test of the logs distinguishes a fair roll from a forged report. If the design needs client-side animation, the server decides first and the animation plays the result. Log the request identifier, the player's counter state before and after, the table version and the outcome for every roll; layer three cannot be run without them.

### 6. Layer three: the live game

Pull server-logged outcomes for a fixed window and compute the same statistics as in step 3, with a confidence interval per item (Wilson interval for a proportion), not a bare average. Then split by platform, client version, table version and region. A discrepancy in one segment and not the others points at a client or data version, not at chance. Exclude test accounts and anything flagged by `economy-exploit-response` before computing.

Compute the distribution of draws needed to reach the rare item, not only the rate. Players judge by streaks, so the complaint lives in the tail: report the median, the 90th and 99th percentile, and the share of players who passed the hard pity without a drop (which must be zero). Compare to the distribution predicted in step 2. A rate that is right on average with a fat tail is a pity bug.

Decide the analysis window before looking, and do not stop the moment a p-value dips below 0.05. Repeatedly peeking at a running total finds a significant result by chance sooner or later; use a fixed sample size or a sequential method chosen in advance.

### 7. Published odds are a spec

Where the platform or jurisdiction requires odds to be disclosed, the disclosed figure is a specification the simulation must match, and it is the claim a regulator or a platform reviewer will compare with behaviour. Check the current text of each store's policy and the rules for each market the game ships in; they change and differ. Record what was tested: table version, build, date, sample size, p-values, who ran it. Store that record with the release, so a complaint two years later is answered with evidence rather than a rerun.

### 8. Report

```markdown
## Claims
[Each stated probability, its source, and the one chosen as the spec.]

## Table (layer one)
[Exact per-item probability, expected value, expected draws to rare, and any mismatch fixed.]

## Code (layer two)
[Draws, seeds and seeding path, per-item observed vs expected, p-values with the correction used.]

## Counters
[Each persistence case, pass or fail, and the backend it ran against.]

## Live (layer three)
[Window, sample, intervals, per-segment splits, draws-to-rare percentiles.]

## Verdict
[Matches or does not, to what error, and what is still unmeasured.]
```

## Anti-patterns

**Simulating a reimplementation.** The spreadsheet or script that reproduces the design is not the shipped logic; a bug in the shipped code never appears in it.

**One long run in one process.** It hides reseeding and shared-seed defects, which are properties of how processes start, not of the generator.

**Reading a p-value without a count.** With a large enough sample any tiny gap is significant, and with a small one a real gap is not. Report the effect size and interval too.

**Testing only the headline rate.** Complaints come from the tail and from the segment: one platform, one client version, one banner.

**Fixing the odds screen to match the code.** If the code and the document disagree, decide which is the intent first; changing the published number to match a bug is a disclosure change, not a fix.

## References

- `references/statistics.md` — read at steps 2, 3 and 6: the formulas for exact per-item probability, pity expectation and draws-to-rare, sample-size rules, the binomial, chi-square and Wilson interval calls in Python, and the multiple-comparison correction.
