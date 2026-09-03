# Experiment catalogue

Read this when choosing and executing the injection: what each experiment costs, the
commands and tooling, the safety controls each one needs, and what to watch while it
runs.

## Contents

- Choosing between them
- Kubernetes-level injections
- Cloud and infrastructure injections
- Network and dependency faults
- Data-layer experiments
- Safety controls that apply to all of them

## Choosing between them

Rank candidates by two numbers: how confident you are in the outcome, and what it costs
if you are wrong. The best experiment is one you are about 70% confident in — high
enough that you are not scheduling a known outage, low enough that the result is worth
someone's morning.

Start with the injection whose failure mode you have already survived in production
without understanding. If the primary database failed over three months ago and nobody
is sure why recovery took eleven minutes, that is the experiment.

## Kubernetes-level injections

Kill a single pod. The cheapest experiment and the least informative; useful only as a
warm-up that proves the observer's tooling works.

```bash
kubectl delete pod -n checkout -l app=checkout --field-selector status.phase=Running \
  --grace-period=30 $(: pick exactly one by name in practice)
```

Remove a whole deployment's capacity, which tests dependents rather than the deployment:

```bash
kubectl -n checkout scale deployment/checkout --replicas=0   # abort: scale back up
kubectl -n checkout rollout status deployment/checkout
```

Drain a node, testing eviction, PodDisruptionBudgets and whether the survivors have real
headroom:

```bash
kubectl cordon node-a1
kubectl drain node-a1 --ignore-daemonsets --delete-emptydir-data --timeout=120s
# abort
kubectl uncordon node-a1
```

A drain that hangs is itself a finding: a PodDisruptionBudget that cannot be satisfied,
or a workload with no way to move. Note the time and let it hang for a bounded period
rather than forcing it immediately, because the same hang will happen during a real node
replacement.

For structured fault injection, LitmusChaos and Chaos Mesh both express experiments as
custom resources with a duration and a selector, which matters because the duration is a
built-in abort — the fault expires on its own if the operator dies. Prefer that shape
over an imperative script that has to survive to clean up after itself.

## Cloud and infrastructure injections

**Availability zone loss.** The highest-value infrastructure experiment, because zone
redundancy is asserted far more often than it is tested. Do not literally break a zone;
simulate it at the edge you control.

```bash
# Remove the zone's subnets from the load balancer target group, or set the
# ASG's desired capacity in that zone to zero, and watch the survivors.
aws elbv2 deregister-targets --target-group-arn "$TG" --targets Id=i-aaa Id=i-bbb
# abort
aws elbv2 register-targets --target-group-arn "$TG" --targets Id=i-aaa Id=i-bbb
```

Watch for the survivors' saturation, not just success rate: passing the experiment while
running at 96% CPU in two zones means the next zone failure at peak is an outage. That
gap is the finding.

**AWS Fault Injection Service** runs the same class of experiment with a stop condition
wired to a CloudWatch alarm, which is the abort mechanism expressed as configuration
rather than as someone watching a graph. If you are on AWS, wiring the stop condition to
the SLO alarm is worth the setup cost on the first exercise.

**Instance termination** at the ASG level tests replacement time and anything holding
local state:

```bash
aws autoscaling terminate-instance-in-auto-scaling-group \
  --instance-id i-aaa --should-decrement-desired-capacity
```

**Certificate expiry** cannot be simulated safely on a production certificate. Do it on a
non-critical internal endpoint with a deliberately short-lived certificate, and measure
two things: how long until something notices, and whether the renewal automation
recovers without a human. The finding is usually that the expiry alert exists but routes
to an unread channel.

**Permission revocation** — remove one IAM permission or one Kubernetes RBAC verb from a
service account and observe how the failure surfaces. The common finding is that it
surfaces as a generic 500 with no attribution, which during a real credential rotation
costs an hour of misdirected debugging. That result usually pairs with a `secret-rotation`
follow-up.

## Network and dependency faults

Slow is harder than dead, and much more common in reality. A dependency returning errors
fast frees the connection; one taking 30 seconds exhausts the pool and takes down callers
that were not even using it.

```bash
# 500ms of added latency on egress, for a bounded period, on one instance.
tc qdisc add dev eth0 root netem delay 500ms 50ms
sleep 300
tc qdisc del dev eth0 root netem            # abort, and the same command cleans up
```

With a service mesh, prefer the mesh's own fault injection: it is scoped by route and
percentage, it is declarative, and removing the configuration is a complete abort.

```yaml
# Istio: 20% of requests to the payments service get a 5s delay.
spec:
  http:
    - fault:
        delay:
          percentage: {value: 20}
          fixedDelay: 5s
      route:
        - destination: {host: payments}
```

What to watch: caller timeout values against the injected delay, retry behaviour (a retry
budget that multiplies load under latency is a cascading failure waiting for peak),
connection pool saturation, and whether the SLI moves at all at 20% degradation. An SLI
that stays flat while a fifth of requests take five seconds is measuring the wrong thing.

**DNS failure** deserves its own experiment because it hits everything at once and its
symptoms are the least legible. Break resolution for one dependency's hostname on one
instance — a hosts-file entry pointing at a black hole is enough — and watch resolver
caching, timeout stacking, and whether any alert names DNS rather than reporting fifteen
unrelated services as unhealthy.

**Disk fill** tests back-pressure and log rotation:

```bash
fallocate -l 20G /var/lib/ballast.bin      # sized to reach ~95%, not 100%
rm /var/lib/ballast.bin                    # abort
```

Leave headroom deliberately. A disk at 100% frequently prevents the very operations you
need to recover, including the shell you were going to abort from.

## Data-layer experiments

**Database failover** is high value and needs the tightest scope. Run it during business
hours, on a service whose SLO has budget, with the abort being "promote back" already
rehearsed. Measure the write-path downtime against the RTO the team claims, and record
the connection-pool recovery separately — most of the observed downtime is usually
clients holding dead connections, not the database.

**Restore from backup** is frequently the single highest-value exercise available, and it
is the one almost nobody runs. Restore last night's backup into a scratch environment and
measure: does it restore at all, how long it takes end to end, and whether the restored
data is consistent and complete. Compare against the stated RPO and RTO. A backup that
has never been restored is a hypothesis, and it is usually wrong in a detail — a missing
role, an encryption key nobody has, a dependent object outside the snapshot.

This experiment has no production blast radius, which makes it the right first game day
for a team that has never run one.

Do not inject data corruption in production. The blast radius is unbounded by
construction and the abort is a restore, which is the thing you were trying to test.
Corruption experiments belong in a scratch environment restored from a real backup.

## Safety controls that apply to all of them

- **A duration cap on the fault itself.** Prefer tools where the fault expires on its own
  (mesh configuration with a duration, a chaos operator's CRD, a `sleep`-then-revert
  script running under a supervisor) over anything that requires a person to remember.
- **The abort, run once, before injection.** Every command listed above has its abort
  next to it for this reason.
- **A watch loop on the steady-state metrics**, on a screen everyone can see, with the
  abort threshold drawn on it.
- **The alert list you expect to fire**, written down beforehand. Any alert not on that
  list firing is an abort condition, because it means the blast radius exceeded the model.
- **One change at a time.** Two simultaneous injections give you an ambiguous result and
  a blast radius nobody modelled.
- **Nothing that cannot be reverted from outside the affected component.** If the abort
  requires the thing you broke, it is not an abort.
