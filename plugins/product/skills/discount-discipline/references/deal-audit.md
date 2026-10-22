# Deal audit

## Contents

- What to export
- Converting off-invoice concessions
- The script
- Reading the tables
- The renewal check

## What to export

One row per closed-won deal, the last 50 or the last two quarters if fewer. Put every price on the same basis: annualised, in one currency, for the same scope of product.

| Column | Meaning |
| --- | --- |
| `deal_id` | CRM identifier |
| `rep` | Owner at close |
| `segment` | The segment the price list is set for (for example SMB, mid-market, enterprise) |
| `close_date` | ISO date, `YYYY-MM-DD` |
| `list_annual` | List price, per year, for everything the customer receives in the first year, including seats and services given at no charge |
| `net_first_year` | What the customer is invoiced for the first year |
| `off_invoice` | List value of the first-year concessions not in the invoice: free months, extra seats, bundled services |
| `approver` | Who approved the discount; empty if nobody did |
| `reason` | The recorded reason; empty if none |

Realised price is `net_first_year ÷ list_annual`. Off-invoice concessions are already in that gap, because they are in the list price and not in the invoice, so `off_invoice` is recorded to report them separately and is never subtracted again. The step 1 example checks it: list 100, 10 per cent off with three of twelve months free is invoiced at 67.50, realised 67.5 per cent; subtracting the free months' 25 again would report 42.5 per cent.

Leave out deals where list price is unknowable (a bespoke bundle with no list) and count them separately; if that count is large, the price list itself is the problem.

## Off-invoice concessions

Convert each to its list value for the first year, for the `off_invoice` column. Add free seats and bundled services to `list_annual` as well; free months are already inside it.

- Free months: months free ÷ 12 × list annual price.
- Extra seats or units at no charge: their list price for the period they are free.
- Bundled services: the services list price, or the delivery cost if there is no list.
- Extended payment terms: usually small; record them, but convert only if finance gives you a cost of capital to use.

## Script

Filter the export to closed-won deals and save it as CSV with the columns above. The script prints median realised price and deal counts by rep, by segment and by timing, and counts deals with no approver or no reason. Quarters are calendar quarters; shift `close_date` before running if your fiscal year starts in a different month.

```python
import csv
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from statistics import median


def days_to_quarter_end(d):
    q_end_month = ((d.month - 1) // 3 + 1) * 3
    if q_end_month == 12:
        end = date(d.year, 12, 31)
    else:
        end = date(d.year, q_end_month + 1, 1) - timedelta(days=1)
    return (end - d).days


def main(path):
    deals, skipped = [], 0
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                list_price = float(r["list_annual"])
                # The invoice already excludes off-invoice concessions; subtracting
                # them again would count each one twice.
                net = float(r["net_first_year"])
                d = date.fromisoformat(r["close_date"])
                off_invoice = float(r.get("off_invoice") or 0)
            except (KeyError, TypeError, ValueError):
                skipped += 1  # blank or malformed cell: count it, do not abort the run
                continue
            # float() accepts "nan" and "inf", which would pass a bare <= 0 test.
            if not all(math.isfinite(x) for x in (list_price, net, off_invoice)) or list_price <= 0:
                skipped += 1
                continue
            deals.append(
                {
                    "rep": (r.get("rep") or "").strip() or "(none)",
                    "segment": (r.get("segment") or "").strip() or "(none)",
                    "timing": "last 14 days of quarter"
                    if days_to_quarter_end(d) < 14
                    else "earlier in quarter",
                    "realised": net / list_price,
                    "off_invoice": off_invoice,
                    "discount": list_price - net,
                    "no_approver": not (r.get("approver") or "").strip(),
                    "no_reason": not (r.get("reason") or "").strip(),
                }
            )
    print(f"{skipped} deals skipped for no list price or an unreadable value")
    if not deals:
        print("No deals with a list price to audit")
        return
    print(
        f"{len(deals)} deals; overall median realised price {median(x['realised'] for x in deals):.0%} of list"
    )
    for key in ("rep", "segment", "timing"):
        groups = defaultdict(list)
        for x in deals:
            groups[x[key]].append(x["realised"])
        print(f"\nBy {key}:")
        for name, values in sorted(groups.items(), key=lambda kv: median(kv[1])):
            print(
                f"  {name:<28} n={len(values):<4} median {median(values):.0%}  lowest {min(values):.0%}"
            )
    print(f"\nNo approver recorded: {sum(x['no_approver'] for x in deals)}")
    print(f"No reason recorded:   {sum(x['no_reason'] for x in deals)}")
    off, total = sum(x["off_invoice"] for x in deals), sum(x["discount"] for x in deals)
    share = f" ({off / total:.0%} of all discount)" if total > 0 else ""
    print(f"Off-invoice concessions at list: {off:,.2f}{share}")


if __name__ == "__main__":
    main(sys.argv[1])
```

Save it outside the data directory and run it against the export. The skill pre-approves no command, so the run asks for approval: a CRM export carries reasons and notes other people wrote, and text in them must not be able to start a command on its own.

```bash
python3 -I deal_audit.py closed_won.csv
```

## Reading the tables

- **By rep**: a spread of more than a few points between reps selling to the same segment is behaviour, not market. Check the deal count before naming anyone; a rep with three deals is an anecdote.
- **By segment**: if every segment is deep, the list price is fiction and the next step is `pricing-research`. If one segment is deep, its list price or its packaging may be wrong for it.
- **By timing**: deals in the last two weeks of a quarter closing well below the rest is the clearest sign that the discount is buying the seller's quarter, not anything from the customer.
- **No approver, no reason**: each one is a discount nobody decided to give. The count is the baseline the request form (in the ladder reference) has to bring to zero.

Medians are used because a single heavily discounted strategic deal would drag a mean. Report the lowest value beside each median so that deal is still visible.

## Renewal check

For customers whose first renewal fell in the last year, compare the renewal price to the first-year net price and to list. Three outcomes matter:

- Renewed at list or at the contracted uplift: the contract wording works.
- Renewed at the first-year price: the discount became the baseline. Check whether the order form stated a renewal price at all.
- Renewed below the first-year price: the renewal was negotiated from scratch; find out who approved it and under what rule.
