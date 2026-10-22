# Queue analysis

## Contents

population queries, reading them, the replay harness, a widening schedule template, quality buckets

## Population by slice

```sql
SELECT date_trunc('hour', enqueued_at) AS hour, region, platform, party_size,
       count(*) AS tickets,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY wait_seconds) AS p50_wait,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY wait_seconds) AS p95_wait
FROM queue_tickets
WHERE enqueued_at >= now() - interval '28 days'
GROUP BY 1, 2, 3, 4;
```

Assumes a `queue_tickets` table with enqueue time and measured wait. Add a column for outcome (matched, cancelled, timed out): cancelled tickets are the players who gave up, and leaving them out understates the wait.

## Reading the result

- Tickets per hour in a slice below a handful: the pool is thin. Wait grows because arrivals are rare, not because the criteria are strict.
- p95 far above median in a deep slice: the tail is the extremes of rating (top and bottom). Widening schedule or a ceiling policy is the lever.
- Large difference between party sizes: parties of four or five wait far longer than solos because few exist. Consider party-size-specific windows rather than loosening everyone.
- Wait that rises sharply at one hour each day: a shift in who is online (regional time), usually solved by a cross-region merge at that hour.

## Replay harness shape

Input: a time-ordered list of tickets (arrival time, rating and uncertainty, region, platform, party, mode) taken from real history. Matcher under test: a function from the current waiting set plus the clock to a list of matches. Loop: advance the clock in small steps (for example one second), add arrivals, call the matcher, record matches formed and remove their members.

Output per run: wait distribution by slice, and for every formed match the predicted win probability from the rating model. Compare current and proposed matchers on the same input. Keep ratings fixed during replay; it measures the matcher, not the rating dynamics. Replays cannot show behaviour changes (players leave when they see long waits), so treat the result as an upper bound on improvement and leave the rest to the experiment.

## Widening schedule template

| Time waiting | Allowed rating difference | Allowed region | Notes |
| --- | --- | --- | --- |
| 0 to 15 s | narrow band | home only | |
| 15 to 45 s | 2x band | home plus nearest within latency limit | |
| 45 to 90 s | 3x band | any within latency limit | |
| ceiling (per tier) | stop widening | | bot or backfill, or longer-wait message |

Fill the values from the replay: choose the narrow band that gives the target quality at peak, and set the ceiling where the predicted fairness drops below the lower target bound.

## Quality buckets

Bucket matches by the stronger side's predicted win probability (for example 0.5 to 0.55, 0.55 to 0.6, 0.6 to 0.7, above 0.7; the first two are the good-quality buckets, the last is the worst), and by whether anyone in the match was in the provisional pool. Report leave-during-match, leave-after-match and next-day return for each. A change that raises the share of the good-quality buckets without growing the worst bucket's return loss is a real improvement.
