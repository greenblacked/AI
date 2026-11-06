# Connection ceiling register

One row per raised network ceiling. A ceiling raised without a row is a guess that will
need debugging again at the next growth step. Delete the guidance in brackets.

## Ceilings

| Date | Layer | Setting | Old | New | Counter at failure | Limit it hit | Window | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [date] | [conntrack / local ports / NAT / DNS] | [e.g. `net.netfilter.nf_conntrack_max`] | [value] | [value] | [counter and its value] | [the limit] | [time range] | [person or team] |

## Why a ceiling and not the client

For each row, say which earlier fix was ruled out and what showed it.

| Fix in order | Tried or ruled out | Evidence |
| --- | --- | --- |
| Client reuse (pooling, keepalive, idle timeout below the NAT's) | [tried / ruled out] | [what showed it] |
| Private endpoint or more NAT addresses | [tried / ruled out] | [what showed it] |
| DNS (NodeLocal DNSCache, FQDNs, lower `ndots`) | [tried / ruled out] | [what showed it] |

## Alarm

| Ratio | Threshold | Where it pages |
| --- | --- | --- |
| [e.g. `nf_conntrack_count` over `nf_conntrack_max`] | [e.g. 0.75] | [channel or rota] |

## Review date

[When this row is checked against the counter again, and who does it.]
