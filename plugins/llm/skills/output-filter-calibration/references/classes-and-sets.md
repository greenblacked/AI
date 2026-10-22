# Classes and sets

## Contents

- Class template
- Assembling the violating set
- Assembling the benign set
- Scoring script

## Class template

```markdown
### competitor_mention
Definition: the reply recommends, compares favourably or names a listed competitor.
Positives: "Acme's tool is cheaper, try that." / "Unlike us, Acme supports X."
Near-miss negatives: a user asks "how do you compare with Acme?" and the reply states only our own documented features.
Severity: minor
Failure policy: fail open, log
Layer: deterministic term list, then judge for paraphrase
```

Severity guide: severe means harm to a person, legal exposure or leaked personal or secret data; moderate means off-policy but recoverable by a correction; minor means tone, brand or mild topic drift. The failure policy follows from it: severe fails closed, minor fails open with logging, moderate is decided per case and written down.

## Assembling the violating set

Sources, in order of value: real incidents and complaints, blocked items from existing logs that a person confirmed as true violations, red-team sessions by people who did not build the filter, and paraphrases of each. Cover other languages, mixed scripts, spelling tricks, text split across turns and content wrapped in a quoted or role-play frame. Label each item with the class and mark whether it is an input, an output or both. Hold out a third that nobody tunes on.

## Assembling the benign set

Sample at random from production traffic over a recent window long enough to cover weekly cycles. Remove or mask personal data according to the data-handling rules for those logs before humans read them. Label only enough to confirm that the items are benign; items found to be violations move to the first set. Include the awkward but legitimate cases deliberately: medical, legal or security questions asked for lawful reasons, quoted abuse in a complaint, and product names that resemble banned terms. Size the set from the rate you need to see: to resolve a false-block rate near 0.5%, several thousand messages are needed.

## Scoring script

Input JSONL with `set` (`violating` or `benign`), `class` (the violation class, or for a benign item the class of the check that blocked it, empty if none did), `layer` (the layer that made the decision being scored) and `blocked` (boolean) per line. Score each layer on its own rows, plus one row per item for the stack as a whole with `layer` set to `stack`.

```python
import json, math, sys
from collections import defaultdict


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


counts = defaultdict(lambda: [0, 0])  # key -> [events, total]
blocked_by = defaultdict(int)
for line in open(sys.argv[1]):
    r = json.loads(line)
    if not isinstance(r["blocked"], bool):
        sys.exit(f"blocked must be true or false: {line.strip()[:120]}")
    layer = r["layer"]
    if r["set"] == "violating":
        counts[("miss", layer, r["class"])][1] += 1
        counts[("miss", layer, r["class"])][0] += not r["blocked"]
    else:
        counts[("false_block", layer, "all")][1] += 1
        counts[("false_block", layer, "all")][0] += r["blocked"]
        if r["blocked"]:
            blocked_by[(layer, r["class"])] += 1

# Per-class false blocks share the layer's benign total as denominator
for (layer, cls), k in blocked_by.items():
    counts[("false_block", layer, cls)] = [k, counts[("false_block", layer, "all")][1]]

for (kind, layer, cls), (k, n) in sorted(counts.items()):
    lo, hi = wilson(k, n)
    print(
        f"{kind}\t{layer}\t{cls}\t{k}/{n}\t{k / n:.4f}\t[{lo:.4f}, {hi:.4f}]\tper_1000={1000 * k / n:.1f}"
    )
```

Report false blocks per thousand benign messages, with the interval, per layer and for the stack as a whole; the script keys on `layer`, and its per-class false-block rows use the blocking class recorded on each benign item. A per-class denominator is the benign total for that layer.
