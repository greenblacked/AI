# Backtest harness

## Contents

- The loop
- Scoring by horizon step
- Interval coverage and calibration
- Checks before trusting the harness

A rolling-origin backtest written with the standard library only, so the logic is visible and the same code can wrap any model. Swap the forecaster for your own; keep the loop.

## The loop

`y` is one series as a list of floats in time order. `m` is the season length in periods (7 for daily data with a weekly pattern, 52 for weekly data with a yearly one). `h` is the horizon the decision needs. `latency` is how many of the most recent periods are not yet known when the forecast runs.

```python
import math
import statistics


def seasonal_naive(train, h, m):
    """Forecast each future step with the value one season earlier."""
    last_season = train[-m:]
    return [last_season[k % m] for k in range(h)]


def naive(train, h, m):
    return [train[-1]] * h


def backtest(y, forecaster, h, m, first_origin, step, latency=0):
    """Yield one record per origin and horizon step.

    At origin t the model sees y[:t - latency] and must forecast y[t:t + h].
    The latency periods are forecast too and discarded, as they would be live.
    """
    for origin in range(first_origin, len(y) - h + 1, step):
        train = y[: origin - latency]
        forecast = forecaster(train, h + latency, m)[latency:]
        scale = mase_scale(train, m)
        for k in range(h):
            yield {
                "origin": origin,
                "step": k + 1,
                "actual": y[origin + k],
                "forecast": forecast[k],
                "scale": scale,
            }


def mase_scale(train, m):
    """In-sample mean absolute error of seasonal naive: the MASE denominator."""
    diffs = [abs(train[i] - train[i - m]) for i in range(m, len(train))]
    return statistics.fmean(diffs) if diffs else math.nan
```

`first_origin` must leave at least two full seasons of training data, or the seasonal baseline and the MASE scale are computed from too little. Choose `step` to match how often the forecast runs live, and choose the range so that the origins span at least one full season.

## Scoring by horizon step

```python
from collections import defaultdict


def score(records):
    """MASE, WAPE and bias per horizon step."""
    by_step = defaultdict(list)
    for r in records:
        by_step[r["step"]].append(r)
    out = {}
    for step, rows in sorted(by_step.items()):
        abs_err = [abs(r["forecast"] - r["actual"]) for r in rows]
        signed = [r["forecast"] - r["actual"] for r in rows]
        actual_sum = sum(abs(r["actual"]) for r in rows)
        scaled = [e / r["scale"] for e, r in zip(abs_err, rows) if r["scale"] > 0]
        out[step] = {
            "n": len(rows),
            "mase": statistics.fmean(scaled) if scaled else math.nan,
            "wape": sum(abs_err) / actual_sum if actual_sum else math.nan,
            "bias": sum(signed) / actual_sum if actual_sum else math.nan,
        }
    return out


baseline = list(backtest(y, seasonal_naive, h=8, m=52, first_origin=104, step=1))
candidate = list(backtest(y, my_model, h=8, m=52, first_origin=104, step=1))
for step, (b, c) in enumerate(zip(score(baseline).values(), score(candidate).values()), 1):
    print(
        step,
        round(b["wape"], 3),
        round(c["wape"], 3),
        "value added",
        round(b["wape"] - c["wape"], 3),
    )
```

Run every model on the same origins. Comparing a model scored on 2023 origins against a baseline scored on 2024 origins compares two different years, not two models.

To check the win is consistent rather than carried by a few origins, compute the per-origin difference in absolute error between baseline and candidate and count how many origins the candidate wins. A win on most origins is a decision; a win on the average driven by three origins is a question.

## Interval coverage and calibration

For a model that returns quantiles, record `lo` and `hi` in each record alongside `forecast` and count coverage per step:

```python
def coverage(records):
    by_step = defaultdict(list)
    for r in records:
        by_step[r["step"]].append(r["lo"] <= r["actual"] <= r["hi"])
    return {step: sum(hits) / len(hits) for step, hits in sorted(by_step.items())}
```

For a model with no intervals, or one whose coverage is off, build intervals from the backtest errors themselves. Using errors from earlier origins only keeps the calibration honest:

```python
def empirical_interval(past_records, step, level=0.8):
    """Quantiles of past forecast errors at this horizon step."""
    errors = sorted(r["actual"] - r["forecast"] for r in past_records if r["step"] == step)
    if len(errors) < 20:
        return None  # too few to estimate tails; widen the backtest first
    if not 0 < level < 1:
        raise ValueError("level must be strictly between 0 and 1")

    def at(p):  # linear interpolation between order statistics
        pos = p * (len(errors) - 1)
        i = int(pos)
        j = min(i + 1, len(errors) - 1)
        return errors[i] + (errors[j] - errors[i]) * (pos - i)

    return at((1 - level) / 2), at((1 + level) / 2)
```

Pass only records whose actual was already known at the origin being forecast, which means `origin + step <= current_origin - latency`. Errors from origins that overlap the current forecast period are outcomes the live forecast would not have seen, and calibrating on them makes coverage look better than production will deliver. Add the returned pair to the point forecast to get the interval. Errors widen with the horizon, so calibrate each step separately rather than pooling.

Score quantile forecasts with pinball loss, which rewards being close and penalises the wrong side asymmetrically:

```python
def pinball(actual, quantile_forecast, tau):
    diff = actual - quantile_forecast
    return max(tau * diff, (tau - 1) * diff)
```

## Checks before trusting the harness

- Seasonal naive at step 1 with `latency=0` should produce a MASE near 1 on the training data's own pattern; a value far from 1 on stable data usually means an off-by-one in the indexing.
- Shift the series by one period and confirm the scores shift, not stay identical. Identical scores mean the forecaster is reading the actual.
- Print one origin's training end date, first forecast date and last forecast date and check them against the latency and horizon by hand.
- Confirm no regressor in the feature-based model has a value later than the training end at fit time, except those declared known-future.
