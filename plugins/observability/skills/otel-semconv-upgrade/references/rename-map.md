# Semantic-convention rename map

Contents: HTTP attributes, HTTP metrics, database attributes, Prometheus spellings, checks per language.

This is the commonly met set. Confirm each row against the convention and instrumentation release notes for your exact versions; some instrumentations moved earlier or later than others, and a few attributes were split into several rather than renamed.

## HTTP attributes

| Old | New |
| --- | --- |
| http.method | http.request.method |
| http.status_code | http.response.status_code |
| http.url | url.full |
| http.target | url.path and url.query |
| http.scheme | url.scheme |
| http.user_agent | user_agent.original |
| http.request_content_length | http.request.body.size |
| http.response_content_length | http.response.body.size |
| http.flavor | network.protocol.version (value is now the version, such as 1.1) |
| net.host.name and http.host | server.address (server side) |
| net.peer.name | server.address (client side) |
| http.route | unchanged |

## HTTP metrics

| Old | New | Change |
| --- | --- | --- |
| http.server.duration (ms) | http.server.request.duration (s) | Rename and unit; new default buckets |
| http.client.duration (ms) | http.client.request.duration (s) | Rename and unit |
| http.server.request.size, http.server.response.size | http.server.request.body.size, http.server.response.body.size | Rename |

The stable duration histograms use seconds with advisory boundaries 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5 and 10. Confirm what your SDK actually applies.

## Database attributes

| Old | New |
| --- | --- |
| db.system | db.system.name |
| db.name | db.namespace |
| db.statement | db.query.text |
| db.operation | db.operation.name |
| db.sql.table | db.collection.name |

Database conventions reached stability later than HTTP and instrumentations differ widely; check the dual-mode value (`database/dup`) exists for your version before relying on it.

## Prometheus spellings

| Telemetry name | Prometheus name |
| --- | --- |
| http.server.duration (ms) | `http_server_duration_milliseconds_bucket`, `_sum`, `_count` |
| http.server.request.duration (s) | `http_server_request_duration_seconds_bucket`, `_sum`, `_count` |
| http.status_code | http_status_code |
| http.response.status_code | http_response_status_code |

Dots become underscores and the unit is appended to the metric name, so a unit change is also a metric name change.

## Checks per language

| Question | Where to look |
| --- | --- |
| Does the SDK still honour OTEL_SEMCONV_STABILITY_OPT_IN | Release notes of the exact SDK or agent version |
| Which instrumentations changed in this release | Per-instrumentation changelog, not the SDK's |
| Does the collector or backend rename attributes on ingest | Its processors and relabel rules |
