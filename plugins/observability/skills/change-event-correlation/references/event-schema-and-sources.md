# Event schema and sources

## Contents

- Record example
- Emitting from each source
- Annotation call
- Blast-radius query
- Checks

## Record example

```json
{
  "kind": "flag",
  "summary": "checkout-new-tax-engine raised from 10 to 50 percent",
  "service": ["checkout", "tax"],
  "environment": "prod",
  "version": "checkout-new-tax-engine=50",
  "actor": "maria@example.com",
  "start": "2026-03-04T13:58:12Z",
  "shape": "point",
  "end": null,
  "link": "https://flags.example.com/audit/12345"
}
```

Use the same record for a range: a batch run sets `shape` to `range`, `start` and, once finished, `end` (left empty while it is still running); a vendor maintenance window sets both from the announced window and the `service` list from the dependency map.

## Emitting from each source

| Source | How it reaches the stream |
| --- | --- |
| Deploys | A final pipeline step posts the record with the image digest and version, from the pipeline, not from the cluster, so a manual `kubectl` change is not mistaken for a pipeline deploy; a second record is written from the cluster's rollout events to catch the manual ones |
| Flags | The flag service's audit webhook or its event stream, mapped to `service` through the flag's owning service |
| Config and secrets | The config store's change feed, or the GitOps repository's merge events; for secrets record the name and version, never the value |
| Infrastructure | The Terraform apply step posts a summary with the changed resource addresses; console changes come from the cloud audit log subscription |
| Migrations | The migration runner posts start and end around each run |
| Batch | The scheduler's run history, or a wrapper that posts at start and finish |
| Scaling | Kubernetes events and the autoscaler's decisions, rate-limited so a flapping autoscaler does not bury everything |
| Vendors | The vendor's status feed or maintenance calendar, mapped to dependants through the dependency map |

## Annotation call

For a Grafana instance, with a service account token in `GRAFANA_TOKEN`:

```bash
set -Eeuo pipefail
curl -sS --fail-with-body -X POST "$GRAFANA_URL/api/annotations" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"time": 1772632692000, "tags": ["service:checkout", "kind:flag", "env:prod"], "text": "checkout-new-tax-engine to 50 percent"}'
```

Add `timeEnd` for a range. On each dashboard, add an annotation query that filters by tags with the service variable so the same stream serves every service.

## Blast-radius query

Resolve the service list first: the alerting service, plus the direct dependencies and callers from the service graph or the dependency map. Then query the store for `service` in that list, `environment` equal to the alert's environment, and an overlap with the window: `start <= window_end` and either `shape` is `point` with `start >= window_start`, or `shape` is `range` with `end` empty (still running) or `end >= window_start`. The explicit `shape` marker is what separates a point event, which has no end, from a range still running; without it year-old point events match. Order by `start` descending and cap at about ten lines in the page; the rest sit behind the link.

## Checks

- Diff of service names: telemetry set minus event set, and the reverse. Zero is the target.
- Clock check: take five events per source and compare with the source's own timestamp; flag any difference over a few seconds.
- Coverage: for the last three incidents, was the culprit change in the stream at the time of the page?
