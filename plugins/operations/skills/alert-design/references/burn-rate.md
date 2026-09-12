# Burn-rate alerting

Read this when writing or debugging SLO burn-rate rules: the arithmetic, the window
tables, the recording rules that keep the expressions honest, and the low-traffic case
where a ratio SLO stops working.

## Contents

- The arithmetic
- Window and threshold tables
- Recording rules
- Latency SLIs
- Low-traffic services
- Validating the rules before they ship

## The arithmetic

Error budget is `1 - SLO` over the compliance period. For a 99.9% SLO over 30 days the
budget is 0.1% of valid events.

Burn rate is the observed error ratio divided by the budget ratio. Burn rate 1 consumes
the budget exactly over the full period; burn rate 10 consumes it in a tenth of the
period.

```text
burn_rate = error_ratio / (1 - SLO)
time_to_exhaustion = period / burn_rate
budget_consumed(window) = burn_rate * window / period
```

The two numbers that set a page threshold are how much budget you are willing to lose
before someone is woken (2% is the common choice) and how long you are willing to wait
to detect it (1 hour). Those two fix the burn rate:

```text
burn_rate = budget_fraction * period / window
          = 0.02 * 720h / 1h
          = 14.4
```

Change either input and the rate moves. A team that would rather burn 5% before paging,
detected over 6 hours, gets `0.05 * 720 / 6 = 6`.

## Window and threshold tables

For a 30-day compliance period. The short window is one twelfth of the long window in
every row; that ratio is what makes the alert reset promptly without making it jumpy.

| Burn rate | Long window | Short window | Budget consumed at fire | Route |
| --- | --- | --- | --- | --- |
| 14.4 | 1h | 5m | 2% | Page |
| 6 | 6h | 30m | 5% | Page |
| 3 | 1d | 2h | 10% | Ticket |
| 1 | 3d | 6h | 10% | Ticket |

For a 7-day period, multiply the windows by 7/30 and keep the rates, or keep the windows
and recompute the rates with the formula above. Do one or the other deliberately; mixing
a 30-day rate with a 7-day period silently changes what fraction of the budget a page
costs.

Two page-severity rows are not redundant. The 14.4x row catches a sharp outage in
minutes; the 6x row catches a moderate, sustained degradation that would never trip the
1-hour window but will still exhaust the month. Ship both or accept that slow-moving
brownouts do not page.

## Recording rules

Write the ratio once, at several windows, and let the alerts compare against a constant.
Repeating the raw expression in four alerts guarantees the day someone fixes a label
selector in three of them.

```yaml
groups:
  - name: checkout-slo-ratios
    interval: 30s
    rules:
      - record: job:slo_errors_per_request:ratio_rate5m
        expr: |
          sum by (job) (rate(http_requests_total{job="checkout",code=~"5.."}[5m]))
          / sum by (job) (rate(http_requests_total{job="checkout"}[5m]))
      - record: job:slo_errors_per_request:ratio_rate1h
        expr: |
          sum by (job) (rate(http_requests_total{job="checkout",code=~"5.."}[1h]))
          / sum by (job) (rate(http_requests_total{job="checkout"}[1h]))
```

Repeat for 30m, 6h, 2h, 1d, 3d and 6h as the table needs. Name them consistently: the
`level:metric:operations` convention makes it obvious at a glance which window an alert
is comparing.

Two decisions to make explicitly rather than inherit:

- **What counts as an error.** 5xx yes; 4xx usually not, because a client sending bad
  input is not your budget to spend. A 429 you emitted under load is arguably yours.
- **What counts as valid.** Health checks, synthetic probes and internal traffic
  normally get excluded, or a prober outage reads as a customer outage.

## Latency SLIs

A latency SLO is still a ratio: the fraction of requests served faster than a threshold.
With a native or classic histogram, the threshold has to line up with a bucket boundary,
or the numerator is an interpolation and the alert is comparing against a number nobody
can reproduce.

```yaml
      - record: job:slo_latency_slow_requests:ratio_rate1h
        expr: |
          1 - (
            sum by (job) (rate(http_request_duration_seconds_bucket{job="checkout",le="0.5"}[1h]))
            / sum by (job) (rate(http_request_duration_seconds_count{job="checkout"}[1h]))
          )
```

Then alert on that ratio against the same burn-rate constants. Do not alert on
`histogram_quantile(0.99, ...) > 0.5` — the quantile of a low-traffic window is
extremely unstable, and a quantile crossing a line tells you nothing about how much
budget it cost.

## Low-traffic services

Below roughly one request per second, the ratio is dominated by single events: one
failure in a 5-minute window with 20 requests is a 5% error rate and a burn rate of 50.
Every option here is a trade-off, so pick one on purpose.

- **Generate traffic.** A synthetic prober at a known, constant rate gives the SLI a
  stable denominator and, as a bonus, covers the case where real traffic drops to zero.
  Keep prober traffic in a separate SLI from organic traffic rather than mixing them.
- **Lengthen the windows.** Move the page row to 6h/30m and drop the 1h row entirely.
  Detection gets slower; that is the honest cost of not having enough events.
- **Raise the SLO's granularity floor.** State the SLO over a longer period, or in terms
  of successful operations per day rather than a ratio per window.
- **Alert on absence instead.** For a service that handles a handful of important
  operations a day — a nightly batch, a billing run — a ratio is the wrong shape. Alert
  that the successful-completion counter did not increase inside the expected interval.

Do not solve it by adding a `for: 30m` to a noisy ratio. That delays the alert without
making the underlying number any less noisy, and it delays the real outage by the same
30 minutes.

## Validating the rules before they ship

```bash
promtool check rules slo-rules.yaml
promtool test rules slo-rules-test.yaml
amtool check-config alertmanager.yml
amtool config routes test --config.file=alertmanager.yml severity=page team=checkout
```

`promtool test rules` takes a series of synthetic samples and asserts which alerts fire
at which minute. It is the only way to prove a burn-rate rule fires when the budget
burns and clears when it stops, and it catches the two most common defects: a short
window that never satisfies the `and`, and a label selector that matches nothing so the
expression is permanently empty.

`amtool config routes test` answers the question that inhibition and grouping bugs hide:
given these labels, which receiver actually gets this? Run it for every severity you
define, and delete any severity whose answer duplicates another's.
