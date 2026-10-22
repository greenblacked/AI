# Forecast layout

## Contents

- Sheet layout
- A worked example in miniature
- Median days-to-pay script

## Sheet layout

Columns: label, then one column per week with the week-commencing date, 13 in all.

| Row | Content |
| --- | --- |
| Opening balance | Bank balance in week 1; previous closing balance after |
| Receipts: signed work | One line per invoice or retainer, at expected pay week |
| Receipts: total | Sum of the above (excludes pipeline) |
| Payments: fixed costs | Rent, payroll, loans, subscriptions |
| Payments: tax set-aside | Transfers and tax payment dates |
| Payments: VAT or sales tax | Remittance in the week the filing is due |
| Payments: annual bills | Insurance, software, accountant, renewals |
| Payments: owner draw | Regular draw |
| Payments: total | Sum of the above |
| Closing balance | Opening + receipts total - payments total |
| Pipeline (weighted) | Separate line, not in the total |
| Closing balance with pipeline | For comparison only |
| Floor | The minimum cash amount repeated across weeks |
| Headroom | Closing balance - floor |

Highlight the minimum of the closing balance row and the week it occurs.

## A worked example in miniature

Opening balance 6,000, fixed costs 1,800 a week, first four weeks shown:

| Week | Opening | Receipts | Payments | Closing |
| --- | --- | --- | --- | --- |
| 1 | 6,000 | 0 | 1,800 | 4,200 |
| 2 | 4,200 | 3,000 (client A, median 38 days) | 1,800 | 5,400 |
| 3 | 5,400 | 0 | 4,300 (includes 2,500 insurance) | 1,100 |
| 4 | 1,100 | 0 | 1,800 | -700 |

The lowest balance is -700 in week 4, even though the business is profitable. A
client B invoice for 5,000 is due in week 3 on 30-day terms, but client B's median is
52 days, so the receipt belongs in week 7. Levers: ask client A about the next invoice
early (chase), move the insurance to monthly instalments (defer), pause the draw for two
weeks (cut). Rerun with those and record the new lowest balance.

## Median days-to-pay script

Input: a CSV with columns `client`, `invoice_date`, `paid_date` in YYYY-MM-DD form.

```python
import csv
import statistics
import sys
from datetime import date

by_client = {}
with open(sys.argv[1], newline="") as handle:
    for row in csv.DictReader(handle):
        by_client.setdefault(row["client"], [])
        if not (row.get("paid_date") or "").strip():
            continue  # still outstanding: no delay to measure yet
        issued = date.fromisoformat(row["invoice_date"])
        paid = date.fromisoformat(row["paid_date"])
        by_client.setdefault(row["client"], []).append((paid - issued).days)

for client, days in sorted(by_client.items()):
    if not days:
        print(
            f"{client}: no paid invoices (use the longest delay across all clients, as an assumption)"
        )
    elif len(days) < 5:
        print(
            f"{client}: longest {max(days)} days over {len(days)} paid invoices (too few for a median)"
        )
    else:
        print(f"{client}: median {statistics.median(days)} days over {len(days)} paid invoices")
```

Run it with `python3 median_days.py invoices.csv`. Rows with a blank `paid_date` are
skipped as outstanding, and a client with only outstanding invoices is still listed. A client with fewer than five paid invoices is better estimated
by the longest delay seen so far than by the median, which is what the script prints.
