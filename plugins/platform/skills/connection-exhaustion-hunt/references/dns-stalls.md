# Five-second DNS stalls

Read this at step 4 when the failure shape is a stall of almost exactly five seconds. Five
seconds is the glibc resolver's default timeout: a lookup that loses one packet waits that
long before retrying. Two separate mechanisms produce the lost packet, and they are fixed
differently.

## Contents

- [Search expansion from ndots:5](#search-expansion-from-ndots5)
- [The conntrack race](#the-conntrack-race)
- [Telling them apart](#telling-them-apart)
- [Fixes and their limits](#fixes-and-their-limits)

## Search expansion from ndots:5

Kubernetes writes `options ndots:5` into each pod's `/etc/resolv.conf`, with a search list
of the pod's namespace domain, `svc.cluster.local`, `cluster.local` and the node's own
search domains. A name with fewer than five dots — `api.partner.example`, which has two —
is tried against every search domain before it is tried as written. Each attempt is an A
and an AAAA query, so one external lookup becomes eight or more queries, most of them
NXDOMAIN. That multiplies load on CoreDNS and the number of packets that can be lost, and
any single loss costs five seconds.

```bash
kubectl exec -n "$NS" "$POD" -- cat /etc/resolv.conf
```

```promql
sum(rate(coredns_dns_responses_total{rcode="NXDOMAIN"}[5m]))
  / sum(rate(coredns_dns_responses_total[5m]))
```

A high NXDOMAIN share — most responses — is search expansion.

## The conntrack race

glibc sends the A and AAAA queries in parallel from the same UDP socket. Both packets
create the same conntrack entry, and when they are processed on different CPUs at the same
moment one insertion can fail and the packet is dropped. The resolver then waits its five
seconds. The node's `insert_failed` counter rises in step with the stalls. Kernel changes
have narrowed the race; check the counter rather than assuming the node's kernel is immune.

## Telling them apart

| Evidence | Search expansion | conntrack race |
| --- | --- | --- |
| NXDOMAIN share at CoreDNS | High | Normal |
| `insert_failed` on the client's node | Flat | Rises with the stalls |
| Affects fully qualified names with a trailing dot | No | Yes |

Both can be present at once; search expansion makes the race more likely by multiplying
the queries.

## Fixes and their limits

**NodeLocal DNSCache.** A caching agent on every node, listening on a link-local address
(169.254.20.10 by convention). Lookups stay on the node, its traffic is excluded from
conntrack, and it talks to CoreDNS over TCP. It fixes the race and cuts the load from
search expansion. Under kube-proxy in iptables mode it can intercept the existing cluster
DNS address; under IPVS mode pods must be pointed at the link-local address through the
kubelet's cluster DNS setting. A default-deny NetworkPolicy must allow egress to that
address, or the fix breaks every lookup.

**Fully qualified names.** Write external hosts with a trailing dot (`api.partner.example.`)
in configuration so no search domain is tried. Some HTTP clients pass the trailing dot into
the TLS server name or `Host` header, which can fail certificate matching or virtual-host
routing; test it per client.

**Lower ndots per pod.**

```yaml
spec:
  dnsConfig:
    options:
      - name: ndots
        value: "2"
```

Short in-cluster names such as `orders.payments` still resolve through the search list;
names with at least as many dots as the setting are tried as written first, costing one
extra query when they are in-cluster names such as `orders.payments.svc`.

**Resolver options.** `single-request-reopen` in `dnsConfig.options` changes how glibc
handles the paired A and AAAA queries and is a common mitigation for the race. musl
ignores it, so it does nothing on Alpine-based images.

**CoreDNS `autopath`.** Answers search-expanded queries server-side in one round trip, at
the cost of CoreDNS watching all pods. Consider it only when per-pod changes are not
possible.
