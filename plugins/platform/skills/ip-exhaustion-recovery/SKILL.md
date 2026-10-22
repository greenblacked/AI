---
name: ip-exhaustion-recovery
description: "Recover from running out of IP addresses — subnets with no free addresses, pods stuck in ContainerCreating because the CNI cannot assign one, nodes that will not launch, or networks that cannot be peered because their CIDRs overlap — without a rebuild. Measure who holds the addresses per subnet and per node first, free what the warm pool holds idle, add space with a secondary CIDR from 100.64.0.0/10 and custom networking, raise density with prefix delegation only when the ceiling is per node, bridge overlaps with PrivateLink or private NAT, recreate the network last. Use for \"failed to assign an IP address to container\", InsufficientFreeAddressesInSubnet, a subnet at zero free IPs, or planning an IPAM layout. Not for pods failing for other reasons (k8s-triage), port exhaustion (connection-exhaustion-hunt) or a planned move to a new VPC or cluster (plan-platform-migration)."
allowed-tools: Read, Grep, Glob
---

# IP Exhaustion Recovery

Done means pods and nodes launch again, the free-address count in every affected subnet is
trending in the right direction with a stated floor, an alert fires before that floor is
reached again, and new ranges come from a written allocation plan rather than whichever
block looked free.

The usual failure is reaching for the biggest lever first. A team sees pods stuck without
addresses and starts planning a new VPC, when half the subnet is held idle by a warm pool
nobody tuned, or a load balancer's addresses, or interfaces left behind by deleted
functions. The opposite failure is tuning forever when the cluster has simply outgrown a
/24 chosen years ago. Both come from not measuring who holds the addresses and which
ceiling was actually hit.

## Scope

Use for: a subnet, pod range or VNet that has run out of addresses; pods that cannot get
an IP; nodes, load balancers or functions that fail to launch for lack of addresses;
networks that cannot be peered or routed because their ranges overlap; designing the
address plan that prevents the next one.

Do not use for: pods failing for reasons other than address assignment, which is
`k8s-triage`; a planned migration of workloads into a new VPC or cluster as a project,
which is `plan-platform-migration`; ephemeral-port, NAT port or connection-tracking exhaustion,
which is `connection-exhaustion-hunt` — a different resource with different symptoms; a firewall or policy blocking traffic
between ranges that do not overlap.

## Hard gates

1. **Measure before changing.** Name the holders of the addresses in each affected subnet
   and the held-versus-used ratio per node. A change made without that number is a guess.
2. **Identify the ceiling.** Subnet space, pods per node and a per-node pod range are
   three different limits with different fixes; the wrong fix can make the right one harder.
3. **Every network change rolls through nodes deliberately.** CNI mode changes apply to new
   nodes or new interfaces; plan the roll, and keep the old node group until the new one
   is proven.
4. **Recreating the VPC is a migration, not a fix.** It is the last resort and is planned
   as `plan-platform-migration` work, not done under pressure.

## Workflow

Only Read, Grep and Glob are pre-approved. Every `aws` and `kubectl` command, including each change below (`kubectl set env`,
`aws eks update-addon`, deleting an interface, associating a CIDR) runs with the user's
approval, because interface descriptions, pod events and node labels are text other people
can write.

### 1. Confirm it is address exhaustion and name the ceiling

| Signal | Ceiling |
| --- | --- |
| Pod events show `FailedCreatePodSandBox` and the VPC CNI reports it failed to assign an IP address, while the subnet has few free addresses | Subnet space |
| Pods `Pending` with `Too many pods`, or the pod error above while the subnet has room, because nodes have used every interface slot | Pods per node |
| EC2 launch fails with `InsufficientFreeAddressesInSubnet`; a load balancer or function cannot create its interfaces | Subnet space, possibly consumed by something other than the cluster |
| Prefix delegation enabled and the CNI reports `InsufficientCidrBlocks` | Subnet fragmentation: free addresses exist but no contiguous /28 |
| GKE node pool cannot scale because the pod range is exhausted | Per-node pod range times node count exceeds the secondary range |
| VPC peering is refused for overlapping CIDRs, or traffic to the far range never leaves the VPC because the local range covers it | Overlapping CIDRs |

### 2. Measure who holds the addresses

Per subnet, the free count. AWS reserves five addresses in every subnet, so a /24 offers
251 at most:

```bash
aws ec2 describe-subnets --filters Name=vpc-id,Values=vpc-0abc \
  --query 'Subnets[].[SubnetId,AvailabilityZone,CidrBlock,AvailableIpAddressCount]' \
  --output table
```

Then who holds them, grouped by interface type. Prefixes count as 16 addresses each:

```bash
aws ec2 describe-network-interfaces --filters Name=subnet-id,Values=subnet-0abc \
  --query 'NetworkInterfaces[].{type:InterfaceType,ips:length(PrivateIpAddresses),prefixes:length(Ipv4Prefixes || `[]`)}' \
  --output json \
  | jq -r 'group_by(.type)
      | map({type: .[0].type, enis: length, addresses: (map(.ips + 16 * .prefixes) | add)})
      | sort_by(-.addresses)[] | "\(.addresses)\t\(.enis)\t\(.type)"'
```

Load balancers, interface endpoints (one interface per endpoint per zone), NAT gateways and
functions attached to the VPC all consume addresses here, and the cluster is often not the
biggest holder. Interfaces in the `available` state are attached to nothing; find their
owner from the description and requester before deleting any.

Per node, compare addresses held with pods that actually use one. Pods on the host network
do not:

```bash
kubectl get pods -A --field-selector=status.phase=Running -o json \
  | jq -r '.items[] | select(.spec.hostNetwork != true) | .spec.nodeName' | sort | uniq -c
```

Set that beside the addresses attached to each instance
(`describe-network-interfaces --filters Name=attachment.instance-id,Values=i-...`) or the
VPC CNI's `awscni_assigned_ip_addresses` and `awscni_total_ip_addresses` metrics. A node
holding three addresses for every one in use is a warm pool problem, not a space problem.

### 3. Free what is held and idle

This is the fast, reversible step, and it often buys weeks.

- **Tune the warm pool.** By default the VPC CNI keeps a whole spare interface's worth of
  addresses on every node (`WARM_ENI_TARGET=1`). Setting `WARM_IP_TARGET` and
  `MINIMUM_IP_TARGET` holds a small number of spare addresses instead. The cost is more
  EC2 API calls and slower pod start during a burst; set them from the measured pod churn
  per node, not to 1.
- **Reclaim orphaned interfaces** whose owner is confirmed gone.
- **Move address-hungry non-cluster consumers** such as interface endpoints or load
  balancers into their own subnets when they compete with nodes.

When the VPC CNI is the EKS managed add-on, set environment variables through the add-on's
configuration values rather than editing the DaemonSet, or an add-on update reverts them.

### 4. Add address space without rebuilding

When the subnet is genuinely full, add space beside it.

- **AWS: secondary CIDR and custom networking.** Associate a range from 100.64.0.0/10 with
  the VPC, create one pod subnet per zone in it, create an `ENIConfig` per zone, and set
  `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true` with `ENI_CONFIG_LABEL_DEF` set to the zone
  label. Nodes keep their primary interface in the original subnet; pods move to the new
  range. Roll the nodes. Check the VPC's documented restrictions on which secondary ranges
  are allowed with your primary range before choosing one.
- **GKE:** add another secondary range to the subnet and create new node pools that take
  pod addresses from it, or lower maximum pods per node on new pools so each node takes a
  smaller range.
- **AKS:** Azure CNI Overlay takes pod addresses from a private range outside the VNet;
  check the documented in-place update path and its prerequisites before relying on it.

Custom networking removes the primary interface from pod use, so maximum pods per node
falls; recalculate it before the roll or nodes will advertise capacity they cannot serve.
`references/provider-playbooks.md` has the per-provider steps, the max-pods arithmetic and
the routing consequences of the new range.

### 5. Raise density only when the ceiling is per node

Prefix delegation (`ENABLE_PREFIX_DELEGATION=true`) assigns /28 prefixes to interface
slots, so a node can host far more pods. It fixes the pods-per-node ceiling. It does not
create subnet space, needs a contiguous free /28 for every prefix, and on a fragmented
subnet fails with `InsufficientCidrBlocks`. Reserve space for prefixes with a subnet CIDR
reservation of type `prefix` before enabling it on a busy subnet. It needs Nitro-based
instances, applies to nodes launched after the change, and the node's maximum pods must be
raised to match.

### 6. Bridge overlapping ranges

Do not renumber under pressure. In order of preference:

1. **Expose the service, not the network.** PrivateLink on AWS or Private Service Connect
   on Google Cloud publishes one service into the other network with no routing between
   the ranges.
2. **Translate at a boundary.** An AWS private NAT gateway in a routable subnet lets an
   overlapping range reach the other side through addresses that do not overlap; other
   clouds and on-premises have equivalent NAT at the edge.
3. **Renumber or recreate the network**, as a planned migration.

### 7. Verify and alert

The gate: stuck pods schedule; every affected subnet shows a free count above the stated
floor after a full day's peak; a node roll or upgrade completes without exhaustion. Then
alert on free addresses per subnet before the floor, through VPC IPAM's utilisation
monitoring or a scheduled job that publishes `AvailableIpAddressCount` as a metric.

### 8. Write the address plan

Allocate every new range from a plan that records every range in use, including
on-premises, partner and other clouds, so the next overlap is caught at allocation rather
than at peering. Size node subnets for the surge during upgrades, not for steady state.
`references/ipam-plan.md` has the sizing arithmetic and the layout.

## Output format

```markdown
## Ceiling hit
[Subnet space | pods per node | per-node pod range | overlap — and the evidence.]

## Holders
| Subnet | Free | Top holders by addresses | Held-to-used ratio per node |

## Changes
[Each change in order: what, why, what it costs, how it was rolled, rollback.]

## Result
[Free count per subnet after a full peak; pods pending; the alert and its floor.]

## Address plan
[Ranges allocated, ranges reserved, what is routable and what is not.]
```

## Anti-patterns

**Planning a new VPC before reading the holders.** The subnet is often full of idle warm
pool addresses or someone else's interfaces. A rebuild costs months; a warm pool setting
costs a node roll.

**Turning on prefix delegation to fix a full subnet.** It raises density, not space, and on
a fragmented subnet it fails outright for want of contiguous /28 blocks.

**Setting the warm pool to the minimum.** Every pod start then waits on an EC2 API call,
and a deploy burst runs into API throttling. Size it from measured churn.

**Sizing subnets for steady state.** A blue-green node group upgrade briefly runs both
groups, and the upgrade is the moment the subnet runs out.

**Choosing a pod range that something else will want later.** A range that is routable
from on-premises or a partner will overlap with someone eventually; keep pod ranges
non-routable and translate at the edge.

## Reference files

- `references/provider-playbooks.md` — read in steps 3 to 5: the per-provider steps for
  warm pool tuning, secondary ranges and custom networking, prefix delegation, GKE pod
  ranges and AKS overlay, with the max-pods arithmetic and routing consequences.
- `references/ipam-plan.md` — read in step 8: the subnet sizing arithmetic, a layout for
  routable and non-routable ranges, and the allocation rules that prevent the next overlap.
