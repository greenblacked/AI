# Failure and rollout

Use this reference to turn fallback and rollback into bounded traffic plans.

## Failure matrix

For each cached operation, decide the response to a miss, cache timeout, cache error, stale entry, source timeout, and source overload. Record whether the request bypasses, serves stale, fails closed, or is rejected. Put a concurrency or rate bound on every path that reaches the source.

Microsoft's official [Cache-Aside pattern](https://learn.microsoft.com/azure/architecture/patterns/cache-aside) describes the consistency window, expiration trade-offs, local-versus-shared cache considerations, and the risk that cache failure sends requests to the data store. Use it for the pattern's constraints; derive numeric limits from measurements of the actual origin.

## Capacity evidence

Measure sustainable source throughput and latency without assuming the cache is available. Compare that budget with maximum admitted fallback concurrency, recovery fills, ordinary uncached traffic, and background jobs. Reserve headroom for retries and skew toward hot keys.

## Safe rollout

1. Compare cached and authoritative answers on a bounded sample.
2. Enable reads for a stable cohort while retaining a kill switch for fills and reads separately.
3. Ramp only while mismatch, stale-age, eviction, and source-headroom gates hold.
4. Keep serialization and key namespaces readable across the rollback window.
5. Exercise cache flush, regional impairment, and restart before full traffic.

## Safe rollback

Stop suspect fills before discarding useful entries. Reduce admission toward the cache-miss capacity of the source, shed optional requests, and drain background refreshes. If all entries may be corrupt or unsafe, fail closed where required and open bypass only at the measured rate. A rollback that flushes first and bypasses second creates the largest possible miss wave.
