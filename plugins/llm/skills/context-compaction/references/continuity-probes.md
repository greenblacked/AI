# Continuity probes

## Building the set

1. Collect 10 to 30 long sessions that reach the compaction point. Use real transcripts where privacy allows, otherwise scripted sessions with facts planted at known turns.
2. For each, write probes and their expected answers by reading the dropped turns yourself.
3. Probe kinds: recall (a decision, an id, a reason), constraint (a task that violates an early instruction if forgotten), state (what remains).

## Record format

```json
{"id": "s04-03", "session": "s04", "kind": "recall", "question": "Which file did we decide to change, and why?", "expected": ["src/billing/retry.py", "double charge"], "forbidden": []}
```

Give every probe a unique `id`. `expected` must not be empty: an empty list would pass vacuously. A recall or state probe passes if every expected string appears in the answer. A constraint probe also carries `forbidden` strings (for example the command the user ruled out); it is violated if any appears in the answer, and a string match for presence cannot detect that. Use a human check for borderline cases at first, then keep the string match.

## Scoring

```python
import json, sys


def load(path):
    rows = {}
    for line in open(path):
        r = json.loads(line)
        if not r["expected"]:
            sys.exit(f"probe {r['id']} has no expected strings")
        rows[r["id"]] = r
    return rows


def passed(r):
    return all(e.lower() in r["answer"].lower() for e in r["expected"])


def violated(r):
    return any(f.lower() in r["answer"].lower() for f in r.get("forbidden", []))


full, comp = load(sys.argv[1]), load(sys.argv[2])
if full.keys() != comp.keys():
    sys.exit(f"probe sets differ: {sorted(full.keys() ^ comp.keys())}")
if not full:
    sys.exit("no probes")
f_rate = sum(passed(r) for r in full.values()) / len(full)
c_rate = sum(passed(r) for r in comp.values()) / len(comp)
violations = sum(violated(r) for r in comp.values() if r["kind"] == "constraint")
print(
    f"uncompacted={f_rate:.2%} compacted={c_rate:.2%} gap={f_rate - c_rate:.2%} "
    f"constraint_violations={violations} n={len(full)}"
)
```

Each file holds the same probe rows plus an `answer` field from one run; a probe a run errored on or dropped must still appear, with an empty answer, so the two denominators match (the script stops when the id sets differ). Write the allowed gap before looking at results.

## Constraint violations

Count them separately from recall. One violation of a user's explicit instruction can matter more than several missed facts, so report the count, not only the rate.

## Finding the recompaction cap

Run the same probes after one, two and three consecutive compactions of the same session. The cap is the last count before accuracy leaves the allowed gap.
