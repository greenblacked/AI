# Red cluster runbook

Use only when `_cluster/health` is red and the allocation explanation shows a primary with
no assignable copy. Nothing here is reversible after the final step.

## Contents

- [Checks before forcing](#checks-before-forcing)
- [Restore from a snapshot](#restore-from-a-snapshot)
- [Forcing a primary](#forcing-a-primary)
- [What to record](#what-to-record)

## Checks before forcing

1. Is every expected node present? `GET _cat/nodes?v`. A node that is restarting returns its
   shard when it joins.
2. Does any node hold a copy? A node holds one when its `store.allocation_id` is set;
   `in_sync` true means current, false means stale. Departed nodes are not listed in the
   explain output, so compare against the expected node list first. A copy that is `in_sync` can be allocated by bringing
   the node back, or by `POST _cluster/reroute?retry_failed=true`.
3. Is a recovery in progress? `GET _cat/recovery?v&active_only=true`.
4. Is there a snapshot with the index? `GET _snapshot/<repo>/_all`, and check that the
   snapshot state is SUCCESS and contains the index.
5. Is the data rebuildable from a source of truth? If so, an empty primary plus a reindex
   may be the better path.

## Restore from a snapshot

Delete or close the red index first, then restore it:

```bash
curl -s -X POST "$ES/_snapshot/<repo>/<snapshot>/_restore" -H 'Content-Type: application/json' \
  -d '{"indices":"orders-2026.10","include_global_state":false}'
```

Writes since the snapshot are lost; say so in the record.

## Forcing a primary

```bash
curl -s -X POST "$ES/_cluster/reroute" -H 'Content-Type: application/json' -d '{
  "commands":[{"allocate_stale_primary":{"index":"orders-2026.10","shard":0,
  "node":"data-3","accept_data_loss":true}}]}'
```

`allocate_empty_primary` takes the same fields and creates a new empty shard. Prefer
`allocate_stale_primary` when any stale copy exists; it keeps whatever that copy held.

## What to record

The index and shard, the nodes checked and their `store` results, snapshot status, the
decision (stale or empty), the named person who accepted the loss and when, and the time
the command ran. Replicas rebuild from the forced primary afterwards.
