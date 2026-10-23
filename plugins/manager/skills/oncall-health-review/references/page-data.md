# Page data

## Fields to request

| Field | Why |
| --- | --- |
| Person paged (user id and name) | The unit of analysis is the person |
| Created, acknowledged, resolved timestamps (UTC) | Time to resolve, and hour-of-day bucketing |
| Service, rule or alert name | The three-bucket sort needs the source |
| Whether a human acted | Separates real interruptions from auto-resolves; if the tool cannot tell you, an acknowledgement or a note is the closest proxy |
| Escalation level | Primary versus secondary load |
| Shift identifier or schedule | Pages per shift |

Most paging tools export incidents or alerts as CSV or through their API. Use the tool's own report where one exists, and note the date range and any filters you applied.

## Per-person table from a CSV

Assumes a CSV with columns `person`, `created_at` (ISO 8601 with offset), `resolved_at`, `human_action` (true or false) and `tz` (the person's IANA time zone, for example Europe/London). Adjust the names to match the export. Run it against a copy of the file.

```python
import csv
import math
import sys
from collections import defaultdict
from datetime import datetime
from statistics import median
from zoneinfo import ZoneInfo

WORK_START, WORK_END = 9, 18  # local working hours; change to your policy


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


stats = defaultdict(
    lambda: {"pages": 0, "ooh": 0, "night": 0, "ooh_days": set(), "resolve": [], "auto": 0}
)
skipped = 0  # rows with no usable time zone or offset, reported at the end
with open(sys.argv[1], newline="") as fh:
    for row in csv.DictReader(fh):
        s = stats[row["person"]]
        if (row.get("human_action") or "").strip().lower() != "true":
            s["auto"] += 1  # counted in its own column, not as an interruption
            continue
        tz = (row.get("tz") or "").strip()
        try:
            created_utc = parse(row["created_at"])
            if created_utc.tzinfo is None:  # no offset: do not guess the machine's zone
                raise ValueError
            created = created_utc.astimezone(ZoneInfo(tz))
        except (ValueError, KeyError):  # ZoneInfoNotFoundError is a KeyError
            skipped += 1
            continue
        s["pages"] += 1
        out_of_hours = created.weekday() >= 5 or not WORK_START <= created.hour < WORK_END
        if out_of_hours:
            s["ooh"] += 1
            s["ooh_days"].add(created.date())
        if created.hour >= 23 or created.hour < 7:
            s["night"] += 1
        if row.get("resolved_at"):
            minutes = (parse(row["resolved_at"]) - parse(row["created_at"])).total_seconds() / 60
            s["resolve"].append(minutes)

print(
    "person,pages,auto_resolved,out_of_hours,sleep_interrupting,days_with_ooh_page,median_resolve_min,p90_resolve_min"
)
for person, s in sorted(stats.items()):
    r = sorted(s["resolve"])
    med = round(median(r)) if r else ""
    p90 = round(r[math.ceil(0.9 * len(r)) - 1]) if r else ""
    print(
        f"{person},{s['pages']},{s['auto']},{s['ooh']},{s['night']},{len(s['ooh_days'])},{med},{p90}"
    )
if skipped:
    print(f"skipped {skipped} rows with a missing time zone or no UTC offset", file=sys.stderr)
```

The script gives days with an out-of-hours page. Divide by that person's on-call days (from the schedule, not the page data, since a quiet day has no rows) to test the quarter-of-days flag. Count nights per shift from the same schedule. For the more-than-two-incidents flag, group the rows with human action by person and local night (23:00 to 07:00, dated by the evening it began) and count nights above two.

## Checks before trusting the table

- Time zones: confirm the `tz` column against where each person actually works. Travelling engineers and people on a different schedule are the usual exceptions.
- Duplicates: one incident can appear as several rows if it escalated. Count a person once per incident unless the tool shows separate pages.
- Overridden shifts: a swap means the person paged may not be the person scheduled. Use who was paged, and take the swap debt to the fairness ledger.
- Gaps: a month with no rows may mean a missing export, not a quiet month.
- Resolve time includes waiting for a fix to deploy. Use it for trend and to find the slowest recoveries, not to judge individuals.
