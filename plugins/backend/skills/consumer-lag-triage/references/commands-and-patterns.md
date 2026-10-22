# Commands and patterns

Read this when you need the exact output columns, the extra diagnostic invocations, or the configuration defaults to compare against.

## Describe output

`kafka-consumer-groups.sh --bootstrap-server $B --describe --group $G` prints one row per partition:

| Column | Meaning |
| --- | --- |
| `GROUP`, `TOPIC`, `PARTITION` | What the row describes |
| `CURRENT-OFFSET` | Next offset the group will consume (last committed) |
| `LOG-END-OFFSET` | Next offset to be written to the partition |
| `LAG` | `LOG-END-OFFSET` minus `CURRENT-OFFSET` |
| `CONSUMER-ID`, `HOST`, `CLIENT-ID` | The member holding the partition; `-` when unassigned |

A partition with `-` for the consumer id has no owner. If several do, the group is mid-rebalance or short of members.

## Other views

```bash
kafka-consumer-groups.sh --bootstrap-server $B --describe --group $G --state
kafka-consumer-groups.sh --bootstrap-server $B --describe --group $G --members --verbose
kafka-consumer-groups.sh --bootstrap-server $B --list
kafka-topics.sh --bootstrap-server $B --describe --topic $T
kafka-configs.sh --bootstrap-server $B --describe --entity-type topics --entity-name $T
```

`--state` shows the coordinator, the assignment strategy and the state: `Stable`, `PreparingRebalance`, `CompletingRebalance`, `Empty` or `Dead`. A group that stays in `PreparingRebalance` is waiting for members to rejoin. `--members --verbose` adds the assigned partitions per member. The topic description gives the partition count (the ceiling for useful consumers); the topic config shows `retention.ms`.

## Defaults to compare against

| Setting | Default | Note |
| --- | --- | --- |
| `max.poll.interval.ms` | 300000 (5 minutes) | Maximum gap between `poll()` calls |
| `max.poll.records` | 500 | Records returned per `poll()` |
| `session.timeout.ms` | 45000 from Kafka 3.0, 10000 before | Heartbeat deadline |
| `heartbeat.interval.ms` | 3000 | Keep to about a third of the session timeout or less |
| `auto.offset.reset` | `latest` | Applies only when there is no valid committed offset |
| `offsets.retention.minutes` | 10080 (7 days) | Broker setting; counts from when the group becomes empty |

Confirm the values the deployment actually sets; defaults here are a starting point for the comparison.

## Reading the pattern

| Signal | Points to |
| --- | --- |
| All offsets advance, lag deltas positive | Consumption slower than production: throughput deficit |
| One offset delta is zero, others positive | Poison record or blocked handler on that partition's owner |
| One partition's rate is a fraction of siblings with no errors | Hot key |
| `CommitFailedException` after a long batch | Poll gap exceeded `max.poll.interval.ms` |
| Members joining and leaving between snapshots | Rebalance churn; check GC and CPU throttling on those hosts |
| Repeated rebalance at each deploy | Restarts without static membership |
| Lag zero, records missing, group was down for days | Expired offsets plus `auto.offset.reset=latest` |

## Age of the oldest unprocessed record

```bash
kafka-console-consumer.sh --bootstrap-server $B --topic $T --partition $P \
  --offset $CURRENT_OFFSET --max-messages 1 --timeout-ms 10000 --property print.timestamp=true
```

The timeout stops the command waiting forever on a partition with zero lag or an offset older than retention. On a compacted topic the record returned can be a later one, so treat the age as approximate. A committed offset of `-` means nothing has been committed, so there is nothing to fetch.

The timestamp printed is `CreateTime` or `LogAppendTime` depending on the topic configuration. Subtract it from the current time. Do this for the partition with the largest lag, and for a stuck partition to learn how long it has been stuck.

## Dry-run reset checklist

1. Group state is `Empty`.
2. Command run with `--dry-run`, planned offsets read for every partition.
3. Skipped or replayed range stated, with the handlers' idempotency confirmed.
4. Then `--execute`, followed by a describe to confirm the new offsets.
