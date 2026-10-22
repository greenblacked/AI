# Cross-tenant matrix

Read this when generating the cases from the API description or deciding what a case must assert.

## Generator outline

1. Load the OpenAPI document (or export the router table) and the job and export registry.
2. For every operation, list the places an identifier can appear: path parameters, query parameters, JSON body fields, headers, cookies, and tokens or claims the client can influence.
3. For each operation and each location, emit one case: authenticated as a user of tenant A, with that location filled from B's manifest (the id of the same resource type belonging to B).
4. Add variants for the identifier shapes: numeric ids incremented and decremented, UUIDs from B's manifest, and a nonexistent id for the timing baseline.
5. Emit a list and search case for every collection endpoint, and a bulk case for every batch endpoint (mix A and B ids in one request; the whole request or the B items must be refused).
6. Emit one case for every scheduled job, queue consumer and export: enqueue or trigger it for A with B's identifiers in the payload.

## Assertions for every case

| Assertion | Why |
| --- | --- |
| Status is the contract's denial (403 or 404, one choice, consistently) | A mix of the two reveals existence |
| Body, headers and error text contain no `SENTINEL-B` marker or B identifier | Error bodies echo data |
| Pagination cursors, counts, totals and facets reflect only A | Aggregates leak size |
| Response size and latency match the nonexistent-id baseline within tolerance | Side channel |
| No write occurred: re-read B's manifest rows and compare | A denied-looking call may still have written |
| Audit log records the attempt against A, not B | Attribution |

## Coverage gate sketch

- Enumerate tenant-scoped tables from the schema (a tenant column, or membership in a tenant-owned parent) and tenant-scoped routes from the API description.
- Compare to the set of tables and routes the generated and hand-written cases reference.
- Fail the build when the difference is not empty, naming each missing item, and require an explicit allow-list entry with a reason for anything deliberately global.

## Stores checklist

Database rows, files, search index, cache keys, queue messages, object storage prefixes, exports, webhooks, logs, analytics warehouse, email and notification templates, feature-flag targeting, background-job payloads, and backups. A store missing from the manifest is a store missing from the test.
