# Counters and ceilings

Read this at steps 2 and 3. Every command here reads. Changing a limit is step 4's last
resort, not something to do while gathering evidence.

## Contents

- [On a node](#on-a-node)
- [AWS NAT gateway](#aws-nat-gateway)
- [GCP Cloud NAT](#gcp-cloud-nat)
- [Azure SNAT and NAT gateway](#azure-snat-and-nat-gateway)
- [Per-destination ceilings](#per-destination-ceilings)

## On a node

A node debug pod runs in the host network namespace, so network sysctls and sockets read
there are the node's. Use an image your registry allows that carries `ss` and `conntrack`.

```bash
kubectl debug node/"$NODE" -it --image="$NET_TOOLS_IMAGE"
```

Inside it:

```bash
cat /proc/sys/net/netfilter/nf_conntrack_count /proc/sys/net/netfilter/nf_conntrack_max
conntrack -S                       # per-CPU insert_failed, drop, early_drop
cat /proc/sys/net/ipv4/ip_local_port_range
ss -s                              # the TCP line includes the timewait total

# TIME_WAIT grouped by peer address and port, top 15
ss -tan state time-wait | awk 'NR > 1 {print $4}' | sort | uniq -c | sort -rn | head -15

# Established connections grouped by peer, to find the busiest destination
ss -tan state established | awk 'NR > 1 {print $4}' | sort | uniq -c | sort -rn | head -15
```

On the node itself, the kernel log shows drops: `nf_conntrack: table full, dropping
packet`.

With node_exporter scraped:

```promql
node_nf_conntrack_entries / node_nf_conntrack_entries_limit
rate(node_nf_conntrack_stat_insert_failed[5m])
rate(node_nf_conntrack_stat_drop[5m])
node_sockstat_TCP_tw
```

`insert_failed` rising in step with 5-second DNS stalls points at the DNS conntrack race,
not at a full table.

kube-proxy sets the conntrack table size on start from its own settings (per-core maximum
and a minimum). Read those in the kube-proxy configuration before concluding what the
limit is, and change them there if step 4 ever gets that far.

## AWS NAT gateway

Metrics in the `AWS/NATGateway` namespace, dimension `NatGatewayId`:

| Metric | Meaning |
| --- | --- |
| `ErrorPortAllocation` | Connections that could not get a source port. Any non-zero value is exhaustion |
| `ActiveConnectionCount` | Concurrent active TCP connections |
| `ConnectionAttemptCount`, `ConnectionEstablishedCount` | New connections attempted and established |
| `IdleTimeoutCount` | Connections closed by the 350-second idle timeout |
| `PacketsDropCount` | Packets dropped by the gateway |

```bash
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
  --metric-name ErrorPortAllocation \
  --dimensions Name=NatGatewayId,Value="$NAT_ID" \
  --statistics Sum --period 60 \
  --start-time "$START" --end-time "$END"
```

To find the destination, use VPC Flow Logs on the NAT gateway's network interface and rank
by destination address and port over the failure window.

## GCP Cloud NAT

Cloud NAT allocates source ports per VM. On GKE every pod on a node shares that node's
allocation, so one busy pod can exhaust ports for its neighbours.

```bash
gcloud compute routers get-nat-mapping-info "$ROUTER" --region "$REGION"
gcloud compute routers nats describe "$NAT" --router "$ROUTER" --region "$REGION"
```

With NAT logging enabled, dropped allocations are logged with
`jsonPayload.allocation_status="DROPPED"`. The metric
`router.googleapis.com/nat/dropped_sent_packets_count` with reason `OUT_OF_RESOURCES` counts
packets dropped for lack of ports.

The allocation is raised with `--min-ports-per-vm`, or made elastic with
`--enable-dynamic-port-allocation` and `--max-ports-per-vm`, on
`gcloud compute routers nats update`.

## Azure SNAT and NAT gateway

Load balancer outbound (the AKS default): the load balancer's metrics include SNAT
connection count, which can be split by connection state — `Failed` is exhaustion — and
allocated and used SNAT ports per backend instance. Each node gets a fixed number of SNAT
ports per outbound address. On AKS the outbound address count and per-node ports are
changed with `az aks update --load-balancer-managed-outbound-ip-count` and
`--load-balancer-outbound-ports`.

NAT gateway: each public address provides 64,512 SNAT ports, allocated on demand. Its
metrics include SNAT connection count and dropped packets. The default idle timeout is four
minutes.

## Per-destination ceilings

Every limit below is per destination IP, port and protocol, which is why one hot
destination exhausts a path that looks nearly empty in aggregate.

| Path | Ceiling toward one destination |
| --- | --- |
| Linux client, default port range | About 28,000 ports per source address (32768 to 60999) |
| AWS NAT gateway | 55,000 simultaneous connections per NAT address; more addresses multiply it |
| GCP Cloud NAT | The ports allocated to the VM (node), shared by every pod on it |
| Azure load balancer outbound | The SNAT ports allocated to the node per outbound address |
| Azure NAT gateway | 64,512 ports per public address |

Little's law gives the demand: ports in use toward a destination equal new connections per
second times the time each port stays in use, TIME_WAIT included (60 seconds on Linux, on
whichever side closed first). If the demand is within a factor of two of the ceiling, the
next traffic peak will cross it.
