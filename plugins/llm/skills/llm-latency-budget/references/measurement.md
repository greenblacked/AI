# Measuring latency per stage

## Fields to record per request

| Field | Source | Notes |
| --- | --- | --- |
| request_id, route, model | Your code | Join key across stages |
| t_enqueue, t_send | Your code | Their difference is your own queueing |
| t_first_byte | Streaming client | Time to first token as the user's server sees it |
| t_last_byte | Streaming client | Total |
| input_tokens | Provider usage block | Total prompt size |
| cache_read_tokens, cache_write_tokens | Provider usage block where reported | Splits cached from uncached |
| output_tokens | Provider usage block | Drives the second half of the wait |
| tool_spans | Your code | Name, start, end, parallel group |
| retrieval_ms | Your code | Separate from tool spans |
| ui_first_paint | Client telemetry | The moment the user sees progress |

Inter-token rate is `output_tokens / (t_last_byte - t_first_byte)`; skip rows where the two timestamps are equal (a single-chunk reply), since the division is undefined. Prompt processing is approximately `t_first_byte - t_send` minus network. Provider field names vary; read the usage block your provider documents rather than assuming the names above.

## Splitting cached from uncached

Providers differ on whether `input_tokens` includes cached tokens. Where it includes cache reads (an OpenAI-style `prompt_tokens`), uncached input is `input_tokens - cache_read_tokens`. Where it already excludes cache reads and writes, uncached input is `input_tokens` itself, and the total prompt is `input_tokens + cache_read_tokens + cache_write_tokens`; subtracting there goes negative or undercounts. Check the provider's usage documentation before choosing the formula. Bucket requests as warm (most of the prefix read from cache) or cold. Report both p95s. A large gap says the prefix is the lever.

## Percentile summary

```python
import json, sys, statistics

rows = [json.loads(l) for l in open(sys.argv[1])]
for bucket in ("warm", "cold"):
    for stage in ("queue_ms", "ttft_ms", "decode_ms", "tool_ms", "total_ms"):
        xs = sorted(
            r[stage] for r in rows if r.get("cache_bucket") == bucket and r.get(stage) is not None
        )
        if len(xs) < 20:
            print(bucket, stage, "too few samples")
            continue
        q = statistics.quantiles(xs, n=100)
        print(f"{bucket} {stage}: p50={q[49]:.0f} p95={q[94]:.0f} n={len(xs)}")
```

Each row carries a `cache_bucket` field of `warm` or `cold`, set from the split above. Run it on the JSON-lines log for the old path and again for the new one, on the same sample.
