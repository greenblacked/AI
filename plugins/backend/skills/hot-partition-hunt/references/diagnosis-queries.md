# Diagnosis by store

Contents: DynamoDB, Kafka, Redis, Cassandra, MongoDB, arithmetic.

## DynamoDB

Enable CloudWatch Contributor Insights for the table (and for each global secondary index, which can be the hot spot on its own). Read the rules for most accessed items and most throttled items. Throttling with low `ConsumedReadCapacityUnits` relative to provisioned is the skew signature. Check `ThrottledRequests` and the read and write throttle events per table and per index. A throttled index can back-pressure writes to the base table.

## Kafka

`kafka-consumer-groups.sh --bootstrap-server <host:port> --describe --group <group>` prints `CURRENT-OFFSET`, `LOG-END-OFFSET` and `LAG` per partition. One partition far above the rest with other consumers idle points at a hot key in that partition; compare against the per-partition produce rate. If the lag stems from a stalled or rebalancing consumer rather than from key skew, that is a different diagnosis.

## Redis

`redis-cli --hotkeys` samples key access frequency and works only when `maxmemory-policy` is an LFU policy (`allkeys-lfu` or `volatile-lfu`). `redis-cli --bigkeys` finds large values by type. In cluster mode, compare CPU and operations per second per node; one node at its limit with others idle is key or slot skew.

## Cassandra

`nodetool toppartitions <keyspace> <table> <duration-ms>` samples the hottest partitions by read and write count for the duration. `nodetool tablehistograms` shows partition-size spread.

## MongoDB

`db.<collection>.getShardDistribution()` shows data and document spread per shard; `sh.status()` shows chunk distribution. Traffic skew can exist with even data, so compare per-shard operation counters as well.

## Arithmetic

- max/mean = highest per-partition rate divided by the mean of all partitions.
- Top-1-percent share = traffic from the busiest 1 percent of keys divided by total traffic.
- Split count N = ceil(peak writes per second for the key divided by (per-partition ceiling times a safety factor of about 0.5)).
- Fitting the Zipf exponent: rank keys by frequency, regress log frequency on log rank; the negative slope is the exponent.
