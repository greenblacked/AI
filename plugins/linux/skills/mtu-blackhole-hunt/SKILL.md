---
name: mtu-blackhole-hunt
description: "Find a path MTU problem: \"small requests work but large ones hang\", \"connection stalls after the TLS ClientHello\", \"only breaks over the VPN or in the overlay network\", \"ssh logs in but hangs on ls\". The signature is a completed handshake and then large packets vanishing because ICMP fragmentation-needed is filtered, so path MTU discovery fails. Prove it with ping -M do -s N binary-searched to the largest payload that passes, tracepath, and a capture showing full-size segments retransmitted and never acknowledged. Compute tunnel overhead (WireGuard, IPsec, GRE, VXLAN, PPPoE) to match a cause. Use for any large-packet-only stall. Fix in order: allow ICMP type 3 code 4 and ICMPv6 packet-too-big, clamp MSS at the tunnel edge, then set MTU consistently end to end. Not for rules dropping all traffic (firewall-rule-tracing) or handshakes that fail outright (tls-handshake-debugging)."
allowed-tools: Bash(ip route get:*), Bash(ip -d link), Bash(ip -br link), Bash(ip -s link), Bash(ss -ti), Bash(nft list ruleset), Bash(iptables -S), Bash(iptables-save), Read, Glob, Grep
---

# MTU Blackhole Hunt

This skill is done when you can state the path MTU as a measured number, name the hop or encapsulation that sets it, show why discovery failed (the ICMP message that never arrived), and have a fix after which a full-size transfer completes from the original client.

The usual failure is lowering MTU everywhere until the symptom goes away. That hides the cause, costs throughput on paths that were fine, and breaks again the next time a tunnel is added. The measurement takes five minutes and names the number, which tells you which fix is the right one.

## Scope

Use for: handshakes that complete and transfers that stall, a service that works from the office and hangs over a VPN or inside an overlay, and sessions that hang when output grows.

Do not use for: a firewall rule that drops all traffic to a port (`firewall-rule-tracing`); a TLS handshake that itself fails with an alert or certificate error (`tls-handshake-debugging`).

## Workflow

### 1. Recognise the signature

Small packets pass and large ones do not. The TCP handshake (tiny packets) completes, a TLS ClientHello with a handful of cipher suites may pass, and the transfer stalls at the first full-size segment: the server certificate flight, an `ls` listing over ssh, a large POST body. Retries repeat the stall at the same point, and a smaller request on the same connection succeeds. It is deterministic per path, which separates it from loss.

The mechanism: the sender sets Don't Fragment and sends a segment that fits its own interface. A router with a smaller next-hop MTU is supposed to drop it and return ICMP type 3 code 4 (IPv4 fragmentation needed) or ICMPv6 type 2 (packet too big). If a firewall filters that message, the sender never learns, retransmits the same size, and the connection hangs. This is why a blanket "block all ICMP" rule produces this symptom.

### 2. Measure the path MTU

`ping -M do` forbids fragmentation. The payload plus 28 bytes (20 IP, 8 ICMP) is the packet size on IPv4; add 48 for IPv6 (`ping -6`: 40 IP, 8 ICMP).

```bash
ping -c 3 -M do -s 1472 HOST      # fits a 1500 MTU path exactly
ping -c 3 -M do -s 1400 HOST
```

Two failures look different and matter. `Frag needed and DF set (mtu = N)` or `message too long, mtu=N` means discovery works and tells you N; the cause is elsewhere in the path or on the host. Silence (100 percent loss at large sizes, success at small) is the blackhole. Binary-search the boundary rather than guessing; the loop in `references/measuring.md` does it and prints the largest passing payload. Then `tracepath -n HOST` shows the MTU it discovered hop by hop (`pmtu 1500`, falling at the constraining hop), and `ip route get HOST` shows a cached `mtu` once discovery has learned one.

Measure in both directions. The return path can differ, and the constraint may sit on the side you have no access to.

### 3. Confirm in a capture

```bash
tcpdump -ni IFACE -s0 'host HOST and (tcp or icmp or icmp6)'
tcpdump -ni IFACE 'icmp[icmptype] == 3 and icmp[icmpcode] == 4'      # IPv4 frag-needed arriving
tcpdump -ni IFACE 'icmp6 and ip6[40] == 2'                           # IPv6 packet-too-big arriving
```

Look for full-size data segments (length near MSS) leaving and retransmitted with exponential back-off while the peer never acknowledges them, with smaller segments and the ACKs of earlier data flowing normally, and no ICMP coming back. Capture on the far side too: offloading (TSO, GSO) makes a capture on the sending host show segments larger than the MTU, because the NIC splits them later; check `ethtool -k IFACE` and trust the capture taken beyond the sender. The ICMP filters above show whether the message is reaching this host at all; if it appears on the wire at the edge and not at the host, a local rule is eating it.

### 4. Match the number to a cause

A measured MTU that corresponds to no known overhead means a second constraint is hiding. Subtract from the underlay MTU (usually 1500):

| Encapsulation | Overhead (IPv4 underlay) | Resulting inner MTU |
| --- | --- | --- |
| WireGuard | 60 bytes (80 over IPv6) | 1440 (1420 for an IPv6-safe default) |
| GRE | 24 bytes | 1476 |
| IP-in-IP | 20 bytes | 1480 |
| VXLAN | 50 bytes (70 over IPv6) | 1450 |
| Geneve | 50 bytes plus options | 1450 or less |
| PPPoE | 8 bytes | 1492 |
| IPsec ESP, tunnel mode | roughly 50 to 73 bytes depending on cipher and padding; NAT-T adds 8 | about 1400 to 1450, measure it |

Treat the IPsec figure as a range to confirm by measurement. Container overlays stack: a pod inside VXLAN inside a VPN subtracts both. Read `references/measuring.md` for the arithmetic and for finding the interface that holds the wrong value (`ip -d link`).

### 5. Fix in this order

1. **Let discovery work.** Allow ICMP type 3 code 4 and ICMPv6 packet-too-big (and the other ICMPv6 types IPv6 needs to function) through every firewall on the path you control. nft: `ip protocol icmp icmp type destination-unreachable accept` and `icmpv6 type packet-too-big accept`. iptables: `-p icmp --icmp-type fragmentation-needed -j ACCEPT`. This fixes every flow, not only TCP, and costs nothing.
2. **Clamp MSS at the tunnel edge** where you cannot fix the filtering (a path you do not own) or for belt and braces. It rewrites the MSS option in SYN packets so TCP never builds oversize segments. iptables: `iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu`. nft, in a forward chain: `tcp flags syn tcp option maxseg size set rt mtu`. It covers TCP only; UDP (QUIC, DNS over large responses, VXLAN itself) is untouched.
3. **Set the interface MTU consistently end to end.** `ip link set dev wg0 mtu 1380` to test, then persist in the tool that owns the interface (the `MTU` line of a wg-quick config, netplan or NetworkManager settings, the CNI configuration for an overlay). Both ends of a tunnel need the same value, and a pod or container MTU must be at most the node MTU minus the overlay overhead.

If you control the endpoints and need a stopgap, `sysctl -w net.ipv4.tcp_mtu_probing=1` makes TCP probe for a working size after repeated failures (`2` probes always); it recovers slowly and is a mitigation, not the fix.

### 6. Check for the opposite error

Before lowering anything, list the MTU of every interface on the path (`ip -br link`, `ip -d link show`) and look for a mismatch the other way: a host set to 9000 on a switch port at 1500 produces the same stall, and the fix is to raise or align the path, not to clamp everyone. Jumbo frames work only where every device in the L2 domain agrees. Never apply a lower MTU fleet-wide on the strength of one broken path.

### 7. Verify

Repeat the failing action from the original client (the large download, the ssh `ls`, the TLS request), then re-run the largest passing `ping -M do` and confirm it matches the intended MTU minus 28. Record the before and after numbers.

## Output format

```markdown
## Signature
[What stalls, at which packet, what still works.]

## Measured path MTU
[Largest passing payload, packet size, direction, tracepath result.]

## Cause
[Which encapsulation or hop, with the overhead arithmetic, and which ICMP message was filtered where.]

## Fix
[Filtering change, MSS clamp, MTU setting: exact rule or value, and which host.]

## Proof
[Original action now completes; ping boundary after the change.]
```

## Anti-patterns

**Setting a low MTU everywhere.** It hides the cause and taxes every path.

**Blocking all ICMP.** Type 3 code 4 and ICMPv6 packet-too-big are required for TCP to work across any path with a smaller link.

**Clamping MSS and calling UDP fixed.** Clamping touches TCP SYNs only.

**Trusting a sender-side capture.** Offload makes it show segments that never go on the wire.

**Fixing one end of a tunnel.** Asymmetric MTU produces a path that works one way.

## Reference files

- `references/measuring.md` - read at steps 2 and 4: the binary-search loop, IPv4 and IPv6 size arithmetic, MSS from MTU, and finding which interface carries the wrong value.
