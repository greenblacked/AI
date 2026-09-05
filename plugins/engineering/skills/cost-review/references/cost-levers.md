# Cost levers

Read this when sizing a specific finding: the rightsizing procedure and the limits that
actually bound an instance, the arithmetic behind commitment and spot decisions, the
data-transfer decision table by path, storage class and retention policy, and the step
that converts a projection into a saving somebody can count.

## Contents

- Rightsizing
- Purchase model: commitments and spot
- Data transfer
- Storage class and retention
- Idle and orphaned resources
- Architectural cost
- Verification

## Rightsizing

The procedure, in order. Skipping step 1 is what produces the page.

1. **Collect a window that contains a real peak.** Two weeks minimum; a month if the
   business has a monthly cycle (close, billing run, payroll, marketing send). A window
   that misses the peak produces a size that misses the peak.
2. **Take percentiles, not averages.** p95 for a service with headroom elsewhere in the
   stack, p99 for anything user-facing without a queue in front of it.
3. **Check every dimension, not just CPU.** Memory is the one that kills: a JVM or a
   Node process sized to a heap does not degrade gracefully when the instance shrinks,
   it gets OOM-killed. Network bandwidth, EBS throughput and IOPS, burst credits and
   connection limits all scale with instance size on most families.
4. **State the target utilisation and the headroom it buys.** "p99 CPU at 60% after the
   change, absorbing a 1.6x traffic increase or the loss of one of three instances."
   A number with no headroom statement is not a recommendation.
5. **Change one dimension at a time.** Family change and size change together makes an
   unexpected regression impossible to attribute.
6. **Verify against the same percentile after a full cycle**, before counting the money.

Two facts worth carrying:

- CloudWatch does not report memory utilisation for EC2 without the CloudWatch agent. A
  rightsizing recommendation from CPU alone, on a memory-bound workload, is a guess.
- A newer instance generation is frequently both cheaper and faster than a smaller
  instance of the old one. Check the generation change before the size change; it is the
  rare cost lever with no reliability cost.

### Kubernetes

Rightsize **requests** from usage percentiles, since requests set both scheduling and
cost. Vertical Pod Autoscaler in recommendation mode produces the percentiles without
acting on them, which is the mode to use while you are still deciding.

Limits are a separate decision with a different failure mode. A CPU limit throttles at
the limit even when the node is idle, so a limit set equal to the request converts spare
capacity into latency and saves nothing. Memory limits are worth setting, because the
alternative to an OOM-killed pod is a node that goes unready and takes its neighbours
with it.

## Purchase model: commitments and spot

### Coverage arithmetic

Commit to the trough of the usage curve, which is the level that runs on a public
holiday at 04:00. Above the trough, usage is a distribution and a commitment is a bet.

```text
break_even_hours = commitment_total / on_demand_hourly_rate
break_even_utilisation = break_even_hours / hours_in_term
```

For a one-year commitment at a 30% discount, break-even utilisation is roughly 70% of
the term. Running the covered capacity less than that loses money against on-demand, and
"we will grow into it" has to be evidence rather than optimism.

Coverage of 60-80% of steady-state compute is a common landing zone. Full coverage looks
efficient until the first architecture change, at which point it is a fixed cost with no
workload attached.

### Choosing the instrument

| Instrument | Flexibility | Use when |
| --- | --- | --- |
| Compute savings plan | Any instance family, size, region, and covers Fargate and Lambda | The default. Survives a re-architecture, which is what usually goes wrong |
| Instance savings plan or standard reservation | Locked to a family, sometimes a region | The workload is genuinely fixed and the extra discount is material |
| Convertible reservation | Exchangeable, smaller discount | Legacy estates; largely superseded by savings plans |
| Spot | None; interruptible with a short warning | Interruption-tolerant work only |

Ladder the end dates. Everything expiring in the same month forces a large decision on a
date chosen by a purchase order rather than by the roadmap.

The commitment trap in one line: a discount is a promise to keep paying for a shape of
workload. Before signing a three-year term, ask what is on the roadmap for that workload
in months 6 to 18, and treat a planned migration as a reason to shorten the term or
choose the flexible instrument rather than a reason to skip the discount entirely.

### Spot

Spot suits CI runners, batch and ETL, stateless replicas behind capacity that can absorb
a loss, and rendering or training work that checkpoints. It does not suit a stateful
singleton, anything with a long unbreakable startup, or a workload whose interruption
handler has never been tested.

The interruption notice is short — around two minutes on AWS, thirty seconds on GCP — so
the workload must drain rather than shut down cleanly at leisure. Diversify across
instance families and availability zones: a spot request pinned to one type in one zone
has the interruption profile of that one pool, which is the configuration that generates
the stories about spot being unusable.

## Data transfer

The line nobody watches, frequently the largest single mover, and invisible on the
dashboards the team keeps.

| Path | Where it appears | Fix | What the fix costs |
| --- | --- | --- | --- |
| Cross-AZ between a service and its database, cache or peers | `DataTransfer-Regional-Bytes` | Colocate the chatty pair in one AZ, or reduce the chattiness | A single-AZ deployment has a zonal failure mode. This is a reliability trade, state it |
| Traffic to S3, DynamoDB or another AWS service via NAT | `NatGateway-Bytes` plus per-GB processing | Gateway or interface VPC endpoints | Interface endpoints have an hourly charge per AZ; compare against the transfer they remove |
| Internet egress to users | `DataTransfer-Out-Bytes` | CDN in front, compression, smaller payloads, cache headers that work | CDN cost, plus cache-invalidation complexity |
| Cross-region replication | Region-pair transfer lines | Question whether both regions need the data at that freshness | Recovery-point objective. Do not cut replication for cost without an RPO conversation |
| Load balancer to targets in another AZ | Regional transfer, plus LCU charges | Cross-zone balancing settings, or targets in every AZ | Uneven load distribution if you disable cross-zone with unequal target counts |
| Chatty service mesh or sidecar telemetry | Regional transfer and observability ingest | Sampling, batching, dropping high-cardinality labels | Debugging fidelity |

Diagnosing it: VPC flow logs aggregated by source and destination AZ and by prefix will
name the pair generating the traffic within an hour, which is faster than reasoning about
the architecture. Cost and Usage Report at the usage-type level tells you which of the
rows above is growing.

## Storage class and retention

The classic quiet ramp. Nothing changed, the bill grew, and the cause is that data
accumulates while nobody is responsible for deleting it.

- **Object storage**: lifecycle rules moving objects to infrequent-access and archive
  tiers by age, with an expiry for anything genuinely temporary. Check minimum storage
  durations and retrieval charges before tiering small, frequently read objects — early
  deletion of an archived object can cost more than leaving it hot.
- **Snapshots and images**: an expiry policy, and an owner. Snapshots of instances that
  no longer exist are the single most common orphan.
- **Logs**: full fidelity for the debugging window (7-30 days for most services), then
  aggregate or archive. Ingest is often a larger charge than storage, so sampling at the
  source beats a shorter retention on data you already paid to ingest.
- **Metrics**: cardinality is the cost driver, not the number of series names. One label
  carrying a user id or a request id multiplies the bill quietly. Downsample old data
  rather than deleting it.
- **Databases**: backup retention, point-in-time recovery windows, and old read replicas
  kept "just in case".

Before cutting any retention, check the floor: regulatory requirements, contractual
commitments, the security team's forensic window, and the debugging window the on-call
rota actually uses. Those are constraints, not preferences, and the person proposing the
cut usually does not know all four.

## Idle and orphaned resources

Cheap to find, safe to remove after an ownership check, and the right place to start
because it builds credibility for the harder recommendations.

- Unattached block volumes, and volumes attached to stopped instances that have been
  stopped for months.
- Unassociated elastic or static IP addresses, which are charged precisely because they
  are idle.
- Load balancers with no healthy targets, and target groups with none at all.
- Old snapshots, machine images and container images in the registry.
- Databases, clusters and caches provisioned for a project that ended.
- Non-production environments running nights and weekends. Scheduling development and
  staging to run only in working hours removes roughly two thirds of their hours, and it
  is the highest-value low-risk change on most bills.

The one check before deleting: ask the owner named in the tag, and if there is no owner
tag, that is a step-1 attribution problem rather than a licence to delete.

## Architectural cost

The only lever that moves unit cost rather than total spend, and the only one that needs
engineering time rather than a config change.

Look for: a design that makes N calls where 1 would do, an N+1 against a metered external
API, a per-row invocation of a serverless function where a batch would work, polling a
quiet queue at high frequency, a cache that is missing more than it hits, a synchronous
fan-out that multiplies both latency and cost, and per-request logging of full payloads.

Size these as engineering work with a cost per unit before and after, and rank them
against the config-change findings honestly — a 40,000 a year architectural saving that
needs two engineer-months may or may not beat three afternoons of lifecycle rules,
depending on what those engineers would otherwise be doing.

## Verification

A projection becomes a saving when a later invoice is smaller. The mechanics:

1. Record the baseline as the specific usage-type and resource lines the change targets,
   not the account total, which moves for a dozen unrelated reasons.
2. Set the verification date one full billing cycle after the change lands.
3. Check the reliability signal at the same time: the percentile the sizing was based on,
   error rate, and any SLO burn. A saving that is running down error budget is a debt.
4. Record the realised figure next to the projected one. Keeping both is what makes the
   next round of projections believable, especially when they differ.
