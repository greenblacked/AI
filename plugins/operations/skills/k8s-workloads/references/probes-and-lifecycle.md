# Probes and the pod lifecycle

Read this at step 4 when setting probes, and at step 8 when the workload has to shut down without dropping requests.

## Contents

- [The fields and their defaults](#the-fields-and-their-defaults)
- [What each probe is for](#what-each-probe-is-for)
- [Sizing a startup probe](#sizing-a-startup-probe)
- [Readiness under load, and the fleet oscillation it can cause](#readiness-under-load-and-the-fleet-oscillation-it-can-cause)
- [The termination sequence in full](#the-termination-sequence-in-full)
- [Measuring the preStop sleep](#measuring-the-prestop-sleep)
- [Sidecars and shutdown order](#sidecars-and-shutdown-order)

## The fields and their defaults

Every probe type takes the same fields.

| Field | Default | Notes |
| --- | --- | --- |
| `initialDelaySeconds` | 0 | A fixed delay paid on every container start, including every restart. A startup probe is almost always the better instrument. |
| `periodSeconds` | 10 | Minimum 1. |
| `timeoutSeconds` | 1 | Minimum 1. The default that catches people out — see below. |
| `successThreshold` | 1 | Must be 1 for liveness and startup probes. |
| `failureThreshold` | 3 | Minimum 1. Three consecutive failures at the default period is 30 seconds before action. |
| `terminationGracePeriodSeconds` | The pod's value | Probe-level override, used when a probe-triggered kill should be faster than an ordinary shutdown. |

`timeoutSeconds: 1` is the sharp edge. A health handler that shares a thread pool or an event loop with request handling will exceed one second under load — precisely when a restart does the most damage, because the fleet is already short of capacity. Either give the handler an isolated path, or raise the timeout to something the handler can meet at peak and lengthen `failureThreshold` to compensate.

Note also that a `grpc` probe respects `timeoutSeconds`, so a gRPC health service that is slow under load fails the same way.

## What each probe is for

Three probes, three different questions, and confusing any two of them produces a distinct outage.

**Readiness — can this pod serve a request right now?** Failure removes the pod's IP from the EndpointSlices of every Service whose selector matches it. That is a fleet-wide instrument dressed as a per-pod one: if every replica's readiness depends on the same downstream, its failure empties the Service entirely, turning a partial failure into a total one. Readiness runs for the whole container lifecycle, not only at start.

**Liveness — is this process wedged in a way only a restart fixes?** Failure kills the container, and the pod's restart policy recreates it. The bar for setting one is higher than most manifests assume: if the failure mode is "the process exits", the restart policy already covers it without a probe. Set a liveness probe when you can name the wedge — a deadlocked event loop, a connection pool the process will not rebuild, a stuck consumer that does not crash. The endpoint must not touch a network dependency, because a liveness probe that fails when a downstream fails converts someone else's outage into a restart storm that destroys warm caches and connection pools across every replica at once.

**Startup — has this container finished booting?** Liveness and readiness are held off until a startup probe first succeeds, which is what lets a slow starter coexist with a tight liveness probe. Without one, a container that takes four minutes to warm a cache is killed by liveness on every attempt, producing a CrashLoop that looks like an application bug and is a manifest bug.

## Sizing a startup probe

The budget is `failureThreshold * periodSeconds`. The upstream worked example is:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: liveness-port
  failureThreshold: 1
  periodSeconds: 10

startupProbe:
  httpGet:
    path: /healthz
    port: liveness-port
  failureThreshold: 30
  periodSeconds: 10
```

Thirty failures at ten seconds gives the application five minutes to start. If the startup probe never succeeds, the container is killed at 300 seconds and the restart policy applies.

Size the budget from the slowest real start, not the typical one: the first start after a cache flush, the start during a dependency's own slow period, the start of the largest tenant's shard. Then note the cost of over-sizing — a container genuinely wedged at boot takes the whole budget before anything notices — and pick a number you can defend at both ends.

The pattern that makes liveness tight and safe is the one above: a long startup budget, and then `failureThreshold: 1` on liveness so a genuine wedge is caught in one period.

## Readiness under load, and the fleet oscillation it can cause

Readiness that fails when a local queue is deep is a load-shedding mechanism, and it behaves like one: shedding from a busy pod moves its traffic to peers that are also busy, which can take them out too, and the Service empties from the tail inwards. If readiness is used this way, something has to hold a floor — a threshold well above the level at which peers can absorb the traffic, or an explicit minimum ready count enforced elsewhere.

The safer default is that readiness reflects only whether this pod can serve at all, and overload is handled by a queue limit and an explicit rejection response, which remains a response.

## The termination sequence in full

1. The pod is marked Terminating in the API and the grace period clock starts. `kubectl describe` shows Terminating from here on.
2. The kubelet runs the `preStop` hook, if there is one and `terminationGracePeriodSeconds` is not 0. The hook runs inside the grace period. If it is still running when the period expires, the kubelet grants one 2-second extension and then proceeds.
3. The container runtime sends SIGTERM to PID 1 of each container. Many runtimes send the image's `STOPSIGNAL` instead if it differs. Without sidecar containers, the containers receive the signal at arbitrary times and in arbitrary order.
4. Concurrently with steps 2 and 3, the control plane evaluates removing the pod from the EndpointSlices of matching Services. Endpoints for terminating pods are not removed instantly; they are marked with `ready: false` and a `serving` condition, and the removal then has to propagate.
5. When the grace period expires, any container still running is sent SIGKILL.
6. The kubelet finishes and the pod object is removed from the API server.

The design consequence is that a workload cannot assume traffic has stopped when SIGTERM arrives. The signal is the start of the drain, not the end of it.

Setting the grace period to 0 forcibly deletes the pod object immediately, skipping `preStop` and any drain at all. It is a way to unstick a pod object, not a way to shut a workload down.

## Measuring the preStop sleep

There is no universal value. The delay you need is the time for endpoint removal to reach every component that forwards traffic, which depends on the dataplane:

- iptables or IPVS kube-proxy, refreshing on its own schedule.
- An eBPF CNI, with its own propagation path.
- An ingress controller, which reads endpoints and reloads or reconfigures.
- A cloud load balancer pointed at node ports or pod IPs, with a health-check interval and a deregistration delay of its own — often the largest term by far.

Measure it rather than adopting somebody's number:

1. Put steady, measurable load through the Service from outside the cluster, at the layer where a user would see the error.
2. Set a `preStop` sleep of 0 and roll the deployment. Count connection resets and 5xx at the edge, attributed to the rollout window.
3. Raise the sleep and roll again. Repeat until the error count reaches zero and stays there across two consecutive rollouts.
4. Record the value, the dataplane it was measured against, and the date — it changes when the ingress or the load balancer changes.

Then check the grace period covers everything that has to happen inside it:

```text
terminationGracePeriodSeconds  >  preStop sleep
                                + longest in-flight request
                                + connection drain and cleanup
```

The grace period is a shared budget, not an addition. If the sum exceeds it, SIGKILL lands mid-request and the measurement above will show it.

## Sidecars and shutdown order

A proxy, log shipper or agent declared as an ordinary container receives SIGTERM at an arbitrary point in step 3, so it can exit while the application still has requests in flight, and those requests fail at the last possible moment.

Native sidecar containers — init containers carrying `restartPolicy: Always`, enabled by default since Kubernetes v1.29 — fix the ordering: the kubelet delays SIGTERM to them until the last main container has fully terminated, and then stops them in reverse order of definition. If a workload has a proxy in the request path, declaring it this way removes a whole class of end-of-rollout errors.

Where the ordering still has to be arranged by hand, a `preStop` hook on the sidecar is the documented way to synchronise it — but the sidecar container form is the better answer wherever the cluster version allows it.
