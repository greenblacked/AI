# Redis patterns

Read this when implementing or reviewing a shared-store limiter: it has a GCRA outline and the checks for racy implementations.

## GCRA outline (single key, one Lua script)

State per key is the theoretical arrival time (TAT) in milliseconds. Parameters: `emission_interval` (milliseconds per allowed request, for example 100 for ten per second) and `burst_tolerance` (emission interval times the burst size).

```text
now = redis.call('TIME')            -- seconds and microseconds, converted to ms
tat = tonumber(redis.call('GET', key)) or now
tat = max(tat, now)
new_tat = tat + emission_interval * cost
allow_at = new_tat - burst_tolerance
if now < allow_at then
  return {0, allow_at - now}        -- rejected, ms until retry
end
redis.call('SET', key, new_tat, 'PX', new_tat - now + burst_tolerance)
return {1, 0}
```

Floor the millisecond values before calling `SET ... PX`, since Redis rejects a fractional expiry with "value is not an integer".

The script runs atomically because Redis executes a script as a single unit. All keys the script touches must be passed as `KEYS` so it works in Redis Cluster, where they must hash to one slot. In recent Redis versions, calling `TIME` before writes inside a script is permitted; on older versions with verbatim script replication it was restricted, so check the version in use.

## Sliding-window counter outline

Keep two counters per key, current and previous window. Estimated count = previous count times the fraction of the previous window still overlapping, plus the current count. Increment the current counter in the same script, and expire counters after two windows.

## Checks for a racy implementation

| Pattern found | Problem |
| --- | --- |
| `GET` then `SET` or `INCR` after a comparison, from application code | Two pods both pass the comparison |
| `INCR` then `EXPIRE` as two commands | A crash between them leaves a key that never expires |
| Timestamps from `Date.now()` or `time.time()` on the app host | Clock skew between pods shifts windows |
| Key without a TTL | Memory grows with every distinct caller |
| Separate keys for the count and the window start | Torn read between them |
| Fixed-window key built from the host's wall clock | Boundary burst and skew together |

## Local cache with periodic sync

Each pod leases a batch of tokens from the shared counter and spends them locally. Worst-case overshoot is the batch size times the number of pods, plus whatever is consumed between syncs. Choose the batch so that figure is an acceptable fraction of the limit, and write it next to the limit.

## Observability

Emit per decision: key class, tenant, allowed or limited, remaining, and latency of the store call. Count store errors separately and alert on them, since fail-open hides a broken limiter.
