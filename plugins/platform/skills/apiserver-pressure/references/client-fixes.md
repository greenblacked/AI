# Client fixes and API Priority and Fairness

Read this at steps 5 and 6, once the audit log has named the client. Most fixes here are
changes to someone else's controller or agent; where you do not own it, the evidence from
step 3 is what goes into the upstream issue or vendor case.

## Contents

- [Resync and relist are different costs](#resync-and-relist-are-different-costs)
- [Symptom to fix](#symptom-to-fix)
- [Unbounded object growth](#unbounded-object-growth)
- [Isolating a client with API Priority and Fairness](#isolating-a-client-with-api-priority-and-fairness)

## Resync and relist are different costs

The two are often confused, and the fix differs.

- **Resync** is an informer replaying objects from its own local cache to the handlers on
  a timer. It makes no request to the API server. It becomes expensive only when the
  reconcile it triggers makes requests — a `GET` per object, or a status write per object.
  controller-runtime's default sync period is long (hours); an operator that sets it to
  seconds and writes on every pass turns a cheap timer into a write storm.
- **Relist** is a full `LIST` from the API server. An informer relists on start-up and
  whenever its watch cannot resume — after a `410 Gone` because the resource version it
  held has been compacted away, or after the apiserver restarts. Watch bookmarks keep the
  held resource version fresh, so a reconnect resumes instead of relisting. client-go's
  reflector requests bookmarks already; a hand-written watch loop often does not.

A relist storm after every apiserver restart is therefore a bookmark and back-off problem,
not a resync problem.

## Symptom to fix

| Audit-log pattern | Cause | Fix |
| --- | --- | --- |
| One `list pods` per node at a fixed interval, cluster-scoped | A DaemonSet agent that wants its own node's pods | Informer with `fieldSelector=spec.nodeName=$NODE`; the selector is applied server-side |
| Cluster-scoped `list` of Secrets or ConfigMaps from one identity | A controller watching everything to find a few | Label selector, namespace-scoped informers, or a metadata-only informer when the payload is not needed |
| `list` at a fixed interval with no `watch` from the same agent | Polling | Informer plus lister; poll only what has no watch |
| Burst of `list` from every controller seconds after an apiserver restart | Relist without bookmarks or back-off | Current client library, bookmarks on, jittered back-off on reconnect |
| `get` on the same object many times per minute | Uncached client in the reconcile loop | Read from the informer cache; controller-runtime's default client already does |
| `update` or `patch` on `status` every reconcile | Unconditional status write | Compare desired with current and write only on change |
| Many `list` calls with `limit` and `continue` | Paginated consistent lists | Recent releases can serve consistent lists from the watch cache; older ones send them to etcd. Prefer an informer to repeated paginated lists |
| `watch` count per resource climbing without bound | A client leaking watches, one per reconcile | Fix the leak; check `apiserver_longrunning_requests` by resource after the fix |
| High `create` rate on `events` | A controller emitting an event per loop | Emit on state change only; events live for the apiserver's event TTL (one hour by default) and every one is an etcd write |

## Unbounded object growth

| Resource | Usual producer | Retention control |
| --- | --- | --- |
| `jobs`, `pods` | CronJobs and batch systems | `ttlSecondsAfterFinished`; CronJob `successfulJobsHistoryLimit` and `failedJobsHistoryLimit` |
| `replicasets` | Frequent Deployment rollouts | `revisionHistoryLimit` (default 10); lower it on Deployments that roll many times a day |
| `secrets` named `sh.helm.release.v1.*` | Helm upgrades | `helm upgrade --history-max` |
| Operator CRDs (certificate requests, workflow runs, backups) | The operator itself | The operator's own retention or garbage-collection setting |
| `leases` | Leader election, node heartbeats | Usually healthy; investigate only a count far above controllers plus nodes |

Clean up after the producer is fixed, in batches, while watching apiserver latency.
Deleting tens of thousands of objects is itself a write storm.

## Isolating a client with API Priority and Fairness

Use this only after the client is fixed or while a vendor fix is pending. It confines the
client's load to its own share; it does not reduce that load.

First see what the client matches today. `kubectl get flowschemas` prints each schema's
`MATCHINGPRECEDENCE` (lower wins) and its priority level. Pick a precedence lower than
the schema the client currently lands in and higher than the system schemas, so the new
schema catches only this client.

```yaml
apiVersion: flowcontrol.apiserver.k8s.io/v1
kind: PriorityLevelConfiguration
metadata:
  name: noisy-operator
spec:
  type: Limited
  limited:
    nominalConcurrencyShares: 10
    lendablePercent: 0
    limitResponse:
      type: Queue
      queuing:
        queues: 16
        handSize: 4
        queueLengthLimit: 50
---
apiVersion: flowcontrol.apiserver.k8s.io/v1
kind: FlowSchema
metadata:
  name: noisy-operator
spec:
  priorityLevelConfiguration:
    name: noisy-operator
  matchingPrecedence: 1000
  distinguisherMethod:
    type: ByUser
  rules:
    - subjects:
        - kind: ServiceAccount
          serviceAccount:
            name: the-operator
            namespace: operator-system
      resourceRules:
        - verbs: ["*"]
          apiGroups: ["*"]
          resources: ["*"]
          clusterScope: true
          namespaces: ["*"]
```

The `v1` API is served from Kubernetes 1.29; on older clusters use the beta version your
cluster lists under `kubectl api-versions | grep flowcontrol`.

After applying, confirm the client's requests carry the new schema's UID in the
`X-Kubernetes-PF-FlowSchema-UID` response header, or appear under the new level in
`dump_priority_levels`, and that rejections in its old level have stopped.

Do not:

- match a client into `exempt` or a system level — it bypasses the protection entirely;
- raise shares on a shared level such as `workload-low` to make one client's 429s stop —
  every client on that level gets the extra seats, including the one causing the load;
- isolate a client that retries without back-off; it will spend its share on retries.
  Fix its retry behaviour first.
