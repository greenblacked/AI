# Step test

Read this when planning or interpreting the load test that proves the protection.

## Plan

1. Measure capacity: the highest arrival rate at which p99 stays within objective with no rejections. Call it 1x.
2. Use an open-loop generator, one that fires at a fixed rate whatever the responses do. Tools such as k6 (`constant-arrival-rate` executor), wrk2 and Vegeta are open-loop; a plain thread-per-user loop is closed-loop.
3. Hold each step for several minutes so queues reach steady state: 1x, 1.5x, 2x, 5x. Then drop to 0.5x for at least as long as the longest queue could take to drain.
4. Use a realistic request mix and set the client timeout to the caller's real deadline, so goodput counts only answers that would still be wanted.

## Table to fill in

| Load | Offered rps | Success rps in deadline | Rejected rps | Timed out rps | Admitted p99 | Reject p99 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1x | | | | | | | |
| 1.5x | | | | | | | |
| 2x | | | | | | | |
| 5x | | | | | | | |
| 0.5x after | | | | | | | recovery time |

Goodput ratio = success in deadline at the step divided by success at 1x. Target about 0.9 or above.

## Failure patterns

| Observation | Meaning |
| --- | --- |
| Goodput falls as load rises | Queueing or thrashing; limit too high or queue unbounded in time |
| Many timed-out, few rejected | Rejection threshold above what callers tolerate; shed earlier |
| Rejections slow | The reject path does real work; move it earlier |
| Latency stays high after load drops | Backlog or retry feedback; apply the recovery lever and check caller retries |
| Low-priority traffic fine, high-priority starved | Priority assigned after the queue, not before |
| Good at 2x, collapses at 5x | A second resource saturates in the rejection path; profile it |

## Evidence to record

Limit values in force, queue depth over time, CPU and pool utilisation, count of dropped-by-age requests, and the time from load removal to p99 within 10 percent of baseline.
