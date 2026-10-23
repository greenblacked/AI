# Measuring result size and replaying tasks

## Trace format

One JSON object per line, one per tool call:

```json
{"task_id": "t17", "step": 4, "tool": "search_tickets", "result_text": "..."}
```

## Size per tool

```python
import json, sys, statistics
from collections import defaultdict


def tokens(text):
    # Replace with the provider's token counter when available.
    return max(1, len(text) // 4)


sizes = defaultdict(list)
for line in open(sys.argv[1]):
    r = json.loads(line)
    sizes[r["tool"]].append(tokens(r.get("result_text") or ""))

total = sum(sum(v) for v in sizes.values())
if not sizes:
    sys.exit("empty trace")
for tool, v in sorted(sizes.items(), key=lambda kv: -sum(kv[1])):
    v.sort()
    p95 = v[int(0.95 * (len(v) - 1))]
    print(
        f"{tool}: n={len(v)} median={statistics.median(v):.0f} p95={p95} max={v[-1]} share={sum(v) / max(total, 1):.0%}"
    )
```

The four-characters-per-token figure is an approximation. Say so when you report numbers from it.

## Replay protocol

1. Fix a task set of at least 30 tasks with a checkable outcome, including tasks where the answer needs a result the old shape returned in full.
2. Run each task with the old shapes and with the new, same model, same prompt, same seed settings where available. Run more than once when the model is not deterministic.
3. Record success, step count and total tool-result tokens per task.
4. Compare pairs. The gate: success rate not lower, tokens lower. Inspect every task that flipped to failure and name the missing field or count.
5. Keep the task set, so the next change to a tool is replayed against it.
