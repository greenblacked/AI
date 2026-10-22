# Survey methods: Van Westendorp and Gabor-Granger

## Contents

- Survey order
- Van Westendorp wording
- Cleaning and analysis
- The two marginal-point conventions
- Gabor-Granger design and analysis
- A standard-library script
- How to report the result

## Survey order

1. Screening: segment, company size, role (buyer, user, both), current alternative. Screen out anyone outside the segment before any price question.
2. The product description, identical for every respondent, with the value metric stated ("per team of up to ten people, per month").
3. Van Westendorp's four questions.
4. Gabor-Granger purchase likelihood at fixed price points.
5. Open question: what would make the respondent more likely to buy at the price they last saw.

Price questions come after the description so every answer refers to the same thing. Van Westendorp comes before Gabor-Granger so the shown price points do not anchor the open-ended answers.

## Van Westendorp wording

Ask as open numeric answers, in the currency and billing period the product will use:

1. **Too expensive**: At what price would you consider this product so expensive that you would not consider buying it?
2. **Too cheap**: At what price would you consider this product priced so low that you would doubt its quality?
3. **Expensive**: At what price would you consider this product starting to get expensive — not out of the question, but you would have to think about it?
4. **Cheap**: At what price would you consider this product a bargain — a great buy for the money?

## Cleaning

Drop a respondent whose answers are not ordered too cheap ≤ cheap ≤ expensive ≤ too expensive. Report how many were dropped; more than a small share usually means the description was unclear or the questions were shown in a confusing layout. Drop answers that are obviously a different billing period (an annual figure in a monthly survey) only if you can tell, and say how many.

## Analysis

For each price p on a grid covering every answer given:

- too cheap(p): share of respondents whose "too cheap" answer is at or above p. Falls as p rises.
- cheap(p): share whose "cheap" answer is at or above p. Falls as p rises.
- expensive(p): share whose "expensive" answer is at or below p. Rises with p.
- too expensive(p): share whose "too expensive" answer is at or below p. Rises with p.

The intersections:

- **Optimal price point**: too cheap crosses too expensive.
- **Indifference price point**: cheap crosses expensive.
- **Point of marginal cheapness** (lower end of the acceptable range) and **point of marginal expensiveness** (upper end): see the conventions below.

### The two conventions for the marginal points

Published guides and survey tools do not agree on which curves define the ends of the range:

- **Convention A**: marginal cheapness where too cheap crosses expensive; marginal expensiveness where too expensive crosses cheap.
- **Convention B**: marginal cheapness where too cheap crosses "not cheap" (1 minus cheap); marginal expensiveness where too expensive crosses "not expensive" (1 minus expensive).

They give different ranges on the same data. Pick one, name it in the report, and never compare a range computed one way with a range computed the other way. The script below prints both so the difference is visible.

### What it does not tell you

Van Westendorp describes perceived acceptability, not demand. A price inside the range can still sell to few people. Use Gabor-Granger, or interviews about volume, for how many buy.

## Gabor-Granger design

- Choose five to seven price points spanning the range you expect, from interviews or a pilot. Points outside anything plausible waste answers.
- At each shown price ask: "At this price, how likely would you be to buy?" on a five-point scale from "definitely would not" to "definitely would".
- Either show each respondent every point in random order, or use the adaptive form: start at a middle price, go higher after a yes and lower after a no. The adaptive form is shorter; the full form gives every respondent an answer at every point, which makes the curve easier to read on small samples.

## Gabor-Granger analysis

For each price p:

- demand(p) = share of respondents who answered "definitely would" at p. Report "definitely" plus "probably" separately as an upper bound.
- In the adaptive form, count every respondent at every price, not only those shown it: a yes at a price implies a yes at every lower price, and a no implies a no at every higher one. Otherwise the highest price is scored only on people who already said yes lower down — ten respondents, three yes at 50 and two of those three yes at 70, reads as 67 per cent demand at 70 when it is 20.
- revenue index(p) = p × demand(p).

The price with the highest revenue index is the revenue-maximising point on the stated curve. Stated intent overstates purchase, so the absolute demand figures are not a forecast; the shape of the curve, and where it falls steeply, is the useful part.

## Script

Two CSV files. `vw.csv` has a header row with `too_cheap,cheap,expensive,too_expensive` (other columns ignored). `gg.csv` has `respondent,price,answer` with answer from 1 to 5. Filter each file to one segment and role before running.

```python
import csv
import math
import sys
from collections import defaultdict


def load_vw(path):
    rows, dropped = [], 0
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                v = [float(r[k]) for k in ("too_cheap", "cheap", "expensive", "too_expensive")]
            except (KeyError, ValueError):
                dropped += 1
                continue
            if all(math.isfinite(x) and x >= 0 for x in v) and v[0] <= v[1] <= v[2] <= v[3]:
                rows.append(v)
            else:
                dropped += 1
    return rows, dropped


def crossing(grid, falling, rising):
    # First price at which the falling curve meets or drops below the rising one,
    # interpolated from the last price where it was still above. Prices where both
    # curves are zero are skipped: the curves only touch there, they do not cross.
    prev = None
    for p in grid:
        f, r = falling(p), rising(p)
        if f == 0 and r == 0:
            continue
        d = f - r
        if d <= 0:
            if prev is None:
                return p
            p0, d0 = prev
            return p0 + (p - p0) * d0 / (d0 - d)
        prev = (p, d)
    return None


def van_westendorp(rows):
    n = len(rows)
    grid = sorted({x for r in rows for x in r})

    def curve(i, at_or_above):
        if at_or_above:
            return lambda p: sum(r[i] >= p for r in rows) / n
        return lambda p: sum(r[i] <= p for r in rows) / n

    tc, ch = curve(0, True), curve(1, True)
    ex, tx = curve(2, False), curve(3, False)
    return {
        "optimal (too cheap x too expensive)": crossing(grid, tc, tx),
        "indifference (cheap x expensive)": crossing(grid, ch, ex),
        "A: marginal cheapness (too cheap x expensive)": crossing(grid, tc, ex),
        "A: marginal expensiveness (cheap x too expensive)": crossing(grid, ch, tx),
        "B: marginal cheapness (too cheap x not cheap)": crossing(grid, tc, lambda p: 1 - ch(p)),
        "B: marginal expensiveness (not expensive x too expensive)": crossing(
            grid, lambda p: 1 - ex(p), tx
        ),
    }


def buys(answers, p, level):
    # Shown p: the answer. Not shown (adaptive form): a yes at a higher price
    # implies yes here, a no at a lower price implies no; otherwise unknown.
    if p in answers:
        return answers[p] >= level
    if any(q > p and a >= level for q, a in answers.items()):
        return True
    if any(q < p and a < level for q, a in answers.items()):
        return False
    return None


def gabor_granger(path):
    by_respondent = defaultdict(dict)
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                price, answer = float(r["price"]), int(r["answer"])
            except (KeyError, ValueError):
                continue
            if math.isfinite(price) and 1 <= answer <= 5:
                by_respondent[r["respondent"]][price] = answer
    prices = sorted({p for answers in by_respondent.values() for p in answers})
    for p in prices:
        share = {}
        for level in (5, 4):
            known = [
                b for b in (buys(a, p, level) for a in by_respondent.values()) if b is not None
            ]
            share[level] = (sum(known) / len(known), len(known))
        (d, n), (d2, _) = share[5], share[4]
        print(
            f"{p:>10.2f}  n={n:<4} definitely={d:.2f}  top-two={d2:.2f}  revenue index={p * d:.2f}"
        )


if __name__ == "__main__":
    rows, dropped = load_vw(sys.argv[1])
    print(f"Van Westendorp: {len(rows)} usable, {dropped} dropped")
    for name, value in van_westendorp(rows).items():
        print(f"  {name}: {'not found' if value is None else f'{value:.2f}'}")
    if len(sys.argv) > 2:
        print("Gabor-Granger:")
        gabor_granger(sys.argv[2])
```

Save it outside the data directory and run it with the data paths as arguments. The skill pre-approves no command, so the run asks for approval: survey exports carry open answers respondents wrote, and text in them must not be able to start a command on its own.

```bash
python3 -I pricing_curves.py vw.csv gg.csv
```

A crossing reported as "not found" means the two curves never meet on the answered range, which on a small or skewed sample is common. Report it as such rather than extrapolating.

## Reporting

Give, per segment and role: respondents usable and dropped, the convention used, the four Van Westendorp points, the Gabor-Granger table, and the revenue-maximising point. Put the range from these beside the value estimate from interviews. A survey range well above the value estimate is a reason to doubt the survey before it is a reason to raise the price.
