# Statistics for loot odds

Read this at steps 2, 3 and 6 of `SKILL.md`. It holds the arithmetic and the library calls so the procedure stays short. Everything here uses the Python standard library plus `scipy` for the tests; the harness that produces the draws is the game's own code, not Python.

## Contents

- [Exact probability from a table](#exact-probability-from-a-table)
- [Pity: expected draws and the distribution](#pity-expected-draws-and-the-distribution)
- [Sample size](#sample-size)
- [Testing the code run](#testing-the-code-run)
- [Intervals for the live game](#intervals-for-the-live-game)
- [Multiple comparisons](#multiple-comparisons)
- [Seeding and range defects](#seeding-and-range-defects)

## Exact probability from a table

For a weighted table, an item's probability is its weight over the sum of all weights, after every modifier is applied in the order the code applies it. Use fractions so no rounding hides a mismatch:

```python
from fractions import Fraction

weights = {"common": 8500, "rare": 1300, "epic": 190, "legendary": 10}
total = sum(weights.values())
probs = {k: Fraction(v, total) for k, v in weights.items()}
```

For a conditional table (roll a tier, then roll within the tier), multiply along the path: `P(item) = P(tier) * P(item | tier)`. Check that the result sums to exactly 1 across all leaves; a sum other than 1 means a table is missing weight or a modifier was added after normalisation.

Expected value of a numeric reward is `sum(p_i * value_i)`. Report it per draw and per currency spent.

## Pity: expected draws and the distribution

A hard pity of `N` draws with base rate `p` (the item is forced on draw `N` if not yet received):

- Probability the first rare arrives on draw `k`, for `k < N`: `(1-p)^(k-1) * p`.
- Probability it arrives on draw `N`: `(1-p)^(N-1)`.
- Expected draws to the first rare: `(1 - (1-p)^N) / p`.

Soft pity raises the rate from some draw `s` onwards, typically in steps. Compute it by dynamic programming over the draw index rather than by a closed form:

```python
def draws_to_rare(rate_at, hard_pity):
    """rate_at(k) is the probability on draw k, given none before."""
    survive = 1.0
    dist = []
    for k in range(1, hard_pity + 1):
        p = 1.0 if k == hard_pity else rate_at(k)
        dist.append(survive * p)
        survive *= 1.0 - p
    return dist  # dist[k-1] = P(first rare on draw k); sums to 1
```

From `dist`, take the mean (`sum(k * d)`), the median and the 90th and 99th percentile from the cumulative sum. These are the predictions step 6 compares with the live distribution. If the design uses a 50/50 split or a featured-item guarantee, run the same calculation per banner state and weight the states by their reach probability.

## Sample size

A binomial count with expected value `n * p` has standard deviation about `sqrt(n * p * (1-p))`. To see a relative error `r` in a rate `p` at roughly two standard deviations, the expected count `n * p` needs to be about `4 / r^2`. For a 5 percent relative error that is about 1,600 expected hits; for 2 percent about 10,000. At `p = 0.001` and ten million draws the expected count is 10,000, which is why ten million is the floor and not the target for the rarest item.

Chi-square needs an expected count of at least five in every cell. Merge or exclude cells below that, and test the excluded rare items separately with the exact binomial.

## Testing the code run

```python
from scipy.stats import binomtest, chisquare

n = sum(observed.values())

# An observed item absent from the table should never drop: a defect.
for item in sorted(set(observed) - set(probs)):
    print("DEFECT: dropped but not in table", item, observed[item])

# Iterate the table, so an item that never dropped gets its own test.
items = sorted(probs)
for item in items:
    count = observed.get(item, 0)
    result = binomtest(count, n, float(probs[item]))
    ci = result.proportion_ci(confidence_level=0.95, method="wilson")
    print(item, count, n, result.pvalue, ci.low, ci.high)

stat, p = chisquare(
    f_obs=[observed.get(i, 0) for i in items],
    f_exp=[n * float(probs[i]) for i in items],
)
```

If you merge or exclude cells with a low expected count, keep the totals equal: recent scipy rejects `f_obs` and `f_exp` whose sums disagree. Either merge the excluded cells into one "other" cell on both sides, or rescale `f_exp` to the remaining observed total.

`chisquare` has `k - 1` degrees of freedom by default for `k` cells. `binomtest` is exact and two-sided by default. Report the counts, not only the p-values, so a reader can redo the test.

## Intervals for the live game

For an observed rate `x / n`, use a Wilson interval, which stays sensible for small counts and rates near zero where the textbook normal interval does not. The call above returns it. State the confidence level. When the stated odds sit inside the interval, the data are consistent with them; when they sit outside, report the gap and the segment, not "the odds are wrong".

Per segment, compute the same interval and compare each against the expected rate, not against each other. Two segments with overlapping intervals can both be off from the spec in the same direction.

## Multiple comparisons

Testing `m` items and reading each at 0.05 gives about `0.05 * m` false alarms. Divide the threshold by the number of tests (Bonferroni), so for 40 items and 0.05 the per-item threshold is 0.00125. State the correction in the report. Segments multiply the number of tests too: items times platforms times versions.

## Seeding and range defects

Signs to look for in the draws themselves, independent of the table:

- Identical sequences from separate processes started in the same second: a clock-derived seed.
- Two accounts or two sessions receiving the same outcome sequence: a shared or fixed seed.
- A consistent excess of low-numbered outcomes: modulo reduction of a generator range that `n` does not divide. The fix is rejection sampling or an unbiased bounded-integer routine from the library, not a different generator.
- Correlation between consecutive draws in the sequence tests: a weak or badly mixed generator, or reseeding on every call.
- Streaks longer than the model predicts: a counter that is not reset or is reset twice.

Note which seeding path the game actually uses in production and test that one. A test harness that seeds from a fixed integer for reproducibility is correct for debugging and proves nothing about production seeding.
