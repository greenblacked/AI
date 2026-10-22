# Redis memory queries

Reference for steps 1 to 3. All commands are read-only unless marked. Run sampling
commands against a replica where possible.

## Contents

- [Eviction policies](#eviction-policies)
- [INFO fields that matter](#info-fields-that-matter)
- [Sampling commands](#sampling-commands)
- [Reading the numbers](#reading-the-numbers)

## Eviction policies

| Policy | Evicts | Use for |
| --- | --- | --- |
| `noeviction` | Nothing; writes fail with the OOM error | Durable stores and queues |
| `allkeys-lru` | Least recently used, any key | General cache |
| `allkeys-lfu` | Least frequently used, any key | Cache with a stable hot set |
| `allkeys-random` | Random key | Rarely the right choice |
| `volatile-lru`, `volatile-lfu` | Same, but only keys with a TTL | Mixed instance where TTL marks disposable data |
| `volatile-random` | Random key with a TTL | Rare |
| `volatile-ttl` | Keys with the nearest expiry | Short-lived data |

A `volatile-*` policy with no keys carrying a TTL behaves like `noeviction`.

## INFO fields that matter

`INFO memory`: `used_memory`, `used_memory_rss`, `used_memory_peak`, `maxmemory`,
`maxmemory_policy`, `mem_fragmentation_ratio`, `used_memory_overhead`,
`used_memory_dataset`, `mem_clients_normal`, `mem_clients_slaves`,
`mem_replication_backlog`, `mem_aof_buffer`.

`INFO stats`: `evicted_keys`, `expired_keys`, `keyspace_hits`, `keyspace_misses`.

`INFO keyspace`: per database `keys`, `expires`, `avg_ttl`.

`INFO persistence`: `rdb_last_cow_size`, `aof_rewrite_in_progress`. `INFO stats`: `latest_fork_usec`.

`MEMORY STATS` and `MEMORY DOCTOR` summarise the same data and give a plain-language hint.

## Sampling commands

```bash
redis-cli --memkeys -i 0.1
redis-cli --bigkeys -i 0.1
redis-cli --scan --pattern 'session:*' -i 0.1 | head -1000
redis-cli MEMORY USAGE session:abc SAMPLES 5
redis-cli TTL session:abc
redis-cli CLIENT LIST
```

For a per-prefix total, scan with `--scan --pattern 'prefix:*'`, run `MEMORY USAGE` on a
sample of the names, and multiply the mean by the prefix's key count. Say in the report
that it is an estimate from a sample of N keys.

In `CLIENT LIST` read `omem` (output buffer bytes) and `tot-mem` per client; one client
with a large figure is a slow consumer.

## Reading the numbers

- `used_memory` near `maxmemory` with `evicted_keys` rising: the policy is working, and
  the question is whether the evicted keys were needed (check the hit ratio).
- `used_memory` far below `maxmemory` but `used_memory_rss` high: fragmentation or
  copy-on-write from a fork, not data.
- `used_memory_overhead` large: buffers and replication state, not keys.
- Keys equal to expires: every key has a TTL, so growth is new keys arriving faster than
  they expire, not forgotten expiries.
