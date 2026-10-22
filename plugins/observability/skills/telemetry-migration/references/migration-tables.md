# Migration tables and checks

Contents: dependency table, translation map, parity comparison, rollback test.

## Dependency table

| Consumer | Type | Reads (metric, attribute, index) | Owner | Criticality | New equivalent | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Checkout latency alert | Alert | trace.duration, service.name | payments | Pages | http.server.request.duration | Rewritten, awaiting parity |

Sources to export from: the old system's API listing monitors, dashboards and saved searches; the repository holding rule files and dashboard JSON; SLO definitions; runbooks and incident templates that quote queries. Search them with `grep -rn` for each old metric or index name so no consumer is found by omission.

Statuses: not started, rewritten, parity-checked, live on new, old retired, deleted by decision.

## Translation map

| Old | New | Change | Notes |
| --- | --- | --- | --- |
| service (tag) | service.name (resource attribute) | rename | Becomes a label via the backend's resource-to-label rule |
| trace.duration (ms) | span duration (ns in the protocol) | unit | Histogram boundaries differ |
| status: 200 (string) | http.response.status_code: 200 (int) | type | Regexes on the old string stop matching |
| index logs-* | Loki stream labels app, env | model | Full-text search becomes a label selector plus a line filter |

## Parity comparison

Run the same question against both systems over the same window and tabulate:

| SLI | Old | New | Difference | Tolerance | Explained |
| --- | --- | --- | --- | --- | --- |
| Request rate (per second) | | | | within 2 percent | |
| p99 latency | | | | within 5 percent | |
| Error ratio | | | | stated margin | |
| Trace count per hour | | | | stated margin | |
| Log lines per hour | | | | stated margin | |

Common legitimate differences: head or tail sampling that the old agent did differently, histogram bucket boundaries, a changed definition of "error", clocks, and instrumentation that the old agent added automatically and the new path does not.

## Rollback test

1. Choose a migrated service and a quiet hour.
2. Re-enable the old exporter or agent.
3. Time how long until old dashboards show current data and old alerts evaluate on it.
4. Re-disable it and confirm the new path was unaffected.
5. Record the time taken and any manual step that was needed.
