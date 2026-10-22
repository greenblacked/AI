# Worked example

Route: `POST /checkout`, p50 410 ms, p99 4.1 s, over one day.

## Cohort comparison

Slowest 1% (n = 380) against the median band (n = 3,800):

| Attribute | Median band | Slowest 1% |
| --- | --- | --- |
| version 2.14 | 4% | 71% |
| region eu-west | 33% | 36% |
| payment cache miss | 12% | 14% |
| items in cart over 40 | 3% | 9% |

The version separates the cohorts; region and cache do not. Cart size is mildly skewed
and is worth a second look after the version is understood.

## Hop budget for one slow 2.14 trace (4,150 ms)

Critical path from the root:

| Hop | Time on path | Share | Kind |
| --- | --- | --- | --- |
| checkout handler self time | 140 ms | 3% | work |
| gap before inventory call | 610 ms | 15% | gap (unattributed) |
| inventory call, 38 identical child queries (2,300 ms) plus 100 ms self | 2,400 ms | 58% | N+1 |
| payment call | 420 ms | 10% | work |
| order write | 380 ms | 9% | work |
| response serialisation | 200 ms | 5% | work |

Self time of the inventory span: 2,400 ms duration minus the union of its child
intervals. The 38 children run one after another for 2,300 ms in total, leaving 100 ms
self. If they had overlapped, the union would have been shorter than the sum, which is the
reason to merge intervals before subtracting.

## Fan-out arithmetic

The pricing step calls 25 shard replicas in parallel. If each exceeds its own p99 on 1% of
calls, at least one is slow on 1-(0.99)^25, about 22% of requests. The step's median
already sits near the shards' tail.

## Next measurements

1. Compare the 2.14 diff for the inventory loop; confirm the query count per request is 38
   in 2.14 and 1 in the previous version.
2. Add a span around the 610 ms gap, or log connection pool wait time, to separate pool
   starvation from uninstrumented work.
3. Rerun the cohort comparison for 2.14 after the loop is batched.
