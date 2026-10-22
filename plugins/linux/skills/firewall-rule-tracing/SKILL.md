---
name: firewall-rule-tracing
description: "Find where a Linux firewall drops traffic: \"connection times out but the port is open\", \"nftables rule not matching\", \"Docker bypasses my iptables rules\", \"ufw and firewalld both installed\". Identify the framework really in force first (nft list ruleset is the truth; iptables may be the nft shim; firewalld, ufw, Docker and kube-proxy all inject rules), then trace one packet instead of reading rules: a meta nftrace set 1 rule with nft monitor trace, or iptables -t raw -j TRACE, plus counters read before and after a test connection. Check hook order and priorities, policies, conntrack state, rp_filter and DOCKER-USER. Change with a timed rollback and a second session. Use for any silent drop. Not for writing a baseline (host-hardening), a rule that already cut you off (linux-lockout-recovery), MikroTik (routeros-config) or large packets only (mtu-blackhole-hunt)."
allowed-tools: Bash(nft list ruleset), Bash(nft -a list ruleset), Bash(iptables -S), Bash(iptables -L -n -v), Bash(iptables-save), Bash(ip6tables-save), Bash(conntrack -S), Bash(ss -ltnp), Bash(ss -s), Bash(ip route get:*), Bash(ip -br addr), Bash(firewall-cmd --list-all), Bash(firewall-cmd --get-active-zones), Bash(ufw status verbose), Read, Glob, Grep
---

# Firewall Rule Tracing

This skill is done when you can name the one chain, rule or policy that dropped the packet, show its counter or trace line, and have a change that makes a fresh test connection pass while a second session stayed open and a timed rollback was armed.

The usual failure is reading rules instead of watching a packet. A Linux host can hold rules from four different writers at once (a distribution firewall, a container runtime, an orchestrator and a hand-written file), spread over several tables that all hook the same point, and a packet is judged by every one of them. Reading the file you edited tells you what you meant; a trace tells you what happened. The second failure is changing the live ruleset with no way back.

## Scope

Use for: a connection that times out or is refused although the service listens, a rule that never seems to match, published container ports that ignore host rules, and two firewall managers fighting.

Do not use for: choosing what a hardened baseline contains (`host-hardening`); a rule that has already locked you out (`linux-lockout-recovery`); a MikroTik device (`routeros-config`); a path where only large packets fail (`mtu-blackhole-hunt`).

## Workflow

### 1. Classify the symptom before touching rules

From the client: `connection timed out` means packets are dropped silently somewhere (a `drop` rule, a policy, rp_filter, a cloud security group). `connection refused` means a reset came back: a `reject` rule or no listener. On the server, prove the listener first.

```bash
ss -ltnp 'sport = :8080'          # bound address matters: 127.0.0.1 is not reachable from outside
ip route get CLIENT_IP            # which interface the reply leaves by; asymmetric paths break rp_filter and conntrack
```

If the listener is on the right address and a capture on the server (`tcpdump -ni IFACE 'tcp port 8080'`) shows the SYN arriving with no SYN-ACK leaving, the host is dropping it. If the SYN never arrives, the problem is upstream (security group, router, another firewall) and nothing here will find it.

### 2. Establish which framework is in force

```bash
nft list tables                    # every table from every writer
iptables -V                        # "(nf_tables)" means the shim: rules live in nft; "(legacy)" means the old xtables tables
update-alternatives --display iptables
systemctl is-active nftables firewalld ufw docker
```

`nft list ruleset` is the ground truth for everything the nf_tables backend holds, including rules added through `iptables-nft`. Legacy xtables rules are invisible to it: if `iptables -V` says legacy, read `iptables-save` and `ip6tables-save` as well, and be aware that both backends can be loaded at once, each seeing the packet. Note which tables belong to whom: `firewalld` owns `inet firewalld`, Docker owns chains such as `DOCKER`, `DOCKER-USER` and `DOCKER-ISOLATION-STAGE-*`, kube-proxy owns `KUBE-*` chains. Do not edit another writer's chains; add your rule where that writer provides a hook (step 6).

Two managers means one of them is stale. Pick the one the host is meant to use, and do not flush the other's rules by hand, because its next reload restores them.

### 3. Count before you trace

Counters are the cheapest evidence. Rules show counters only if they carry the `counter` statement (nft) or always in `iptables -L -v -n -x` output.

```bash
nft list ruleset > /root/ruleset.before.nft          # also the rollback source
iptables -L -v -n -x --line-numbers
# make one test connection from the client, then list again and diff the counters
```

A rule whose counter did not move did not see the packet: it is in the wrong chain or table, hooked at the wrong point, shadowed by an earlier verdict, or the match is wrong (interface name, address family, `tcp dport` versus `sport`). The policy counter on a base chain, where shown, tells you the packet fell off the end.

### 4. Trace one packet

```bash
nft add table inet tracedbg
nft add chain inet tracedbg pre '{ type filter hook prerouting priority -301; }'
nft add rule inet tracedbg pre ip saddr CLIENT_IP tcp dport 8080 meta nftrace set 1
nft monitor trace
```

Priority -301 runs before the raw hook (-300), so the trace flag is set before any other rule sees the packet. Add a matching chain on `hook output` for locally generated traffic. Each line of `nft monitor trace` names the table, chain, rule and verdict the packet met, in order, ending in `verdict drop` or `verdict accept` at a named rule. For iptables-nft the equivalent monitor is `xtables-monitor --trace`; for legacy xtables use `iptables -t raw -A PREROUTING -p tcp --dport 8080 -j TRACE` and read the kernel log (some kernels also need the `nf_log_ipv4` logger bound via `sysctl net.netfilter.nf_log.2=nf_log_ipv4`). Read `references/trace-recipes.md` for how to read the output, trace by conntrack state, and a Docker example.

Delete the trace table when done: `nft delete table inet tracedbg`. A trace rule left in place costs every packet.

### 5. Check what the trace cannot show

Not every drop is a rule.

- **Hook order and priority.** A packet visits every base chain at a hook in priority order: raw (-300), mangle (-150), dstnat (-100), filter (0), security (50), srcnat (100). An `accept` in one chain ends only that chain; a later chain at the same hook, in another table, can still drop it. Default policy `drop` on a base chain is a verdict too.
- **Conntrack.** `ct state invalid drop` is common and correct; asymmetric routing and a firewall restart mid-connection produce invalid packets. `conntrack -S` shows `invalid` and `drop` counts, `conntrack -L -d SERVER_IP` shows entries and their state. A full table drops new flows (kernel log: `nf_conntrack: table full, dropping packet`).
- **Reverse path filter.** `sysctl net.ipv4.conf.all.rp_filter net.ipv4.conf.IFACE.rp_filter`: the higher of the `all` and per-interface values wins, and 1 (strict) drops packets that would not be routed back out the same interface. Set `net.ipv4.conf.all.log_martians=1` temporarily to see `martian source` lines in the kernel log.
- **Forwarding.** For routed or NATed traffic, `sysctl net.ipv4.ip_forward` and the `forward` hook apply, not `input`.

### 6. Containers and managers

Published container ports are DNATed in `prerouting` and then travel the `forward` hook, never `input`, so host `INPUT` rules and `ufw allow/deny` on the host do not govern them. Docker consults `DOCKER-USER` first in `FORWARD`; put your restrictions there and match the original destination, because the destination is already rewritten by then: `iptables -I DOCKER-USER -i eth0 ! -s 10.0.0.0/8 -p tcp -m conntrack --ctorigdstport 8080 --ctdir ORIGINAL -j DROP`. Check the `DOCKER-USER` rule before concluding the host firewall is broken. With firewalld, add runtime rules with a timeout to test them (`firewall-cmd --add-port=8080/tcp --timeout=300`) and persist with `--runtime-to-permanent` only after the test.

### 7. Change with a safety net

```bash
snap=$(mktemp /root/fw-snap.XXXXXX)    # under /root, never a predictable /tmp path that root will later load
nft list table inet filter > "$snap"
if test -s "$snap"; then
  { echo 'table inet filter'; echo 'delete table inet filter'; cat "$snap"; } > /root/fw-rollback.nft
  systemd-run --on-active=5min --unit=fw-rollback /usr/sbin/nft -f /root/fw-rollback.nft &&
  nft -c -f /root/new-rules.nft &&     # syntax and semantic check, changes nothing
  nft -f /root/new-rules.nft           # atomic: the whole file applies or none of it
else
  echo 'snapshot empty: stop, nothing applied and no rollback armed' >&2
fi
```

Replace `inet filter` with the table you are changing. The `if test -s` guard writes the rollback file, arms the timer and only then applies the new rules, all inside the branch: an empty snapshot would turn the rollback into deleting the table and loading nothing, so on the `else` branch nothing is applied; fix the save and run the block again. A failed `systemd-run` or check also stops before the change. Restoring one table is deliberate: `nft flush ruleset` also removes the tables Docker and firewalld own, and they do not come back until restarted. Then test a fresh connection from a second session, and only when it passes cancel the rollback (`systemctl stop fw-rollback.timer`) and persist: write your table to the file the distribution loads (`/etc/nftables.conf` on Debian family, `/etc/sysconfig/nftables.conf` on RHEL family), or use the manager's own save. `at now + 5 minutes` with the same restore command works where `at` is installed. Read `references/trace-recipes.md` for rollback variants.

## Output format

```markdown
## Framework in force
[nft or legacy, which managers are active, which tables are whose.]

## Drop point
[Table, chain, rule or policy, with the trace line or counter before and after.]

## Fix
[The rule or setting changed, in the writer's own chain; nft -c result.]

## Proof
[Fresh connection from the original client; rollback armed then cancelled; persisted where.]
```

## Anti-patterns

**Reading the config file as the live state.** The file is one writer's intent; `nft list ruleset` is the result.

**Flushing to start clean.** It deletes other writers' tables and the rules your services depend on.

**Appending a rule after a catch-all drop.** It sits below the verdict and its counter stays at zero.

**Saving before testing.** A persisted bad rule survives the reboot that would have cleared it.

**Testing from the session you are changing over.** A failure then cuts the only way to roll back.

## Reference files

- `references/trace-recipes.md` - read at step 4 and step 7: reading trace output, tracing by state or interface, iptables TRACE specifics, a Docker walk-through and rollback variants.
