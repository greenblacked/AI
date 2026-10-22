# Queries for API server and etcd pressure

Read this at steps 2 to 4. Every query here reads; none changes the cluster. Label names
can drift between releases, so if a query returns nothing, list what the apiserver
actually exposes before concluding the signal is absent:

```bash
kubectl get --raw /metrics | grep -E '^# HELP (apiserver|etcd)_' | cut -d' ' -f3 | sort -u
```

## Contents

- [Request rate, errors and latency](#request-rate-errors-and-latency)
- [API Priority and Fairness](#api-priority-and-fairness)
- [Object counts and watches](#object-counts-and-watches)
- [Ranking clients from the audit log](#ranking-clients-from-the-audit-log)
- [etcd size and health](#etcd-size-and-health)
- [Recovering from a NOSPACE alarm](#recovering-from-a-nospace-alarm)

## Request rate, errors and latency

```promql
# Heaviest verb/resource pairs by rate
topk(15, sum by (verb, resource, scope) (rate(apiserver_request_total[5m])))

# Where the 429s land
sum by (verb, resource) (rate(apiserver_request_total{code="429"}[5m]))

# p99 latency, long-running verbs excluded
histogram_quantile(0.99,
  sum by (le, verb, resource) (
    rate(apiserver_request_duration_seconds_bucket{verb!~"WATCH|CONNECT"}[5m])))

# apiserver-to-etcd latency: separates a busy apiserver from a slow etcd
histogram_quantile(0.99,
  sum by (le, operation, type) (rate(etcd_request_duration_seconds_bucket[5m])))

# Admission webhook latency, which every write pays
histogram_quantile(0.99,
  sum by (le, name, operation) (
    rate(apiserver_admission_webhook_admission_duration_seconds_bucket[5m])))
```

Read `scope="cluster"` `LIST` rows first. A namespaced list of a few hundred objects is
cheap; a cluster-scoped list of every pod or Secret is the call that causes the problem.

## API Priority and Fairness

```promql
# Which flow and level are rejecting, and why (queue-full, time-out, concurrency-limit)
sum by (flow_schema, priority_level, reason) (
  rate(apiserver_flowcontrol_rejected_requests_total[5m]))

# Queue depth per level
sum by (priority_level) (apiserver_flowcontrol_current_inqueue_requests)

# Time spent waiting in queue
histogram_quantile(0.99,
  sum by (le, priority_level) (
    rate(apiserver_flowcontrol_request_wait_duration_seconds_bucket[5m])))
```

Rejections concentrated in one `flow_schema` with a shared level (`service-accounts` is
the usual one) mean a single client is starving its neighbours. Rejections spread across
every level mean the server as a whole is saturated — still look for the client, but also
check apiserver CPU and the etcd latency above.

```bash
kubectl get --raw /debug/api_priority_and_fairness/dump_priority_levels
kubectl get --raw /debug/api_priority_and_fairness/dump_queues
```

## Object counts and watches

```promql
topk(20, max by (resource) (apiserver_storage_objects))

# Open watches per resource
sum by (resource) (apiserver_longrunning_requests{verb="WATCH"})
```

On a release where the gauge is missing, count directly, namespaced resources across all
namespaces:

```bash
for r in pods events replicasets jobs secrets configmaps leases; do
  printf '%s\t' "$r"; kubectl get "$r" -A --no-headers | wc -l
done
```

That loop is itself a set of cluster-wide lists; run it once, not in a watch. Errors are
left visible on purpose: a Forbidden would otherwise print as a count of 0.

## Ranking clients from the audit log

Local file, one JSON event per line:

```bash
jq -r 'select(.stage == "ResponseComplete")
  | [.userAgent, .user.username, .verb, .objectRef.resource] | @tsv' audit.log \
  | sort | uniq -c | sort -rn | head -25

# Cluster-wide lists only
jq -r 'select(.stage == "ResponseComplete" and .verb == "list"
  and (.objectRef.namespace // "") == "")
  | [.userAgent, .user.username, .objectRef.resource] | @tsv' audit.log \
  | sort | uniq -c | sort -rn | head -25
```

EKS, CloudWatch Logs Insights on the cluster's log group:

```text
fields userAgent, user.username, verb, objectRef.resource
| filter @logStream like /kube-apiserver-audit/
| filter stage = "ResponseComplete"
| stats count(*) as requests by userAgent, user.username, verb, objectRef.resource
| sort requests desc
| limit 25
```

AKS: send the `kube-audit` diagnostic category to Log Analytics. `kube-audit-admin` omits
`get` and `list`, so a read storm is invisible there.

GKE: audit entries for the Kubernetes API appear in Cloud Logging under the
`k8s.io` service name. Writes are in Admin Activity logs; reads appear only where Data
Access audit logging is enabled for the Kubernetes Engine API.

Rank twice: by total count, and by cluster-scoped `list` count. The second ranking is the
one that usually names the cause.

## etcd size and health

```promql
etcd_mvcc_db_total_size_in_bytes / etcd_server_quota_backend_bytes
etcd_mvcc_db_total_size_in_use_in_bytes

# Disk latency: etcd's guidance is a WAL fsync p99 under 10 ms
histogram_quantile(0.99, sum by (le, instance) (
  rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le, instance) (
  rate(etcd_disk_backend_commit_duration_seconds_bucket[5m])))
```

Self-managed, with the client certificates for the etcd members:

```bash
etcdctl endpoint status --cluster --write-out=table
etcdctl endpoint health --cluster
etcdctl alarm list
```

Managed clusters do not expose etcd. Recent releases publish the database size through the
apiserver as `apiserver_storage_size_bytes`; older ones used
`apiserver_storage_db_total_size_in_bytes`. Use whichever the `/metrics` listing at the
top of this file shows.

The apiserver compacts etcd history on its own schedule (five minutes by default), so
manual compaction is rarely the fix. A wide gap between total and in-use size is
fragmentation; defragment to return it.

## Recovering from a NOSPACE alarm

While the alarm is active etcd accepts only key reads and deletes. A scale, a patch, a
create and a graceful pod deletion are all writes and fail with `mvcc: database space
exceeded`, so the producer cannot be stopped first. Free space with etcd's documented
sequence, disarm the alarm, then stop the producer straight away, because the space it
frees is refilled quickly while the producer still runs. Have the scale-to-zero command
ready before you disarm.

1. Compact history to the current revision, using the revision from `endpoint status`:

   ```bash
   etcdctl endpoint status --write-out=json
   etcdctl compact "$REV"
   ```

2. Defragment one member at a time, followers before the leader, waiting for each to
   report healthy:

   ```bash
   etcdctl --endpoints="$MEMBER" defrag
   etcdctl endpoint status --cluster --write-out=table
   ```

3. Check in-use size is well below quota, then clear the alarm so writes work again:

   ```bash
   etcdctl alarm disarm
   ```

4. Stop the producer found in step 3 of the skill (scale the controller to zero if
   necessary) before it refills the space, then delete the excess objects it created, in
   batches, watching apiserver latency as you go. If compaction and defragmentation free
   too little to make writes possible, delete objects first: deletes are accepted under
   the alarm, though they free space only after a further compaction and defragmentation.
5. Raise `--quota-backend-bytes` only with a written reason and never past what etcd
   advises; a larger database makes every snapshot, defragmentation and restore slower.

On a managed cluster you cannot run these; open a provider support case with the evidence
from step 3 while doing the producer and delete steps yourself.
