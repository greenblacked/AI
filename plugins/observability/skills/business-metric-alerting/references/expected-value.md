# Expected value details

## Ratio distribution over history

The recording rules have no history when first created, and `orders:expected5m` needs four or more weeks of `orders:rate5m` behind it. Backfill `orders:rate5m`, `orders:expected5m` and the ratio with `promtool tsdb create-blocks-from rules`, or compute the ratio in the warehouse, and confirm the full 60 days are present before reading the quantile.

Record the ratio, then read its lower quantiles over a quiet period:

```yaml
- record: orders:observed_over_expected
  expr: orders:rate5m / (orders:expected5m > 0)
```

```promql
quantile_over_time(0.001, orders:observed_over_expected[60d])
```

Exclude known incidents by evaluating the quantile on the weeks that had none, or by joining against an incident series. Pick the alert fraction slightly under the result, then confirm in the backtest. Compute it separately for peak and off-peak hours when the spread differs.

## Growth

A business that grew 10 percent over the window has an expectation that runs low. Scale by the recent level:

```promql
orders:expected5m
  * (sum_over_time(orders:rate5m[7d]) / sum_over_time(orders:rate5m[7d] offset 1w))
```

Use a damped factor (cap it at a sensible range) so one unusual week does not move the expectation.

## Missing weeks

If a past week is missing data or contained a long outage, the median across the remaining weeks still works; require at least three present weeks, and fall back to a ticket-only alert otherwise. `count` over the `label_replace` union tells how many weeks contributed.

## Calendar series

Expose planned events as a gauge: `calendar_event{kind="holiday"} 1` while active, written by a small job that reads the calendar. Use it to mute, or to substitute the expectation from the same event last year. Add a pre-event ramp window if the event changes traffic before it starts.

## Zero-traffic alert

```promql
(sum(increase(orders_total[10m])) or on() vector(0)) == 0
and on() sum(orders:expected5m) > 0.1
```

The `or on() vector(0)` arm matters: when the counter series disappears (a deploy removed the event, tracking broke) `increase` returns an empty vector, and without the arm the comparison stays silent in exactly those cases. Add a promtool unit-test case in which the series stops being exposed and the alert must fire.

For quiet paths widen the window until the expected count in it is above about 20, so a gap of that length is surprising.
