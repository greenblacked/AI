# Kubernetes Symptom Decode Table

Read this once the pod state is known and a rollback has either happened or been ruled
out. Each section is: the symptom as it appears in `kubectl get pods`, the one piece of
evidence that decides between causes, then causes ordered by prior probability — check
them top-down and stop at the first that matches the evidence.

## Contents

- [CrashLoopBackOff](#crashloopbackoff)
- [OOMKilled — exit 137](#oomkilled--exit-137)
- [ImagePullBackOff / ErrImagePull](#imagepullbackoff--errimagepull)
- [Pending / unschedulable](#pending--unschedulable)
- [Running but not Ready](#running-but-not-ready)
- [Terminating forever](#terminating-forever)
- [DNS resolution failures](#dns-resolution-failures)
- [RBAC 403 / Forbidden](#rbac-403--forbidden)
- [Service with no endpoints](#service-with-no-endpoints)
- [Exit code reference](#exit-code-reference)

## CrashLoopBackOff

The container starts, exits, and the kubelet is waiting before trying again.
`CrashLoopBackOff` is not a failure mode — it is the *waiting*. The failure already
happened and its evidence is in the previous container.

**Decisive evidence:** `lastState.terminated.exitCode` plus `kubectl logs --previous`.
The current log is empty or truncated because the container is not running; without
`--previous` you are reading nothing and concluding nothing.

```bash
kubectl logs "$POD" -n "$NS" -c "$CONTAINER" --previous --tail=200
kubectl get pod "$POD" -n "$NS" -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}{.lastState.terminated.exitCode}{"\t"}{.lastState.terminated.reason}{"\n"}{end}'
```

| Exit code | Cause, most likely first | Confirm with |
| --- | --- | --- |
| `1` | Application error at startup: missing or malformed env var, absent Secret or ConfigMap key, unparseable config, failed migration | The `--previous` log's last 20 lines; `kubectl get pod -o yaml` for `envFrom` referencing a name that does not exist |
| `137` | `OOMKilled`, or SIGKILL after `terminationGracePeriodSeconds` elapsed during a shutdown that never finished | `lastState.terminated.reason` — it says `OOMKilled` explicitly when it was memory |
| `143` | SIGTERM. Something asked it to stop: a failing liveness probe, an eviction, a rollout | `kubectl events --for pod/$POD --types=Warning` for `Unhealthy` / `Killing` |
| `126` | Entrypoint found but not executable — missing `+x` bit on a script copied into the image | `kubectl debug` a copy with `--set-image` and `ls -l` the path |
| `127` | Entrypoint not found. Overwhelmingly a distroless or scratch image with shell-form `CMD`, or a binary built for a path that does not exist in the final stage | Same; there is no `/bin/sh` in the image to interpret the command |
| `0` repeatedly | The process is doing its job and exiting; `restartPolicy: Always` on something that should be a Job | The log looks like a clean run |

A dependency unreachable at startup — database, config service, message broker — presents
as exit 1 with a connection error, and is the most common cause of a *whole namespace*
crash-looping at once. Fix the dependency, not the pods.

**The backoff is exponential and capped.** Delays run 10s, 20s, 40s, 80s, 160s and cap at
300s (5 minutes); the counter resets after the container has run 10 minutes without
crashing. A pod that appears frozen in `CrashLoopBackOff` with no new log lines may simply
be inside a 5-minute wait. Read `lastState.terminated.finishedAt` before concluding it is
stuck, and do not delete it to "kick" it — that destroys the previous-container log.

## OOMKilled — exit 137

**Decisive evidence:** `lastState.terminated.reason: OOMKilled`, and `kubectl top pod`
readings taken before the kill if you have them. The container's own memory limit is what
matters, not the node's free memory.

```bash
kubectl get pod "$POD" -n "$NS" -o jsonpath='{range .spec.containers[*]}{.name}{"\t"}{.resources.limits.memory}{"\t"}{.resources.requests.memory}{"\n"}{end}'
kubectl top pod "$POD" -n "$NS" --containers
```

Causes, most likely first:

1. **The limit is below the real working set.** Someone copied a limit from another
   service, or set it from a load test that never exercised the cache.
2. **A runtime heap that is not limit-aware.** A JVM without `-XX:MaxRAMPercentage`
   sizes its heap from the *node's* memory, not the cgroup's, and will happily target
   more than the limit. Node needs `--max-old-space-size` set below the limit. Both
   produce a container killed while the runtime believes it has headroom.
3. **A genuine leak.** Memory climbs monotonically across the pod's lifetime and the
   time-to-OOM is roughly constant across restarts.
4. **A sidecar sharing the limit.** Log shippers and service-mesh proxies count against
   the pod's total; the application container gets killed for the sidecar's growth.

Raising the limit is a mitigation, not a fix. It buys time proportional to the headroom
added and nothing else, and against a leak it buys almost nothing. Record the raise in the
incident document as a follow-up item so it does not become the permanent answer.

## ImagePullBackOff / ErrImagePull

**Decisive evidence:** the event message, which names the failure precisely. Read it
before theorising.

```bash
kubectl describe pod "$POD" -n "$NS" | sed -n '/Events:/,$p'
```

| Message contains | Cause |
| --- | --- |
| `manifest unknown`, `not found` | Tag typo, or a tag deleted or overwritten upstream. Check the digest the running pods use versus the one requested |
| `unauthorized`, `authentication required` | Missing `imagePullSecrets` on the pod or ServiceAccount; or the Secret exists but in a different namespace — image pull Secrets are namespaced and do not travel with a copied manifest |
| `denied`, `403` on a previously working image | Registry credentials expired or were rotated; ECR/ACR/GCR tokens have short lives and a stale Secret pulls fine until the cached token dies |
| `toomanyrequests` | Docker Hub anonymous rate limit. Affects whole nodes at once and looks like a cluster problem |
| `no matching manifest for linux/arm64` | Architecture mismatch — a single-arch image scheduled onto an arm64 node pool, common after adding Graviton or Ampere nodes to an existing cluster |
| `ErrImageNeverPull` | `imagePullPolicy: Never` with the image absent from that node |

The pull happens on the node, so a failure on one node and success on another points at
node-local credentials or architecture, not at the manifest.

## Pending / unschedulable

**Decisive evidence:** the `FailedScheduling` event message is literally the answer. It
enumerates, per node, why that node was rejected. Read it verbatim.

```bash
kubectl get events -n "$NS" --field-selector reason=FailedScheduling --sort-by=.metadata.creationTimestamp
kubectl describe pod "$POD" -n "$NS" | sed -n '/Events:/,$p'
```

| Message fragment | Cause and mitigation |
| --- | --- |
| `Insufficient cpu` / `Insufficient memory` | No node has room for the *requests*. Either the cluster is full or one request is absurd. Check whether the autoscaler is scaling — and whether it is stuck |
| `had untolerated taint` | Taint without a matching toleration. Frequently a new node pool, or a node cordoned by an operator |
| `node(s) didn't match Pod's node affinity/selector` | `nodeSelector` or `requiredDuringScheduling` affinity matching no current node — a label removed or a zone drained |
| `pod has unbound immediate PersistentVolumeClaims` | The PVC is Pending. Check the StorageClass exists and its provisioner is healthy |
| `node(s) had volume node affinity conflict` | The PV lives in one zone, the schedulable capacity is in another. Zonal disks pin a pod to a zone permanently |
| `didn't match pod topology spread constraints` | `whenUnsatisfiable: DoNotSchedule` with skew already at the limit; loosening to `ScheduleAnyway` is a valid mitigation |
| `exceeded quota` (on the ReplicaSet, not the pod) | ResourceQuota. The pod never gets created at all — look at the ReplicaSet's events, not the pod's, because there is no pod |
| No events at all, pod just sits | No scheduler is running, or the pod has a `schedulerName` naming a scheduler that does not exist |

When the autoscaler is the suspect, its own events say why it declined:
`kubectl -n kube-system logs deploy/cluster-autoscaler --tail=100` shows
`no.scale.up.in.zone`, `max node group size reached`, or a quota error from the cloud API.

## Running but not Ready

The container is up, the readiness probe is failing, so the Service removed it from the
endpoints. Traffic is not reaching it and it is not restarting.

**Decisive evidence:** the `Unhealthy` warning event, which quotes the probe's HTTP status
or connection error, together with the probe spec.

```bash
kubectl events --for "pod/$POD" -n "$NS" --types=Warning
kubectl get pod "$POD" -n "$NS" -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{.readinessProbe}{"\n"}{.livenessProbe}{"\n"}{end}'
```

Causes, most likely first:

1. **Wrong port or path.** The probe targets 8080 and the app listens on 3000, or the path
   moved in a framework upgrade. The event shows `connection refused` or `404`.
2. **`initialDelaySeconds` too short.** A JVM or a large Python import graph takes 40
   seconds to serve, the probe starts at 10, and the liveness probe kills it before it
   ever finishes starting. Use a `startupProbe` for this instead of inflating
   `initialDelaySeconds` on the liveness probe.
3. **Bound to `127.0.0.1` rather than `0.0.0.0`.** The app works when you exec in and curl
   localhost, and fails from the kubelet. This is the one that wastes the most time,
   because every in-container test passes.
4. **`timeoutSeconds` under the real p99.** Default is 1 second. A health endpoint that
   checks a database and normally answers in 800ms will flap under load, taking pods out
   of rotation exactly when you need them, which increases load on the rest.
5. **The dependency really is down** and the readiness probe is correctly reporting it.

Never point a **liveness** probe at a dependency. Readiness may reflect a dependency —
that just removes the pod from load balancing. Liveness restarts the container, so a
downstream outage becomes a cluster-wide restart storm that destroys your warm caches and
your connection pools, and the pods cannot recover even after the dependency does. If you
find this configuration during an incident, deleting the liveness probe is a legitimate
mitigation.

## Terminating forever

**Decisive evidence:** `deletionTimestamp` is set and `metadata.finalizers` is non-empty,
or the node hosting the pod is `NotReady`.

```bash
kubectl get pod "$POD" -n "$NS" -o jsonpath='{.metadata.deletionTimestamp}{"\n"}{.metadata.finalizers}{"\n"}'
kubectl get node "$(kubectl get pod "$POD" -n "$NS" -o jsonpath='{.spec.nodeName}')"
```

1. **A finalizer whose controller is gone.** An operator was uninstalled while its CRs
   still existed; nothing will ever remove the finalizer. Patching it off is safe *once
   you have confirmed the controller is genuinely gone*, not merely restarting.
2. **A stuck volume detach.** The cloud provider will not detach the disk because it
   believes another node holds it. Events on the pod and the `VolumeAttachment` object say
   so. This resolves on its own more often than people wait for.
3. **`preStop` hook or shutdown exceeding the grace period.** The pod terminates after
   `terminationGracePeriodSeconds` regardless — if it has been longer than that, this is
   not the cause.
4. **The node is unreachable.** The control plane cannot confirm the pod is gone, so it
   will not remove it. Pods on a `NotReady` node stay `Terminating` by design.

Force delete (`--grace-period=0 --force`) only removes the API object; it does not stop the
process. If the container is still running and holding a lock, a volume, or a StatefulSet
identity, forcing the delete lets a replacement start alongside it — split brain, and for a
StatefulSet with a consensus protocol that means data loss. Confirm the process is really
gone, or the node really is dead, first.

## DNS resolution failures

**Decisive evidence:** a test lookup from a pod in the affected namespace, plus CoreDNS's
own state.

```bash
kubectl run -it --rm dnstest --restart=Never --image=registry.k8s.io/e2e-test-images/agnhost:2.39 -- nslookup kubernetes.default
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl -n kube-system logs -l k8s-app=kube-dns --tail=50
```

1. **CoreDNS pods Pending or OOMKilled.** Two replicas serve the whole cluster by default;
   losing them presents as every service failing simultaneously with connection errors
   rather than as a DNS problem. Check this first because it explains everything at once.
2. **`ndots: 5`.** The default `/etc/resolv.conf` search path means `api.example.com` is
   tried as `api.example.com.<ns>.svc.cluster.local`, then three more suffixes, before the
   real name — five round trips per external lookup. Under load this saturates CoreDNS and
   shows up as latency, not as failure. Mitigate with a trailing dot on external names or
   `dnsConfig: {options: [{name: ndots, value: "1"}]}` on the pod.
3. **A NetworkPolicy blocking egress to kube-dns.** A default-deny egress policy without a
   UDP/TCP 53 allow rule to the kube-system namespace breaks all name resolution in that
   namespace. It appears the moment the policy is applied, to every pod at once.
4. **Node-local DNS cache unhealthy**, where deployed — the pod talks to a local address
   that is no longer answering.

## RBAC 403 / Forbidden

**Decisive evidence:** the error message names the subject, verb, resource and namespace.
Then ask the API directly rather than reading YAML.

```bash
kubectl auth can-i --list --as="system:serviceaccount:$NS:$SA" -n "$NS"
kubectl auth can-i get secrets --as="system:serviceaccount:$NS:$SA" -n "$NS"
```

1. **A Role where a ClusterRole was needed.** A `Role` grants nothing outside its own
   namespace and nothing at all on cluster-scoped resources — nodes, PVs, CRDs,
   namespaces. Binding a Role and expecting cluster-wide access is the single most common
   RBAC mistake.
2. **A RoleBinding referencing a ClusterRole**, which correctly narrows it to one
   namespace — right when you wanted cluster-wide, so the permission silently applies in
   one place only.
3. **Wrong ServiceAccount.** The pod runs as `default` because `serviceAccountName` was
   omitted or misspelled; the carefully-written binding applies to an account nothing uses.
4. **Missing subresource.** `pods` and `pods/log`, `pods/exec`, `deployments` and
   `deployments/scale` are separate grants.
5. **Wrong `apiGroup`** in the rule — `""` for core resources, the group name otherwise.

## Service with no endpoints

Traffic gets connection refused or times out, and the Service has no backends.

**Decisive evidence:** EndpointSlices. `kubectl get endpoints` still works but
EndpointSlices are the source of truth and show readiness per address.

```bash
kubectl get endpointslices -n "$NS" -l "kubernetes.io/service-name=$SVC" -o yaml
kubectl get pods -n "$NS" -l "$(kubectl get svc "$SVC" -n "$NS" -o jsonpath='{.spec.selector}' | tr -d '{}"' | tr ',' ',')"
```

1. **Selector mismatch.** The Service selects `app=web` and the Deployment labels pods
   `app.kubernetes.io/name=web`. Common after a Helm chart upgrade changes label
   conventions. No endpoints at all, ever.
2. **`targetPort` name mismatch.** The Service names a port that the container spec does
   not define. Endpoints appear but traffic goes nowhere.
3. **All backends failing readiness.** Endpoints exist with `ready: false`. This is not a
   Service problem — go to *Running but not Ready* above; the Service is behaving exactly
   as designed and the fault is upstream.
4. **A headless Service** (`clusterIP: None`) being used as though it load-balanced.
5. **Pods in a different namespace.** Services do not select across namespaces.

## Exit code reference

| Code | Meaning |
| --- | --- |
| 0 | Clean exit — wrong for a long-running server under `restartPolicy: Always` |
| 1 | Generic application error |
| 2 | Shell misuse, or an application's own usage error |
| 126 | Command found but not executable |
| 127 | Command not found |
| 128+n | Killed by signal n |
| 137 | 128+9, SIGKILL — OOMKilled, or SIGKILL after the grace period |
| 139 | 128+11, SIGSEGV — segfault, often a native library or architecture mismatch |
| 143 | 128+15, SIGTERM — asked to stop by the kubelet |
