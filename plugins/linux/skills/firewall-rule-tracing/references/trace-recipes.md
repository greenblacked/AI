# Trace recipes

## Contents

- Reading `nft monitor trace` output
- Narrowing a trace
- Counters as a diff
- iptables and legacy xtables tracing
- A Docker walk-through
- Rollback variants
- Common causes mapped to evidence

## Reading `nft monitor trace` output

Each packet gets a trace id, and every rule it is evaluated against produces a line with that id. Follow one id from top to bottom. The lines to look for:

| Line shows | Meaning |
| --- | --- |
| `trace id ... packet: iif "eth0" ... tcp dport 8080 tcp flags == syn` | The packet as the firewall saw it, including the interface and flags |
| `... rule ... (verdict continue)` | A rule matched with a non-terminal statement such as `counter` or `log` |
| `... rule ... (verdict accept)` | Accepted by this chain only; later chains at the same hook still run |
| `... rule ... (verdict drop)` | The packet is dead here; this is the rule to fix |
| `... policy drop` | No rule matched and the base chain policy dropped it |
| `... verdict jump` / `goto` | Evaluation entered a user chain, whose lines follow |

If the trace shows the packet reaching `input` and `accept` with no later line, the host firewall is not the cause; look at the socket (`ss -ltnp`), a listen backlog overflow (`nstat -az TcpExtListenOverflows`) or the application.

If the trace never shows the packet at all, either the match in the trace rule is wrong (wrong address family: `ip` rules do not see IPv6), or the packet is dropped before the prerouting hook, by an ingress or netdev rule or at the NIC. A reverse-path (rp_filter) drop looks different: the packet is traced through `prerouting` and no `input` or `forward` line follows, because the check runs in the routing lookup after that hook.

## Narrowing a trace

```bash
# only SYNs from one client, to one port
nft add rule inet tracedbg pre ip saddr 203.0.113.10 tcp dport 8080 tcp flags syn meta nftrace set 1
# bridged or interface-specific traffic
nft add rule inet tracedbg pre iifname "eth0" tcp dport 8080 meta nftrace set 1
# locally generated traffic needs the output hook
nft add chain inet tracedbg out '{ type filter hook output priority -301; }'
nft add rule inet tracedbg out tcp dport 443 meta nftrace set 1
```

Once the flag is set, every later chain traces the packet, so a narrow match here keeps the monitor readable on a busy host. `nft monitor trace` prints nothing for a packet whose trace flag was never set, which is why a typo in the match looks like a healthy firewall.

## Counters as a diff

```bash
nft list ruleset > /tmp/a.txt
# one test connection
nft list ruleset > /tmp/b.txt
diff /tmp/a.txt /tmp/b.txt
```

This works for rules that carry `counter`. To add one without editing the owner's file, insert a counting rule at the top of the suspect chain and note its handle for removal:

```bash
nft -e -a insert rule inet filter input tcp dport 8080 counter
nft delete rule inet filter input handle HANDLE
```

For iptables, `iptables -L INPUT -v -n -x` prints packet and byte counters on every rule; `iptables -Z INPUT` zeroes them between tests.

## iptables and legacy xtables tracing

```bash
iptables -t raw -A PREROUTING -p tcp --dport 8080 -j TRACE
iptables -t raw -A OUTPUT -p tcp --sport 8080 -j TRACE
```

On the nf_tables shim, watch with `xtables-monitor --trace`. On legacy xtables the trace goes to the kernel log through a logger module (`journalctl -k -f`); if nothing appears, check `sysctl net.netfilter.nf_log` and bind the IPv4 logger with `sysctl net.netfilter.nf_log.2=nf_log_ipv4`. Remove the rule with `-D` and the same arguments. A TRACE rule in the raw table runs before conntrack, so it sees every packet including those later marked invalid.

## A Docker walk-through

Symptom: a container publishes 8080, the host denies 8080 in `ufw`, and the port is still open.

1. `iptables -t nat -S DOCKER` shows a DNAT of host port 8080 to the container address.
2. Trace shows the packet in `prerouting` (nat) and then `forward`, never `input`: the host rule sits in `input`.
3. `iptables -S FORWARD` shows `DOCKER-USER` jumped to first, then `DOCKER-ISOLATION-STAGE-1`, then the accept for the bridge.
4. Fix in `DOCKER-USER`, matching the original destination port with conntrack because the destination is already the container's: `-m conntrack --ctorigdstport 8080 --ctdir ORIGINAL`. Docker does not flush `DOCKER-USER`, so the rule persists across daemon restarts, though it must still be saved by whatever restores your iptables at boot.

Other approaches (publish only on `127.0.0.1` with `-p 127.0.0.1:8080:8080`, or put the container on an internal network behind a proxy) remove the exposure instead of filtering it.

## Rollback variants

| Tool | Arm | Cancel |
| --- | --- | --- |
| systemd | `systemd-run --on-active=5min --unit=fw-rollback /usr/sbin/nft -f /root/fw-rollback.nft` | `systemctl stop fw-rollback.timer` |
| at | `echo '/usr/sbin/nft -f /root/fw-rollback.nft' \| at now + 5 minutes` | `atrm JOBID` (see `atq`) |
| firewalld | `firewall-cmd --add-port=8080/tcp --timeout=300` (rule expires itself) | `--remove-port` |
| iptables | `iptables-save > /root/ipt.before`; restore from the timer with `/usr/sbin/iptables-restore /root/ipt.before` (a file argument, since systemd-run starts no shell and a `<` redirect would not apply) | same as above |

The rollback file for one nft table is `table inet T`, then `delete table inet T`, then the saved `nft list table inet T` output. The first line makes the file valid when the table was removed in the meantime; the whole file applies atomically.

Use an absolute path to the binary in a timer or `at` job; their environment has no useful `PATH` guarantee.

## Common causes mapped to evidence

| Evidence | Likely cause |
| --- | --- |
| Rule counter zero, policy counter moving | Rule in wrong chain, hook or address family |
| Trace ends in an earlier table's `drop` | Another writer's chain at the same hook |
| `conntrack -S` `invalid` rising | Asymmetric path or restart mid-flow |
| Trace shows `accept`, still no reply | Application, listener address or return path |
| SYN arrives, SYN-ACK leaves by another interface | rp_filter or policy routing |
| Works until a firewall reload | Rules added at runtime and never persisted |
