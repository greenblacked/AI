# Unassigned reasons and deciders

## Contents

- [Unassigned reasons](#unassigned-reasons)
- [Deciders](#deciders)
- [Settings snippets](#settings-snippets)

## Unassigned reasons

| `unassigned.reason` | Meaning | First thing to check |
| --- | --- | --- |
| `NODE_LEFT` | The node holding the shard left the cluster | `_cat/nodes`, node logs, the delayed timeout |
| `INDEX_CREATED` | New index not yet allocated | Filters, disk, shard limit |
| `ALLOCATION_FAILED` | An attempt failed | `unassigned.details` and the node log; then retry |
| `CLUSTER_RECOVERED` | Full cluster restart recovery | Wait; check `cluster.routing.allocation.enable` |
| `REPLICA_ADDED` | Replica count was raised | Enough nodes for the new count |
| `REROUTE_CANCELLED` | An earlier reroute was cancelled | Retry once |

## Deciders

| Decider in explain | Meaning | Fix |
| --- | --- | --- |
| `disk_threshold` | Node over a watermark | Free space or add nodes; see watermarks |
| `filter` | `require`, `include` or `exclude` rule excludes the node | Remove the stale rule |
| `awareness` | Copy would unbalance the attribute | Add a node in the missing zone, or relax awareness |
| `same_shard` | A node already holds a copy of this shard | Need more nodes than copies |
| `max_retry` | Retries exhausted | Fix the cause, then `retry_failed=true` |
| `shards_limit` | `cluster.max_shards_per_node` or index limit reached | Reduce shard count |
| `enable` | Allocation switched off | Set `cluster.routing.allocation.enable` to `all` |
| `data_tier` | Elasticsearch tier preference with no matching node | Add a node with the role, or fix `_tier_preference` |
| `node_shutdown` or `node_replacement` | A planned node shutdown is registered | Complete or remove the shutdown record |

## Settings snippets

```bash
# Read the settings that matter
curl -s "$ES/_cluster/settings?include_defaults=true&flat_settings=true&pretty" \
  | jq 'to_entries[] | select(.key | test("watermark|allocation|max_shards"))'

# Clear a leftover cluster-level exclude
curl -s -X PUT "$ES/_cluster/settings" -H 'Content-Type: application/json' \
  -d '{"persistent":{"cluster.routing.allocation.exclude._name":null}}'

# Clear a leftover index-level filter
curl -s -X PUT "$ES/orders-2026.10/_settings" -H 'Content-Type: application/json' \
  -d '{"index.routing.allocation.require._name":null}'

# Release a read-only block once space is freed
curl -s -X PUT "$ES/_all/_settings" -H 'Content-Type: application/json' \
  -d '{"index.blocks.read_only_allow_delete":null}'

# Retry shards that gave up
curl -s -X POST "$ES/_cluster/reroute?retry_failed=true"
```

Watermark defaults are 85, 90 and 95 percent for low, high and flood stage. If a cluster
has custom values, report them rather than the defaults. Percentages can be replaced by
absolute free-space values; the two forms cannot be mixed within one cluster's settings.
