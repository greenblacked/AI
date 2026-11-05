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
| `kind` | `source` or `sink` |
| `archetype` | `new`, `engaged` or `grinder`, matching the archetype table |
| `band` | Level or progression band the row applies to, or `all` |
| `per_hour` | Units per hour of play for this archetype and band, always positive |
| `basis` | `assumed`, `designed` or `measured` |
| `note` | Where it lives in code or the design document |

A conversion is not a third kind. Write it as two rows, one `sink` on the stock it spends and one `source` on the stock it produces, sharing the same `flow` name, so the conversion appears in both balances. Give both rows the same `per_hour` only when one unit in is one unit out; otherwise each row carries its own rate.

A separate small table holds the stocks:

| Column | Meaning |
| --- | --- |
| `stock` | Matches the flow rows |
| `cap` | Hard limit, or empty when there is none |
| `decay_rate_per_hour` | Fraction of the held stock lost each hour (0.02 is 2 per cent), or 0. Always a fraction, never a flat amount |
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
  "stocks": {"gold": {"cap": 999999, "decay_rate_per_hour": 0, "lean": "positive"}},
  "flows": [
    {"stock": "gold", "flow": "quest_reward", "kind": "source", "archetype": "engaged",
     "band": "all", "per_hour": 420, "basis": "designed"}
  ],
  "purchases": [{"stock": "gold", "item": "first_weapon", "price": 3000}]
}
```

## Computing the gates

Net per hour for an archetype and stock is the sum of its `source` rows minus the sum of its `sink` rows, taking the rows for the band the player is in: a row marked `all` applies in every band, and a row with a named band applies only there. Never add rows across different bands, or the result describes a player who is in all of them at once; compute one net per band and report each. Then:

- Time-to-cap, in hours of play, is `cap / net`, when net is positive and a cap exists. Divide by `hours_per_week / 7` to get calendar days.
- Time-to-afford is `price / net` with the same conversion when there is no decay, and the time-to-cap formula with the price in place of the cap when there is. A non-positive net means never, and so does a price above the stock's cap, which the player can never hold, or at or above `net / decay_rate_per_hour`.
- Where decay applies, the game loses `decay_rate_per_hour` times the held stock each hour, so net falls as the stock grows and the stock settles at `net / decay_rate_per_hour`. If that is below the cap, the cap is never reached; if not, time-to-cap is `-ln(1 - cap * rate / net) / rate` hours. Decay is a fraction in every form here: do not mix it with a flat loss per hour.
- The share wasted at the cap is the inflow that arrives after the cap is reached, over total inflow across a stated play span.

```python
import json
import math
import sys

sheet = json.load(open(sys.argv[1]))
for arch, a in sheet["archetypes"].items():
    for stock, s in sheet["stocks"].items():
        rows = [f for f in sheet["flows"] if f["stock"] == stock and f["archetype"] == arch]
        # One net per band: a row for "all" counts in every band, a named band only in its own.
        bands = sorted({f["band"] for f in rows if f["band"] != "all"}) or ["all"]
        for band in bands:
            mine = [f for f in rows if f["band"] in (band, "all")]
            net = sum(f["per_hour"] if f["kind"] == "source" else -f["per_hour"] for f in mine)
            per_day = a["hours_per_week"] / 7
            rate = s.get("decay_rate_per_hour", 0)
            line = f"{arch:8} {stock:8} {band:8} net/h {net:8.1f}"
            cap = s.get("cap")
            if cap and net > 0:
                if rate and net / rate <= cap:
                    line += f"  never caps: settles at {net / rate:.0f}"
                else:
                    h = -math.log(1 - cap * rate / net) / rate if rate else cap / net
                    line += f"  cap in {h:9.1f} h = {h / per_day:8.1f} days"
            elif not cap:
                line += "  NO CAP: gate one needs a demand-backed sink"
            for p in sheet.get("purchases", []):
                if p["stock"] == stock:
                    price = p["price"]
                    # A price above the cap can never be held, whatever the inflow.
                    if net <= 0 or (cap and price > cap) or (rate and price >= net / rate):
                        line += f"  {p['item']} never"
                    else:
                        h = -math.log(1 - price * rate / net) / rate if rate else price / net
                        line += f"  {p['item']} in {h:.1f} h"
            print(line)
```

Save it as `flow_gates.py` and run it with `python3 -I flow_gates.py sheet.json`. It prints one line per archetype, stock and band; a line with `NO CAP` is not itself a failure, since a demand-backed sink satisfies gate one, but it is a line to check against the sheet.

## Sensitivity

Multiply each largest source and sink by 1.2 and by 0.8, rerun, and note which pass or fail result changes. A flow that flips a gate is the one that needs telemetry first after launch; give that list to `game-balance`.
