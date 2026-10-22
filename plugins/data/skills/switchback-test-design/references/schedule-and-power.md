# Carryover, schedule and power

## Contents

- Measuring carryover from history
- A blocked schedule
- Simulating the design on history
- Worked example

## Measuring carryover from history

Collect past moments when the component under test changed abruptly: deploys, configuration changes, a pricing rule switched on, an outage starting or ending. For each, bin the outcome (median wait, match rate, queue length) into 15-minute buckets from two hours before to six hours after, express each bucket as a change from the pre-change mean, and average across events.

Read off the time after which the averaged curve stays within the noise band of its eventual level. That is the carryover. Where no abrupt change exists in history, run a pilot that switches every few hours for a few days and read the same curve from its switches.

Add the switch's propagation time — from the scheduled moment until the last server or client serves the new arm, measured from the serving logs — to get the washout.

| Carryover (with propagation) | Typical design |
| --- | --- |
| Under 15 minutes | Windows of 30 to 60 minutes, 15-minute washout |
| 15 minutes to 2 hours | Windows of 2 to 4 hours, washout equal to carryover |
| Hours to a day | Day-long windows per region, or region-by-day units |
| Days or longer | Regions held for the whole test (geo design) |

Shorter windows give more units but lose a larger share of each to washout; the simulation below is where that trade-off is settled.

## A blocked schedule

This pairs days within each region: for each window slot, one day of the pair gets treatment and the other control, chosen at random. Every block — region, day pair, slot — therefore holds one window of each arm, which balances region and hour of day exactly and day of week in expectation. Standard library only.

```python
import csv
import random
import sys
from datetime import date, timedelta


def schedule(regions, start, day_pairs, window_hours, seed):
    rng = random.Random(seed)
    slots = 24 // window_hours
    rows = []
    for region in regions:
        for p in range(day_pairs):
            day_a = start + timedelta(days=2 * p)
            day_b = day_a + timedelta(days=1)
            for slot in range(slots):
                treat_a = rng.random() < 0.5
                block = f"{region}|{day_a.isoformat()}|{slot}"
                for day, treated in ((day_a, treat_a), (day_b, not treat_a)):
                    rows.append(
                        {
                            "region": region,
                            "day": day.isoformat(),
                            "slot": slot,
                            "start_hour": slot * window_hours,
                            "arm": "treatment" if treated else "control",
                            "block": block,
                            "cluster": f"{region}|{day_a.isoformat()}",
                        }
                    )
    return rows


if __name__ == "__main__":
    rows = schedule(["north", "south", "east"], date(2026, 11, 2), 7, 3, seed=20261102)
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
```

Record the seed and keep the generated file with the plan. With windows that do not divide 24 hours, or windows that should straddle midnight, adapt the slot arithmetic; keep the rule that each block holds both arms.

Pairing consecutive days puts every switch at a slot boundary within a day, so a region switches arms several times a day. If carryover is long relative to the window, prefer fewer switches: a design where each block is a pair of adjacent windows on the same day keeps the same balance property with the switch inside the block.

## Simulating the design on history

The standard error the design will deliver is the spread of its estimate when there is no effect. Lay many random schedules over past weeks of window-level outcomes and estimate each one exactly as the analysis will.

```python
import random
from statistics import fmean, stdev


def paired_effect(outcome, sched):
    """Mean within-block difference, treatment minus control.

    outcome: dict mapping (region, day, slot) to the window's outcome after washout.
    """
    by_block = {}
    for r in sched:
        key = (r["region"], r["day"], r["slot"])
        if key in outcome:
            by_block.setdefault(r["block"], {})[r["arm"]] = outcome[key]
    diffs = [b["treatment"] - b["control"] for b in by_block.values() if len(b) == 2]
    return fmean(diffs)


def simulated_se(outcome, make_schedule, n_sims=1000, seed=0):
    rng = random.Random(seed)
    estimates = [paired_effect(outcome, make_schedule(rng.randrange(2**32))) for _ in range(n_sims)]
    return stdev(estimates)


# make_schedule = lambda s: schedule(regions, history_start, day_pairs, 3, s)
# se = simulated_se(history_outcomes, make_schedule)
# mde = 2.8 * se   # alpha 0.05 two-sided, power 0.8
```

Use history of the same length and season as the planned test, and drop the washout from each historical window just as the analysis will, so the simulated noise matches the real one. Simulate each candidate window length and keep the one with the smallest minimum detectable effect that also respects the carryover.

## Worked example

Dispatch algorithm, three cities. Past deploys show median pickup time settling about 40 minutes after a change; config propagation adds 5. Washout 45 minutes.

- 2-hour windows: 12 per day, 75 minutes analysable each. Simulated SE on six past weeks, 21 day pairs: 3.1 seconds of median pickup.
- 3-hour windows: 8 per day, 135 minutes analysable each. Simulated SE: 2.6 seconds.
- Minimum detectable effect with 3-hour windows: about 2.8 × 2.6 ≈ 7.3 seconds over six weeks. The product team's threshold is 10 seconds, so six weeks of 3-hour windows suffices; 2-hour windows would also clear it but lose more time to washout for no gain.

The plan tells the owner: 1,008 analysable windows (3 cities × 42 days × 8), not millions of trips, and an interval roughly ±5 seconds wide.
