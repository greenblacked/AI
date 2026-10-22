# Reindex runbook

Contents: setup, dual write, backfill, verify, swap, bake, rollback.

## Setup

Reads and writes use two aliases, for example `items_read` and `items_write`, pointing at `items_v1`. Create `items_v2` with the new settings and mappings. Set `refresh_interval` to `-1` and replicas to 0 on the new index for the bulk load, and restore both before the swap.

## Dual write

Change the consumer to write each event to both `items_v1` and `items_v2`, with the same external version. Failures writing to v2 must be retried, not dropped; the backfill below does not cover events that arrive during it unless the dual write is complete.

## Backfill

Either call `POST _reindex` from `items_v1` to `items_v2` with `version_type: external` in `dest` and `"conflicts": "proceed"` in the body, so documents written by the dual path are not overwritten by older copies and the first version conflict does not abort the run (the conflicts counted are expected skips of newer documents), or page the database in id order and bulk-index with the row version. The database route also fixes drift that already existed in v1.

## Verify

- Counts: `GET items_v2/_count` against `SELECT count(*)` for the same filter.
- Checksums: for each id range of fixed size, hash the concatenated id and version in the database and in the index (use a scripted aggregation or export), and list ranges that differ.
- Spot queries: run a fixed set of real queries on both and compare top results, accounting for the intended mapping change.

## Swap

Send one request to `POST _aliases` with `actions` that remove `items_v1` and add `items_v2` for both aliases. The actions apply atomically. Restore refresh interval and replicas before this step.

## Bake and rollback

Keep `items_v1` and keep dual writing to it for the bake period. To roll back, swap the aliases in one request the other way. After the bake, stop writing to v1, then delete it.
