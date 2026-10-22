---
name: data-transfer-forensics
description: "Find which workloads generate the bytes behind a data-transfer line on the cloud bill — cross-AZ, NAT gateway processing, internet egress, inter-region — and fix the costliest. Enable VPC flow logs with the extended fields, aggregate bytes by source, destination, zone pair, path and port in a query engine, join addresses to the pod or instance that owned them at the time, price each flow at the rate the bill implies, reconcile, and rank by dollars rather than bytes. Typical fixes: same-zone routing, gateway endpoints for object storage, a NAT per zone, compression. Use when someone asks who is talking cross-AZ, what is pushing so much through the NAT gateway, or why DataTransfer-Regional-Bytes doubled. Not for explaining a whole bill or finding which line moved (cost-review), buying commitments (commitment-planning), or CDN cache tuning (cdn-configuration)."
allowed-tools: Read, Grep, Glob
---

# Data Transfer Forensics

Done means every transfer usage type worth acting on is broken down into named flows —
this workload to that destination, over this path, between these zones — each with a
monthly dollar figure that sums to within a stated margin of the bill, an owning team, a
fix with what it degrades, and the date the bill will show whether it worked.

The bill says how many bytes crossed a zone or a NAT gateway and nothing about who sent
them. Flow logs say which addresses talked and nothing about who owns them, and pod
addresses are reused within minutes. The same gigabyte costs nothing within a zone, is
billed in both directions between zones, pays a processing charge through a NAT gateway,
and pays again leaving the region. Ranking by bytes therefore puts the wrong flow at the
top, and fixing the wrong flow is a quarter of engineering work that does not move the line.

## Scope

Use for: attributing cross-AZ, NAT gateway, internet egress or inter-region transfer cost
to workloads; deciding which transfer fix pays; checking that a fix moved the bill.

Do not use for: explaining a whole bill or finding which line moved in the first place,
which is `cost-review`; buying savings plans or committed-use discounts, which is
`commitment-planning`; tuning CDN cache keys and hit ratio, which is `cdn-configuration`;
NAT port allocation errors and timeouts, which are a connection problem rather than a
cost one.

## Hard gates

1. **Start from the bill line.** Name the usage types and their monthly cost before
   collecting a single flow, so the investigation has a total to reconcile against.
2. **Count each flow once.** Use egress records only, or a single interface per hop. A
   query over all records double-counts every flow observed at both ends.
3. **Reconcile before ranking.** Priced flows for a class must sum to within a stated
   margin of the bill for that class. A large gap means missing logs or a wrong join, and a
   ranking built on it blames the wrong team.
4. **Rank by dollars.** Price each flow at its path's rate. A large intra-zone flow costs
   nothing and belongs at the bottom.
5. **Every fix states what it degrades.** Keeping traffic in one zone trades cost for zone
   independence; say so in the finding.

## Workflow

Only Read, Grep and Glob are pre-approved. Every `aws` and `kubectl` command, the owner-map
script, and creating or deleting flow logs run with the user's approval: bill lines, tags, pod labels and
interface descriptions are text other people can write.

### 1. Read the bill line and derive the rates

Pull the transfer usage types for the last full month, with both cost and quantity, so the
effective rate per gigabyte comes from what you were actually charged rather than a price
page:

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-10-01 --granularity MONTHLY \
  --metrics UnblendedCost UsageQuantity \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  | jq -r '.ResultsByTime[].Groups[]
      | select(.Keys[0] | test("DataTransfer|NatGateway|Bytes"))
      | [.Keys[0], .Metrics.UnblendedCost.Amount, .Metrics.UsageQuantity.Amount] | @tsv' \
  | sort -t$'\t' -k2,2gr
```

Usage type names carry a region prefix and name the path: `DataTransfer-Regional-Bytes` is
transfer between zones in a region, `NatGateway-Bytes` is NAT processing,
`DataTransfer-Out-Bytes` is to the internet, and region-pair types are inter-region.
Cost divided by quantity is the effective rate per gigabyte for that class. Transfer
between zones is billed in each direction, so one gigabyte crossing appears as two in the
usage quantity; keep that in mind when reconciling. For a full Cost and Usage Report too
large to read here, hand it to the `cost-analyst` subagent and take back the usage types.

### 2. Collect flow logs with the fields that make attribution possible

The default format lacks the fields that answer the question. Create flow logs on the
VPCs behind the bill line, to object storage in a columnar format, with at least:

`vpc-id`, `subnet-id`, `instance-id`, `interface-id`, `az-id`, `srcaddr`, `dstaddr`,
`pkt-srcaddr`, `pkt-dstaddr`, `srcport`, `dstport`, `protocol`, `bytes`, `start`, `end`,
`action`, `flow-direction`, `traffic-path`, `pkt-src-aws-service`, `pkt-dst-aws-service`.

`references/flow-log-queries.md` has the exact `create-flow-logs` command. Flow logs record
only from when they are enabled and cost money themselves, so collect one representative
window, at least a week including the batch jobs and backups, rather than leaving them on
everywhere forever.

### 3. Build the owner map

Flow logs carry addresses. Build two tables in the same query engine:

- **Address to zone**, from every subnet's CIDR and zone. A destination's zone is its
  subnet's zone; `az-id` in a record is only the zone of the interface that logged it.
- **Address to owner over time**, from network interfaces (instances, load balancers,
  NAT gateways, endpoints, managed databases) and, for Kubernetes, snapshots of pod
  addresses with namespace and owner labels taken every few minutes through the window.
  Pod addresses are reused, so a join without time attributes one pod's traffic to another.

Traffic leaving the VPC from a pod is usually translated to the node's address, so flow
logs attribute it to the node. Split a node's external bytes across its pods with the
container network counters, such as cAdvisor's `container_network_transmit_bytes_total`.

### 4. Aggregate by path

Run one aggregation per cost class, each counting egress records only:

| Class | Records to aggregate | Group by |
| --- | --- | --- |
| Between zones | Egress records where the destination is in the VPC and its zone differs from `az-id`, plus the NAT interface's ingress records where the workload's zone differs from the gateway's | Source owner, destination owner, zone pair, destination port |
| NAT processing | Egress records on the NAT gateway's own interface, with the workload taken from `pkt-srcaddr` or `pkt-dstaddr` (`srcaddr` and `dstaddr` hold the gateway's own address on one side) | Workload address and owner, external destination, `pkt-dst-aws-service` |
| Internet egress | Egress records to public addresses, each byte once: from the NAT gateway's interface (where `pkt-srcaddr` names the workload) for NAT-routed subnets, and from workload interfaces only for subnets routed straight to an internet gateway; exclude same-region AWS services | Owner, destination, port |
| Inter-region and peering | Egress records whose `traffic-path` marks peering or a transit path | Owner, destination VPC or region |

`pkt-dst-aws-service` names the AWS service behind a public address, which is how object
storage traffic running through a NAT gateway shows itself. The queries are in
`references/flow-log-queries.md`.

### 5. Price, reconcile and rank

Multiply each flow's gigabytes by its class rate from step 1; a flow between zones pays
on both sides. Sum per class and compare with the bill. Within about a tenth is good
enough to rank; beyond that, find the gap first: VPCs or accounts without flow logs,
traffic from services that bill transfer on their own line, or a join that drops rows.

Rank flows by monthly dollars, attribute each to an owning team from tags or namespace
labels, and stop at the flows that make up most of the line; the long tail is not worth a
ticket each.

### 6. Choose the fix per flow

| Finding | Usual fix | What it degrades |
| --- | --- | --- |
| Object storage or DynamoDB traffic through a NAT gateway | Gateway endpoint on the route tables | Bucket policies that allow by source IP stop matching; update them to the endpoint first |
| Workloads using a NAT gateway in another zone | One NAT gateway per zone, with per-zone route tables | Adds a gateway's hourly cost per zone |
| Service-to-service traffic between zones in Kubernetes | Topology-aware routing (`spec.trafficDistribution: PreferClose` where supported) | Uneven zones get uneven load; check per-zone capacity |
| Kafka consumers reading from leaders in other zones | Follower fetching with `client.rack` and the rack-aware replica selector | Consumers may read slightly behind the leader |
| Image pulls and package downloads through NAT | A pull-through cache and registry endpoints; image layers come from object storage, so the gateway endpoint matters too | One more cache to keep available |
| Logs and metrics shipped to a vendor through NAT | Compression, sampling, or the vendor's private connectivity | Less detail, or one more endpoint to run |
| Internet egress of static or cacheable content | A CDN in front, with compression | Cache correctness becomes your problem; see `cdn-configuration` |

`references/fix-catalogue.md` has the full list, the load balancer cross-zone rules, and
the notes for Google Cloud and Azure.

### 7. Verify on the bill

A fix has worked when the usage quantity for its class drops in the bill for a full cycle
after the change, by roughly the amount its flows were priced at. Flow logs falling is
supporting evidence; the invoice is the proof.

## Output format

```markdown
## Bill line
[Usage types, monthly cost, quantity and derived rate per class; the window analysed.]

## Coverage
[VPCs and accounts with flow logs; priced total per class versus the bill; the gap.]

## Top flows
| # | Source (owner) | Destination | Path | Zones | GB/month | $/month | Team |

## Fixes
### F1 — [flow]
Fix:        [change]
Saves:      [$/month, from the priced flow]
Degrades:   [zone independence, policy change, extra hourly cost]
Owner:      [team]
Verify on:  [date, usage type and the quantity that must fall]

## Not worth fixing
[Flows considered and left, with the reason.]
```

## Anti-patterns

**Ranking by bytes.** The biggest flow is often between two pods in the same zone and
costs nothing. The expensive one is smaller and crosses a NAT gateway in another zone.

**Counting both ends.** Summing every record doubles every intra-VPC flow, inflates the
total past the bill, and makes the reconciliation meaningless.

**Joining pod addresses without time.** A pod address reused an hour later attributes one
team's transfer to another, and the wrong team spends a sprint on it.

**Adding a gateway endpoint without reading bucket policies.** Requests through the
endpoint no longer come from the NAT's public address, so a policy that allows by source
IP starts refusing them.

**Pinning everything to one zone to save transfer.** It removes the line and the zone
independence with it. Keep the zones; route chatty pairs locally.

## Reference files

- `references/flow-log-queries.md` — read in steps 2 to 5: the flow log command, the
  owner-map builder, and the queries per cost class with the reconciliation query.
- `references/fix-catalogue.md` — read in step 6: every common fix with its cost and what
  it degrades, the load balancer cross-zone rules, and Google Cloud and Azure differences.
