---
name: procgen-seed-testing
description: "Validate procedurally generated levels, worlds or loot by treating the generator as a function from seed to content and sweeping many seeds. Makes it pure and byte-reproducible across platforms with the generator version in the seed string, encodes hard validity invariants as code run over at least 100,000 seeds in CI that print the failing seed, plots soft quality metrics and inspects the tails, runs a bot or solver on a sample because reachability is not winnability, and keeps a regression list of every reported bad seed. Use whenever someone says \"the generator sometimes makes an unbeatable level\", \"seeded runs differ between machines\", \"how do I test procedural generation\", \"player reports a bad seed\" or \"daily challenge seed\". Not for hand-built layout (game-level-design), tuning numbers (game-balance), or whole-game bot runs (automated-playthrough)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Procgen Seed Testing

The work is done when the same seed and generator version give byte-identical content on every supported platform, hard invariants are checked over at least 100,000 seeds in CI with the failing seed printed, the worst percentile of each quality metric has been looked at by eye, and every seed a player ever reported is in a regression list.

The usual failure is testing the generator on the few seeds a developer happened to see. A defect that occurs in one seed in ten thousand is invisible in play-testing and certain to reach a player within a day of launch.

## Scope

Use for: unbeatable or degenerate generated output; seeds that give different results on different machines; shared and daily seeds; designing the checks that run over many seeds.

Do not use for: levels placed by hand, which is `game-level-design`; tuning drop rates or difficulty numbers, which is `game-balance`; playing the whole game with a bot, which is `automated-playthrough` (this skill uses a bot only on generator output).

## Workflow

### 1. Make the generator a pure function of its seed

One seeded generator is threaded through all generation as an argument. Remove every use of the global random source, the clock, thread scheduling and unordered iteration (hash-map order, directory listing order). Pin the algorithm: do not rely on a standard library's distribution classes, whose output may differ between implementations; specify the generator (for example PCG or xoshiro) and write the integer and float draws yourself. Floating-point maths that feeds a decision needs care across compilers and CPUs, so make decisions on integers or on values rounded in a defined way.

Test it: generate the same seed twice, in two processes, on every supported platform, and compare hashes of the serialised output. `references/sweep-and-metrics.md` has the harness.

Store a generator version in the save and in the shareable seed string (for example `v3-8F2A19C4`), so a seed names both the input and the algorithm.

### 2. Write the hard invariants as code

An invariant is a yes-or-no property that every output must have. Examples: the start connects to the exit; required keys are reachable before the doors they open; no geometry overlaps; the spawn is not inside a wall; resource totals stay within bounds. Each is a function from generated content to a list of violations. Run all of them over at least 100,000 seeds in CI, in parallel, and on failure print the seed and the invariant, so the failure can be reproduced with one command. Give each seed a time limit and report a seed that exceeds it as a `timeout` failure: a generator that retries until valid can loop forever on one seed, and without a limit the sweep hangs and the stuck seed is never printed.

A failure is a bug in the generator or in the invariant. Fix it, add the seed to the regression list (step 5), and do not weaken the invariant to make the sweep pass.

### 3. Measure the soft quality metrics

Some properties have no pass or fail: path length, room count, dead-end ratio, enemy density, time to first reward. Compute them over the same seeds and plot the distribution. The tails matter more than the mean: a generator with a good average and a 1 percent tail of empty maps still ships empty maps. Take the worst and best percentile (for 100,000 seeds, the extreme 0.1 percent), render a handful of those levels and look at them. Set an acceptable range for each metric once the tails have been inspected, and have CI report a seed outside it.

### 4. Check winnability, not only reachability

A path from start to exit does not mean the level can be beaten: the required item may need a skill the player lacks at that point, or the enemy density may be impossible. Run a bot or solver over a sample of seeds (a few thousand is usually enough to see the rate) and record the win rate and the seeds it cannot win. Treat a seed the bot cannot solve as a candidate bug to examine by hand before deciding whether the bot or the level is at fault.

### 5. Keep a regression list

Every bad seed ever reported, by a player or in testing, goes into a file in the repository with a line saying what was wrong. CI generates each one, with the generator version it was reported on, and runs all invariants on it. The list is cheap and is the only protection against the same defect returning after a rewrite.

### 6. Version algorithm changes

Any change that alters output for an existing seed is a new generator version. Keep the old versions callable so shared seeds and daily challenges still replay. Do not edit a released generator in place, even for a bug fix, unless the seed string is documented as breaking; say which in the changelog. Test the old versions on the regression list too, because they stay in service.

### 7. Report

```markdown
## Reproducibility
[Platforms compared, hash result, generator version format.]

## Invariants
[List, seeds swept, failures found and the seeds.]

## Quality metrics
[Metrics, percentiles, what the tails looked like, accepted ranges.]

## Winnability
[Bot or solver, sample size, win rate, unsolved seeds examined.]

## Regression list
[Count, where it lives, the versions it covers.]
```

## Anti-patterns

**Sweeping 1,000 seeds and calling it covered.** A one-in-ten-thousand defect needs far more; use the whole budget CI allows.

**Judging by the average.** The player who meets the tail is the one who writes the review.

**Fixing the generator in place after seeds were shared.** The daily-challenge seed from last week now means something else.

**Weakening the invariant.** If an invariant fires too often, ask whether it is wrong, then fix the generator or the invariant on evidence.

## References

- `references/sweep-and-metrics.md` — read at steps 1 to 3: the cross-platform hash harness, the parallel sweep and the percentile report.
