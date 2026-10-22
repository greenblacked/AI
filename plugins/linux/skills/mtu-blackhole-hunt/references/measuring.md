# Measuring path MTU

## Contents

- Binary search for the largest passing payload
- Size arithmetic
- Reading the result
- Finding the interface with the wrong MTU
- Persisting an MTU by tool

## Binary search for the largest passing payload

Save this as a script (`bash probe.sh`) rather than pasting it into a login shell: the `exit 1` lines would close your session.

```bash
dst=HOST
lo=0; hi=1473                       # hi is assumed to fail; raise it on a jumbo path
# the search is meaningless unless a small payload passes: an ICMP-filtering or unreachable host fails every probe
ping -c 2 -W 1 -n -M do -s 0 "$dst" >/dev/null 2>&1 || { echo "no reply to a minimal ping: cannot measure (ICMP filtered, host down or name wrong)" >&2; exit 1; }
ping -c 2 -W 1 -n -M do -s "$hi" "$dst" >/dev/null 2>&1 && { echo "payload $hi passes: raise hi and rerun" >&2; exit 1; }
while [ $((hi - lo)) -gt 1 ]; do
  mid=$(( (lo + hi) / 2 ))
  if ping -c 2 -W 1 -n -M do -s "$mid" "$dst" >/dev/null 2>&1; then lo=$mid; else hi=$mid; fi
done
echo "largest payload: $lo  packet size: $((lo + 28))"
```

For IPv6 add `-6` to the ping and use `$((lo + 48))`. Run it at a quiet moment: packet loss on a lossy path makes a passing size look failing, so repeat the final two sizes with `-c 10`. A local `message too long` error means the payload exceeds your own interface MTU and counts as a fail in the loop, which is what you want.

## Size arithmetic

| Quantity | Formula |
| --- | --- |
| IPv4 packet size from ping payload | payload + 8 (ICMP) + 20 (IP) |
| IPv6 packet size from ping payload | payload + 8 (ICMP) + 40 (IP) |
| TCP MSS for a given MTU, IPv4 | MTU - 40 |
| TCP MSS for a given MTU, IPv6 | MTU - 60 |
| Inner MTU through a tunnel | underlay MTU - encapsulation overhead |

Example: payload 1372 passes and 1373 fails on IPv4. Packet size 1400. With a 1500 underlay that is 100 bytes of overhead, more than a single WireGuard (60), GRE (24), VXLAN (50) or PPPoE (8) layer adds. Two things match 1400: a single IPsec tunnel (ESP in tunnel mode, with NAT-T, at the low end of the "about 1400 to 1450" range in `SKILL.md`) or a tunnel somebody configured at MTU 1400. Check the interface MTU and the IPsec policy before assuming a stack. Stacked layers have to add up to 100 to explain it: WireGuard plus VXLAN is 60 + 50 = 110 and would give 1390, so it is not this path, and neither is PPPoE under WireGuard (8 + 60 = 68, giving 1432).

## Reading the result

| Observation | Meaning |
| --- | --- |
| Large pings return `Frag needed ... mtu = N` | Discovery works; set the sender or tunnel to N |
| Large pings time out, small ones pass | Blackhole: the ICMP message is filtered somewhere |
| Ping boundary and TCP stall point disagree | TCP is using an MSS from an option you can read in the SYN; capture it |
| `tracepath` stops at a hop with no `pmtu` change but the ping boundary is lower | The constraint is beyond that hop or ICMP is filtered after it |
| Works one direction, hangs the other | Asymmetric MTU or return path filters the ICMP |

To see the MSS each side advertised, capture the SYN and SYN-ACK: `tcpdump -nvi IFACE 'tcp[tcpflags] & tcp-syn != 0 and host HOST'` prints `mss N` in the options. An advertised MSS above MTU - 40 on a constrained path means no clamp is in place.

## Finding the interface with the wrong MTU

```bash
ip -br link                         # name, state, MAC; add -d for details
ip -d link show wg0                 # mtu, and for vxlan the underlying device and port
ip route get 10.20.0.5              # which interface and which cached mtu applies
ip -s link show eth0                # errors and drops that mimic a blackhole
```

Compare the MTU on both ends of each link and on each virtual device (bridge, veth, vxlan, wg) along the path. A bridge takes the lowest MTU of its ports; a veth pair needs both sides set. For containers, read the MTU inside the namespace as well (`nsenter -t PID -n ip link`, or `ip link` inside the container).

## Persisting an MTU by tool

| Tool | Where the value lives |
| --- | --- |
| wg-quick | `MTU = 1380` in the `[Interface]` section, then restart the interface |
| netplan | `mtu: 1380` under the interface |
| NetworkManager | `nmcli connection modify NAME 802-3-ethernet.mtu 1380` (or the connection type's own setting) |
| systemd-networkd | `MTUBytes=1380` in the `[Link]` section of the `.network` or `.link` file |
| Container networking | The CNI or network driver option, not `ip link` inside a pod; changes apply to new pods |

A value set with `ip link set` is lost at the next restart of the interface or the host. Confirm persistence by restarting the interface in a window where that is safe, not by reading the file.
