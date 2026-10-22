# Scoring and test skeletons

## Slicing a long window

Fetch in weekly slices and concatenate. A shell loop over GNU date:

```bash
set -Eeuo pipefail
OUT=$(mktemp -d)   # fresh directory per run, so slices from an earlier EXPR are never picked up
for week in $(seq 0 12); do
  s=$(date -u -d "-$((week + 1)) week" +%s)
  e=$(date -u -d "-${week} week" +%s)
  curl -sG --fail-with-body "$PROM/api/v1/query_range" \
    --data-urlencode "query=$EXPR" \
    --data-urlencode "start=$s" --data-urlencode "end=$e" \
    --data-urlencode "step=60" > "$OUT/slice-$week.json"
done
```

Stop on any failed slice rather than scoring a partial history. `--fail-with-body` makes curl exit non-zero on an HTTP error; Prometheus also answers some problems with HTTP 200, so check each slice before use:

```bash
set -Eeuo pipefail
for f in "$OUT"/slice-*.json; do
  jq -e '.status == "success" and ((.warnings // []) | length == 0)' "$f" >/dev/null \
    || { echo "bad slice: $f" >&2; exit 1; }
done
```

Reduce each result to the intervals where the value is non-empty, merge slices, then drop intervals shorter than the rule's `for:` duration.

## Worked table

| Firing | Incident | Delay from impact start | Note |
| --- | --- | --- | --- |
| 03 Mar 14:12 to 14:50 | Checkout errors, impact 14:02 | 10 min | caught |
| 19 Mar 02:30 to 02:36 | none | n/a | false fire |
| none | Search outage 22 Mar, impact 09:00 | n/a | missed |

Summary: recall 1 of 2, median delay 10 minutes, false fires 1 in 13 weeks. The miss is the finding: read the missed incident's error ratio against the rule's short window before touching thresholds.

## Unit test skeleton

```yaml
rule_files:
  - rules/checkout.yml
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{job="checkout",code="500"}'
        values: '0+60x30'
      - series: 'http_requests_total{job="checkout",code="200"}'
        values: '0+940x30'
    alert_rule_test:
      - eval_time: 20m
        alertname: CheckoutErrorBudgetBurn
        exp_alerts:
          - exp_labels:
              severity: page
              job: checkout
```

Write cases for absent data, a spike shorter than `for:`, and a slow burn beside this one. Series notation `a+bxn` means start at a, add b, n times.

## Routing test checklist

- every assertion passes `--verify.receivers=<expected>`, so a wrong route fails the command
- every receiver is reached by at least one case
- a paging label set reaches the paging receiver and not the ticket one
- a label set missing `team` still reaches a receiver somebody reads
- a label set an inhibition rule should suppress is covered by a separate test of the inhibition, since the tester checks routes only
- the `continue` behaviour is asserted: the tester lists every receiver matched
