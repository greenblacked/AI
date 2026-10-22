# Metrics and baselines

## Error metrics

| Metric | Definition | Use it when | It misleads when |
| --- | --- | --- | --- |
| MAE | mean of absolute errors | One series, one unit, and people think in that unit | Comparing series of different size |
| RMSE | square root of mean squared error | Large misses cost disproportionately more | Comparing across series; a few outliers dominate |
| MASE | MAE divided by the in-sample MAE of seasonal naive | Comparing across series and against the baseline; below 1 means better than the in-sample one-step seasonal naive; the bar is the seasonal naive's own backtest MASE at the same horizon | The training period has no seasonal variation, so the scale is near zero |
| WAPE | sum of absolute errors divided by sum of actuals | Business series where high-volume items matter more | One huge series dominates and hides the rest; report by segment too |
| MAPE | mean of absolute errors divided by actuals | Avoid for operational series | Any actual is zero or near zero; it also penalises over-forecasts more heavily than under-forecasts |
| sMAPE | absolute error over the mean of absolute actual and forecast | Rarely; included because people ask | Asymmetric and unstable near zero despite the name |
| Bias | sum of (forecast minus actual) over sum of actuals | Always, beside one of the above | Never on its own: positive and negative errors cancel |
| Pinball loss | asymmetric absolute loss at quantile tau | Scoring a quantile forecast, such as the 90th percentile for stock | Comparing to point-forecast metrics directly |
| Coverage | share of actuals inside the interval | Checking an interval against its nominal level | Read without the interval width, since a huge interval covers everything |

Report error per horizon step. A model that is excellent one step ahead and poor eight steps ahead is the wrong model for an eight-week ordering decision, and the average across steps hides that.

## Baselines by data shape

| Data shape | Baseline the model must beat |
| --- | --- |
| Clear seasonality (weekly retail, daily traffic with a weekly cycle) | Seasonal naive: the value one season ago |
| Several seasonalities (hourly data with daily and weekly cycles) | Seasonal naive at the longer cycle, and at the shorter; keep the better |
| Trend without seasonality | Naive with drift: last value plus the average historical change per period |
| Noisy level, no trend or season | Naive (last value) and a moving average over a window chosen in the backtest |
| Intermittent demand (many zeros) | Zero forecast, and Croston's method or a simple average of non-zero demand times its frequency |
| Existing forecast in use | The current production forecast, scored in the same harness |

The current production forecast, or the planners' manual numbers, is the most important baseline when one exists. A model that beats seasonal naive but loses to the planners' spreadsheet does not replace the spreadsheet.

## Intermittent demand

When most periods are zero, point errors favour forecasting zero, which is useless for stocking. Instead:

- Score the quantity that drives the decision, usually a high quantile or the total over the replenishment lead time, with pinball loss or the error on the lead-time total.
- Aggregate in time (weeks instead of days) or in the hierarchy (category instead of item) until the series is no longer mostly zeros, forecast there, and allocate down.
- Use MASE or WAPE, never MAPE.

## Aggregating across many series

- Weight by the decision's value: revenue, units or margin. An unweighted average across ten thousand items lets the long tail of tiny items decide which model wins.
- Report the distribution as well as the average: the share of series where the candidate beats the baseline, and the worst decile.
- If forecasts at different levels (item, store, region) must add up, check coherence: the sum of item forecasts against the region forecast. Reconciliation methods exist for hierarchical series; whichever is used, score the level at which each decision is made.

## Choosing the backtest span

- At least one full seasonal cycle of origins, so the peak and the trough are both scored.
- Enough origins per horizon step that the error estimate is stable. With weekly origins over a year, each step has around fifty scored points, which is enough to compare models; a dozen is not.
- Exclude or mark periods a structural break makes unrepresentative, and report results with and without them.
