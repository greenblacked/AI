# Flow sheet

## Contents

- Columns
- Worked sheet (CSV)
- JSON shape
- Computing the gates
- Sensitivity

The flow sheet is a file in version control, one row per flow. It is data, so a reward change is a one-line diff and the gates rerun in seconds.

## Columns

| Column | Meaning |
| --- | --- |
| `stock` | The currency or item the flow changes, for example `gold` |
| `flow` | A short name, for example `quest_reward` or `repair_cost` |
| `kind` | `source`, `sink` or `convert` (see below) |
| `archetype` | `new`, `engaged` or `grinder`, matching the archetype table |
| `band` | Level or progression band the row applies to, or `all` |
| `per_hour` | Units per hour of play for this archetype and band, always positive |
| `basis` | `assumed`, `designed` or `measured` |
| `note` | Where it lives in code or the design document |

A `convert` flow is written as two rows, one `sink` on the stock it spends and one `source` on the stock it produces, sharing the same `flow` name, so the conversion appears in both balances.

A separate small table holds the stocks:

| Column | Meaning |
| --- | --- |
| `stock` | Matches the flow rows |
| `cap` | Hard limit, or empty when there is none |
| `decay_per_hour` | Units lost per hour while held, or 0 |
| `lean` | `positive`, `flat` or `negative`: the intended sign of net inflow |
| `band_low`, `band_high` | Acceptable net inflow per hour for the archetype, stated before the result |

And the archetypes:

| Column | Meaning |
| --- | --- |
| `archetype` | Name |
| `hours_per_week` | Assumed play time |

## Worked sheet (CSV)

```text
stock,flow,kind,archetype,band,per_hour,basis,note
gold,quest_reward,source,engaged,all,420,designed,quests.json
gold,vendor_sale,source,engaged,all,150,assumed,shop.py
gold,repair_cost,sink,engaged,all,200,designed,durability.py
gold,upgrade_cost,sink,engaged,all,310,designed,upgrades.json
gold,quest_reward,source,grinder,all,780,designed,quests.json
gold,vendor_sale,source,grinder,all,260,assumed,shop.py
gold,repair_cost,sink,grinder,all,260,designed,durability.py
gold,upgrade_cost,sink,grinder,all,310,designed,upgrades.json
```

Engaged: 570 in, 510 out, net +60 per hour. Grinder: 1,040 in, 570 out, net +470 per hour, nearly eight times the engaged rate. If the stated band for the grinder is no more than twice the engaged rate, gate two fails and the finding is that the grinder's quest income scales and the sinks do not.

## JSON shape

The same data as one file, convenient when the sheet is generated from game data:

```json
{
  "archetypes": {"engaged": {"hours_per_week": 6}, "grinder": {"hours_per_week": 25}},
  "stocks": {"gold": {"cap": 999999, "decay_per_hour": 0, "lean": "positive"}},
  "flows": [
    {"stock": "gold", "flow": "quest_reward", "kind": "source", "archetype": "engaged",
     "band": "all", "per_hour": 420, "basis": "designed"}
  ],
  "purchases": [{"stock": "gold", "item": "first_weapon", "price": 3000}]
}
```

## Computing the gates

Net per hour for an archetype and stock is the sum of its `source` rows minus the sum of its `sink` rows, taking the rows for the band the player is in. Then:

- Time-to-cap, in hours of play, is `cap / net`, when net is positive and a cap exists. Divide by `hours_per_week / 7` to get calendar days.
- Time-to-afford is `price / net`, with the same conversion. A non-positive net means never.
- Where decay applies and the stock is held, net falls as the stock grows; the stock settles where `net_before_decay` equals `decay_per_hour` times the stock, so the ceiling is `net / decay_rate` when decay is proportional. State which form the game uses.
- The share wasted at the cap is the inflow that arrives after the cap is reached, over total inflow across a stated play span.

```python
import json
import sys

sheet = json.load(open(sys.argv[1]))
for arch, a in sheet["archetypes"].items():
    for stock, s in sheet["stocks"].items():
        rows = [f for f in sheet["flows"] if f["stock"] == stock and f["archetype"] == arch]
        net = sum(f["per_hour"] if f["kind"] == "source" else -f["per_hour"] for f in rows)
        per_day = a["hours_per_week"] / 7
        line = f"{arch:8} {stock:8} net/h {net:8.1f}"
        if net > 0 and s.get("cap"):
            h = s["cap"] / net
            line += f"  cap in {h:9.1f} h = {h / per_day:8.1f} days"
        elif not s.get("cap"):
            line += "  NO CAP: gate one needs a demand-backed sink"
        for p in sheet.get("purchases", []):
            if p["stock"] == stock:
                h = p["price"] / net if net > 0 else float("inf")
                line += f"  {p['item']} in {h:.1f} h"
        print(line)
```

Run it with `python3 script.py sheet.json`. It prints one line per archetype and stock; a line with `NO CAP` is not itself a failure, since a demand-backed sink satisfies gate one, but it is a line to check against the sheet.

## Sensitivity

Multiply each largest source and sink by 1.2 and by 0.8, rerun, and note which pass or fail result changes. A flow that flips a gate is the one that needs telemetry first after launch; give that list to `game-balance`.
