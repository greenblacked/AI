# Route comparison

Read this at steps 5 and 6. The comparison has two halves: synthetic requests against both
addresses before any traffic moves, and per-route error rate and latency while it moves.

## Contents

- [Before traffic: the same request to both addresses](#before-traffic-the-same-request-to-both-addresses)
- [Edge cases beyond routes.tsv](#edge-cases-beyond-routestsv)
- [During the shift: per-route error rate and latency](#during-the-shift-per-route-error-rate-and-latency)
- [Abort condition, written before the first step](#abort-condition-written-before-the-first-step)

## Before traffic: the same request to both addresses

`curl --resolve` pins a hostname to an address for one request, so DNS is out of the
picture and the `Host` header and SNI are still correct.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
# routes.tsv: host<TAB>path, one row per inventory route, plus the edge cases below
OLD_IP="${1:?old controller address}"
NEW_IP="${2:?new controller address}"

probe() {
  local ip="$1" scheme="$2" host="$3" path="$4" port
  port=443; [[ "$scheme" == http ]] && port=80
  curl -sk -o /dev/null --max-time 10 \
    --resolve "${host}:${port}:${ip}" \
    -w '%{http_code} %{redirect_url} %{size_download}' \
    "${scheme}://${host}${path}" || printf 'ERR'
}

rows=0
unreachable=0   # old-side probes that got no HTTP status (000 or ERR)
healthy=0       # old-side probes that returned a 2xx or 3xx
while IFS=$'\t' read -r host path || [[ -n "$host" ]]; do
  [[ -n "$host" ]] || continue
  rows=$((rows + 1))
  for scheme in http https; do
    old="$(probe "$OLD_IP" "$scheme" "$host" "$path")"
    new="$(probe "$NEW_IP" "$scheme" "$host" "$path")"
    case "$old" in
      000*|ERR*|*ERR) unreachable=$((unreachable + 1)) ;;
      [23][0-9][0-9]\ *) healthy=$((healthy + 1)) ;;
    esac
    if [[ "$old" != "$new" ]]; then
      printf 'DIFF\t%s://%s%s\told=%s\tnew=%s\n' "$scheme" "$host" "$path" "$old" "$new"
    fi
  done
done < routes.tsv
printf 'compared %d routes over http and https\n' "$rows"
[[ "$rows" -gt 0 ]] || { echo 'routes.tsv is empty: nothing was compared' >&2; exit 1; }
# If both addresses fail the same way every row compares equal, so require the old side to work.
[[ "$healthy" -gt 0 ]] || {
  echo "old side returned no 2xx or 3xx ($unreachable unreachable): the comparison proves nothing" >&2
  exit 1
}
```

The loop reads `routes.tsv` on stdin and `curl` does not touch it, so no later row is
swallowed. The `|| [[ -n "$host" ]]` keeps a final row that lacks a trailing newline, and
the summary line stops an empty or misnamed file from looking like a clean run. The final
guard covers the other way to a false pass: if both addresses are unreachable, or both
return the same error for every row, nothing differs, so the script fails unless at least
one old-side probe returned a 2xx or 3xx.

`-k` is there because the new Gateway's certificate may not be issued for the name yet
during early testing; drop it once the Gateway holds the real certificate, and add a check
that the presented certificate matches.

Response size is a cheap proxy for "same page"; for routes where content matters, compare a
hash of the body or a specific header instead.

## Edge cases beyond routes.tsv

Each of these is decided by a default rather than by anything in the Ingress object. The
loop above reads only host and path and sends only GETs, so the first five rows can go in
`routes.tsv`; send the rest as separate one-off `curl --resolve` requests against both
addresses (with `--data-binary @file`, credentials or a source address as the row says) and
compare the results by hand.

| Request | What it catches |
| --- | --- |
| `http://` on a TLS host | The implicit HTTPS redirect |
| `/path` and `/path/` | Trailing-slash and prefix semantics |
| `/apiv2` where a route is `/api` | String-prefix against path-element matching |
| Mixed-case path on a regex route | Case-insensitive regex in the old controller |
| A host with no route | The default backend |
| A `POST` with a 2 MiB body (use `--data-binary @file`) | The 1 MiB default body limit |
| A request to an endpoint that takes over 60 seconds | Upstream timeout defaults |
| A request with and without credentials on an authenticated route | That auth was ported and fails closed |
| A request from outside an allow-listed range | That the allow-list was ported and fails closed |

## During the shift: per-route error rate and latency

Compare the same route on both sides, at the same time, over the same window. On the old
side, ingress-nginx exports per-Ingress request counts and duration histograms:

```promql
# 5xx ratio per host and Ingress, old controller
sum by (host, ingress) (rate(nginx_ingress_controller_requests{status=~"5.."}[5m]))
  / sum by (host, ingress) (rate(nginx_ingress_controller_requests[5m]))

# p99 per host and Ingress, old controller
histogram_quantile(0.99,
  sum by (le, host, ingress) (rate(nginx_ingress_controller_request_duration_seconds_bucket[5m])))
```

Metric names and labels on the new side depend on the implementation, so write the matching
pair of queries for it before the first shift and check that both return data. Where the
two sides' metrics cannot be made comparable, compare at a layer both share: the cloud load
balancer's access logs or metrics per address, or a synthetic probe hitting each address on
a fixed schedule.

Three things that make the comparison misleading:

- **Different traffic mixes.** At 1 per cent, the new side sees a sample that may not
  include the slow endpoints. Compare per route, not per host.
- **Cold caches and connection pools.** The first minutes on the new side are slower for
  reasons that disappear. Hold each step long enough to get past them.
- **Health-check traffic.** Load-balancer and uptime probes inflate request counts and
  flatter latency. Exclude their user agents or paths from both sides.

## Abort condition, written before the first step

State it as a number you can check, for example: abort and set the weight back when any
route's 5xx ratio on the new address exceeds the old by more than an agreed margin over
two consecutive five-minute windows, or its p99 exceeds the old by more than an agreed
fraction. Agree the margins with the route owners in advance; deciding them during the
shift is how a regression gets talked into acceptable.
