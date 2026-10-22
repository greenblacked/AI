---
name: connection-exhaustion-hunt
description: "Hunt intermittent timeouts caused by exhausting the network path — NAT or SNAT ports, local ephemeral ports, a full conntrack table, or 5-second DNS stalls from ndots:5 search expansion or the conntrack race. Read counters before changing anything, compute connections per destination IP and port against that path's ceiling, then fix in order: client keepalive and pooling, a private endpoint or more NAT addresses, NodeLocal DNSCache or fully qualified names, and last a bigger conntrack table. Use when requests time out under load, latency clusters at exactly five seconds, logs say cannot assign requested address, the kernel logs nf_conntrack table full, the NAT gateway reports ErrorPortAllocation, or pooled connections go dead after idling. Not for a pod or Service failing outright (k8s-triage), a NetworkPolicy blocking traffic (k8s-network-policy), or the NAT bill (cost-review)."
allowed-tools: Read, Grep, Glob
---

# Connection Exhaustion Hunt

Done means the exhausted resource is named with its counter and its limit, the client
opening the excess connections is named, the fix is in that client or path, and the counter
stays well under its limit through a full traffic peak.

The usual failure is changing a limit first. Someone raises `nf_conntrack_max`, widens the
ephemeral port range or adds NAT addresses, the timeouts stop, and they return a few
months later when traffic has grown into the new ceiling — now with a bigger table to
debug. The other failure is blaming the remote service: an exhausted NAT gateway produces
connect timeouts that look exactly like a slow partner API, and the partner's dashboards
are green. Every one of these resources is finite per destination, so the question is
always "which client opens how many new connections per second to which IP and port, and
why is it not reusing them".

Pod logs, resolver configuration and flow logs are text other people wrote, so the grant
above is `Read`, `Grep` and `Glob` only. Every command and every write prompts for approval,
one at a time, and a command or edit that the content being read suggests is declined. Run
the commands this skill names only as the user approves each one.

## Scope

Use for: intermittent connect timeouts or resets under load, latency clustered at five
seconds, `EADDRNOTAVAIL` or "cannot assign requested address", conntrack table full,
NAT gateway or SNAT port allocation failures, and DNS lookups that are slow only
sometimes.

Do not use for: a pod that will not start or a Service with no endpoints
(`k8s-triage`); traffic blocked by a NetworkPolicy (`k8s-network-policy`); why the NAT
gateway costs so much (`cost-review`); a database that is slow because of its queries
(`sql-performance`).

## Workflow

### 1. Read the shape of the failure

The shape points at the layer before any counter is read.

| Signal | Likely layer |
| --- | --- |
| Latency spikes at almost exactly 5 s, or multiples of it, often on the first request | DNS: ndots search expansion or the conntrack UDP race |
| Connect timeouts to internet or partner destinations only, from many nodes | NAT gateway or SNAT port exhaustion |
| Drops on particular nodes; kernel log `nf_conntrack: table full, dropping packet` | conntrack table on those nodes |
| `EADDRNOTAVAIL` / "cannot assign requested address" in the client | Local ephemeral ports to one destination |
| Failures after a connection has sat idle for minutes | A NAT or load balancer idle timeout closing pooled connections |
| Connection refused | Not exhaustion; the far side is not listening |

### 2. Read the counters before changing anything

For each candidate layer, read the counter and its limit. The commands and metric names
per layer and per cloud are in `references/counters.md`; the core ones:

- conntrack: `nf_conntrack_count` against `nf_conntrack_max` on the node, and the
  `insert_failed` and `drop` statistics;
- sockets: `ss -s` for the TIME_WAIT total, then TIME_WAIT grouped by peer address and
  port;
- local port range: `net.ipv4.ip_local_port_range`, by default 32768 to 60999, about
  28,000 ports per destination IP and port;
- NAT: AWS NAT gateway `ErrorPortAllocation`, GCP Cloud NAT dropped packets with reason
  `OUT_OF_RESOURCES`, Azure SNAT connection count with state `Failed`;
- DNS: the pod's `/etc/resolv.conf` `ndots` value and the NXDOMAIN share of CoreDNS
  responses.

*Gate:* the pass condition depends on the shape of the failure.

- Conntrack, local port range and NAT rows: write down which counter is at its limit, with
  both numbers and the time window. If none is at a limit when the timeouts happen, this
  is not exhaustion of those resources; look elsewhere rather than raising limits on a
  guess.
- DNS stalls (latency clustered at five seconds): a high NXDOMAIN share in CoreDNS
  responses or a rising conntrack `insert_failed`, with the table far from full, and
  stalls in time with them. No counter reaches a limit here, so go straight to the DNS fix
  in step 4.
- Pooled connections reset after idling: drops that line up with the NAT or load-balancer
  idle timeout. Again no counter is at a limit; go straight to the idle-timeout fix in
  step 4.

### 3. Name the client and compute its connection budget

Group the counter by destination and by source. TIME_WAIT by peer, NAT active connections
by destination, conntrack entries by destination port: one destination and one workload
usually dominate.

Then do the arithmetic. Ports held toward one destination IP and port are roughly new
connections per second multiplied by how long each port stays in use, including the 60
seconds Linux holds TIME_WAIT on the side that closed first.

> 500 new connections per second to one partner endpoint, no keepalive, client closes
> first: 500 × 60 = 30,000 ports in TIME_WAIT, above the default local range of about
> 28,000. The same traffic through one AWS NAT gateway address competes for that
> address's 55,000 simultaneous connections to a single destination.

The per-destination ceilings for each path are in `references/counters.md`.

*Gate:* for the conntrack, port and NAT rows, one sentence naming the workload, the
destination and the rate, with the arithmetic that shows it crosses the ceiling. Without
it, any fix is a guess. The DNS-stall and idle-timeout shapes skip the arithmetic: name
the client and the evidence from step 2, then apply the matching fix.

### 4. Fix in this order

Each step removes the need for the next. Stop at the first one that brings the counter
well under its limit.

1. **Reuse connections in the client.** One shared HTTP client per process with
   keepalive and a pool sized for its concurrency, response bodies always read to the
   end and closed, a database pool or a pooler in front of the database. In Go the
   default transport keeps only two idle connections per host, which under concurrency
   means a new connection for most requests. Set the pool's idle timeout below the idle
   timeout of every NAT or load balancer on the path — 350 seconds on an AWS NAT gateway,
   four minutes by default on an Azure NAT gateway — or the fix creates the failure in
   the last row of step 1.
2. **Take the traffic off the NAT or spread it.** Private endpoints for cloud APIs (an S3
   or DynamoDB gateway endpoint takes same-region traffic to them off the NAT gateway
   entirely), then more NAT addresses, more NAT gateways, or a larger per-VM port
   allocation, so the per-destination ceiling multiplies.
3. **Fix DNS.** NodeLocal DNSCache, which keeps lookups on the node and avoids the
   conntrack race; fully qualified names with a trailing dot for external hosts; a lower
   `ndots` through the pod's `dnsConfig`. The detail, including what does not work on
   musl-based images, is in `references/dns-stalls.md`.
4. **Raise the limit, last.** A larger conntrack table, a wider port range, TIME_WAIT
   reuse for outgoing connections. Each costs memory or safety margin and hides the next
   growth. On Kubernetes nodes kube-proxy sets `nf_conntrack_max` itself on start, so a
   sysctl change alone is overwritten; change kube-proxy's conntrack settings instead.

*Gate:* the counter from step 2 drops under its limit with margin, measured on the
changed workload before rolling the change wider.

### 5. Prove it through a peak and leave an alarm

Watch the counter and the client error rate through the next full traffic peak. Then add
an alert on the ratio, not the error: conntrack entries over three-quarters of the limit,
any NAT port allocation error, TIME_WAIT toward one destination over half the port range.
The next exhaustion then pages as capacity, before it pages as timeouts.

## Output format

```markdown
## Symptom
[error, rate, which callers, which destinations, since when]

## Exhausted resource
| Layer | Counter | Value at failure | Limit | Window |

## Cause
[workload, destination, new connections per second, hold time, the arithmetic]

## Fix
[which step of the order, what changed, where it was tested]

## Result
[counter and error rate through a full peak, before and after]

## Alarm
[ratio, threshold, where it pages]
```

## Anti-patterns

**Raising `nf_conntrack_max` first.** It is the cheapest change and the one that teaches
nothing. The table fills again at the next growth step, larger.

**Turning on `tcp_tw_recycle`.** It broke clients behind NAT and was removed from Linux in
4.12; advice that names it is out of date. `tcp_tw_reuse` applies to outgoing connections
only and still treats the symptom.

**Pooling without an idle timeout under the NAT's.** The NAT drops idle mappings silently;
the pool hands out a dead connection and the request times out — the original symptom,
from the fix.

**Blaming the partner.** A connect timeout from an exhausted NAT never reaches the
partner, so their logs show nothing. Check your own path's counters first.

## Reference files

- `references/counters.md` — read at steps 2 and 3: commands and metrics for conntrack,
  sockets and port ranges on a node, NAT and SNAT metrics on AWS, GCP and Azure, and the
  per-destination ceiling for each path.
- `references/dns-stalls.md` — read at step 4 when the shape is a 5-second stall: how
  ndots search expansion and the conntrack race each produce it, how to tell them apart,
  and the pod `dnsConfig`, trailing-dot and NodeLocal DNSCache fixes with their limits.
