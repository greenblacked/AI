# Floor queries

Read this when measuring the hourly floor, converting it into a commitment, and reading
utilisation and coverage. The queries are shapes: table and column names depend on how the
export was set up, so check them against your schema before trusting a number.

## Contents

- Why hourly, and where hourly data lives
- AWS: hourly floor from the Cost and Usage Report
- AWS: effective discount for your mix
- AWS: utilisation, coverage and recommendations
- Google Cloud: hourly floor from the billing export
- Reading the result

## Why hourly, and where hourly data lives

A commitment applies hour by hour; an hour where usage is below it wastes the difference.
Daily totals hide the overnight trough that decides the floor.

- **AWS:** Cost Explorer keeps hourly granularity only for a short recent window and only
  when enabled, so 90 days of hourly data comes from the Cost and Usage Report (legacy CUR
  or CUR 2.0 through Data Exports) with hourly time granularity, queried in Athena or a
  warehouse. If the report was set up daily, switch it to hourly now and measure on the
  data you have, marking the floor as provisional.
- **Google Cloud:** the standard billing export to BigQuery records `usage_start_time` per
  hour.

## AWS: hourly floor from the Cost and Usage Report

Compute Savings Plans cover EC2 instance usage regardless of family, size, region,
operating system and tenancy, plus Fargate and Lambda duration. Start with EC2, which is
usually most of it; add Fargate and Lambda lines identified by their usage types when they
are material. Exclude spot, which commitments do not cover.

```sql
WITH hourly AS (
  SELECT date_trunc('hour', line_item_usage_start_date) AS hour,
         SUM(pricing_public_on_demand_cost)              AS od_equivalent
  FROM cur
  WHERE line_item_usage_start_date >= date_trunc('day', current_timestamp) - INTERVAL '92' DAY
    AND line_item_usage_start_date <  date_trunc('day', current_timestamp) - INTERVAL '2' DAY
    AND line_item_line_item_type IN ('Usage', 'SavingsPlanCoveredUsage', 'DiscountedUsage')
    AND line_item_product_code = 'AmazonEC2'
    AND product_product_family = 'Compute Instance'
    AND line_item_usage_type NOT LIKE '%SpotUsage%'
  GROUP BY 1
)
SELECT min(od_equivalent)                       AS floor_raw,
       approx_percentile(od_equivalent, 0.05)   AS p5,
       approx_percentile(od_equivalent, 0.50)   AS median,
       avg(od_equivalent)                       AS mean,
       count(*)                                 AS hours
FROM hourly;
```

Including `SavingsPlanCoveredUsage` and `DiscountedUsage` (reserved-instance-covered) lines
matters: usage already covered still counts toward the floor, and step 4 of the skill
subtracts existing commitments explicitly. Using `pricing_public_on_demand_cost` puts every
line on the same on-demand basis whatever currently covers it.

The window is 90 whole days that end two days ago, on purpose. The report is delivered
with a lag, so the newest hours are incomplete and a partial hour reads as a false low:
a window ending now would take its minimum from the hours still being written, and a window
starting mid-hour adds a partial hour at the other end. Check `hours` against 90 times 24
(2,160). A shortfall means missing data, not a quiet period; an hour with no EC2 usage at
all has no row, so find the missing hours before accepting a minimum.
List the ten lowest hours with their timestamps before accepting the minimum; an outage or
a cut-over in that list is excluded with a written reason, a Sunday night is not.

For reserved instances on databases and caches, run the same shape per product code
(`AmazonRDS`, `AmazonElastiCache` and so on), grouped additionally by engine, instance
family and region, and measure in normalised instance units rather than dollars where the
reservation is size-flexible within a family.

## AWS: effective discount for your mix

Where Savings Plans already cover part of the fleet, the report shows the rate you
actually get:

```sql
SELECT savings_plan_savings_plan_a_r_n AS plan,
       SUM(savings_plan_savings_plan_effective_cost) / SUM(pricing_public_on_demand_cost) AS sp_to_od_ratio
FROM cur
WHERE line_item_line_item_type = 'SavingsPlanCoveredUsage'
  AND line_item_usage_start_date >= current_timestamp - INTERVAL '30' DAY
GROUP BY 1;
```

One row per plan, so read the row for a plan of the same type, term and payment option
as the one being priced.

The commitment for an uncovered floor is then roughly `uncovered_floor_od * sp_to_od_ratio`
dollars per hour. Without existing plans, take the published Savings Plans rates for the
top instance types by hours and weight them by their share of the floor. The ratio differs
by term, payment option and instrument, so compute it for the instrument you are pricing.

## AWS: utilisation, coverage and recommendations

```bash
aws ce get-savings-plans-utilization \
  --time-period Start=2026-09-21,End=2026-10-21 --granularity DAILY
aws ce get-savings-plans-coverage \
  --time-period Start=2026-09-21,End=2026-10-21 --granularity DAILY
aws ce get-reservation-utilization \
  --time-period Start=2026-09-21,End=2026-10-21 --granularity DAILY
aws ce get-reservation-coverage \
  --time-period Start=2026-09-21,End=2026-10-21 --granularity DAILY
```

The recommendation, as a cross-check against the floor:

```bash
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days SIXTY_DAYS
```

The longest lookback it accepts is sixty days. When it recommends more than the floor
supports, the difference is usage some hours do not have; the floor wins.

All of these read only. The purchase itself is a separate, deliberate action by the person
who owns the plan.

## Google Cloud: hourly floor from the billing export

Resource-based committed use discounts are bought in vCPUs and memory per machine series
and region, so measure in those units rather than in cost:

```sql
SELECT TIMESTAMP_TRUNC(usage_start_time, HOUR) AS hour,
       location.region                        AS region,
       sku.description                        AS sku,
       SUM(usage.amount) / 3600               AS units_per_hour,
       ANY_VALUE(usage.unit)                  AS unit
FROM `PROJECT.DATASET.gcp_billing_export_v1_XXXXXX`
WHERE service.description = 'Compute Engine'
  AND usage_start_time >= TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY), INTERVAL 92 DAY)
  AND usage_start_time <  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY), INTERVAL 2 DAY)
  AND (sku.description LIKE '%Instance Core%' OR sku.description LIKE '%Instance Ram%')
  AND sku.description NOT LIKE '%Spot%'
  AND sku.description NOT LIKE '%Preemptible%'
GROUP BY 1, 2, 3;
```

The window ends two days ago for the same reason as the AWS query: recent export rows are
still arriving. Check `unit` before reading the numbers: core usage is recorded in seconds, so dividing by
3600 gives vCPUs in that hour; memory is recorded in byte-seconds and needs converting to
GiB as well. Then take the minimum per machine series and region across the hours, as for
AWS. For spend-based (flexible) commitments, use `cost` summed per hour over eligible SKUs
instead, and read the existing discounts from the `credits` array, where committed-use and
sustained-use discounts appear as separate credit types.

## Reading the result

| Pattern | Meaning | Commit to |
| --- | --- | --- |
| Minimum close to p5, both well below median | A real daily or weekly trough | The minimum |
| Minimum far below p5 | A few anomalous hours | p5, after confirming the anomalies are one-off |
| Floor falling month over month | Rightsizing or migration already under way | Nothing new until it settles |
| Floor rising steadily | Growth | The current floor; the ladder catches growth next month |
| Median close to mean, minimum close to both | Flat, always-on fleet | The minimum, with a larger first tranche |
