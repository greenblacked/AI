# Address plan

Read this once the immediate exhaustion is fixed, to size the next ranges and to stop the
next overlap at allocation time rather than at peering time.

## Contents

- Allocation rules
- Layout
- Sizing arithmetic
- Recording allocations in AWS VPC IPAM
- When IPv6 is the answer

## Allocation rules

1. **Register every range before allocating any.** Include on-premises, every cloud,
   partners, acquired companies' networks, VPN client pools and the ranges managed
   services use. An overlap is almost always with a range nobody wrote down.
2. **Allocate only through the plan.** A VPC created with a CIDR typed by hand is the
   next overlap.
3. **Every allocation has an owner and a purpose.** An unowned /16 is never reclaimed.
4. **Do not hand out large blocks just in case.** 10.0.0.0/8 holds 256 /16 blocks; an
   organisation that gives every VPC a /16 runs out of private space for routable ranges
   far sooner than it expects.
5. **Keep pod ranges non-routable.** Pods take addresses from a range such as part of
   100.64.0.0/10 that is never advertised over peering, transit or VPN, and is therefore
   reused in every VPC. Traffic leaving the VPC is translated to node addresses.
6. **Hold back half.** Leave a contiguous half of each VPC's routable range unallocated
   so the next subnet does not need a secondary CIDR.

## Layout

| Range | Routable | Holds | Size it by |
| --- | --- | --- | --- |
| Regional supernet per environment | Yes | All VPCs of that environment in the region | Expected VPC count with the half held back |
| VPC primary range | Yes | Node, load balancer, endpoint and data subnets | The subnets below, then doubled |
| Node subnet, one per zone | Yes | Node primary interfaces | Peak nodes during an upgrade |
| Load balancer subnet, one per zone | Yes | Load balancer interfaces | Load balancers times their scaling headroom; ALBs need free addresses to scale |
| Endpoint subnet, one per zone | Yes | Interface endpoints | One address per endpoint per zone, with room for new services |
| Data subnet, one per zone | Yes | Databases and caches | Instances plus failover replacements |
| Pod range, one subnet per zone | No | Pod addresses via custom networking or an equivalent | Pods during an upgrade plus the warm pool |

Separate subnets by function so a burst in one consumer, such as a load balancer scaling
out, cannot starve nodes.

## Sizing arithmetic

Size for the upgrade, not steady state. A blue-green node group upgrade runs both groups
for a while; a surge upgrade adds a configured number of extra nodes.

```text
addresses per zone = (peak nodes per zone x upgrade factor) x (addresses per node)
                     + other consumers in the subnet
                     + 5 reserved by the provider
round up to the next power of two, then keep a margin for growth
```

Worked example for a pod subnet under custom networking: 60 nodes per zone at peak,
blue-green upgrades (factor 2), 30 pods per node plus a warm pool of 10:

```text
120 nodes x 40 addresses = 4,800 -> /19 (8,192) per zone
```

The node subnet in the same design needs one primary address per node plus any warm
interfaces held there, so a /24 per zone covers 120 nodes with room.

Without custom networking, nodes and pods share the subnet and the addresses per node are
the node's full attached interface capacity, not its pod count.

## Recording allocations in AWS VPC IPAM

```bash
aws ec2 create-ipam --operating-regions RegionName=eu-west-1
aws ec2 create-ipam-pool --ipam-scope-id ipam-scope-0abc \
  --address-family ipv4 --locale eu-west-1 --description "prod eu-west-1"
aws ec2 provision-ipam-pool-cidr --ipam-pool-id ipam-pool-0abc --cidr 10.32.0.0/12
aws ec2 create-vpc --ipv4-ipam-pool-id ipam-pool-0abc --ipv4-netmask-length 20
```

Allocate VPCs from the pool rather than by literal CIDR, and import ranges that exist
outside AWS into the plan so the overlap check covers them. IPAM also reports utilisation
per resource; alert on it before a subnet reaches the free-address floor set during recovery.

On other clouds and on-premises, the same rules apply in whatever records the plan; a
version-controlled file reviewed like code is better than an unreviewed spreadsheet.

## When IPv6 is the answer

An IPv6 cluster removes pod address exhaustion as a class. On EKS the address family is
chosen when the cluster is created and cannot be changed afterwards, so it is a new cluster
and a migration, not a fix for today. Raise it in the plan for the next cluster rather than
as part of this recovery.
