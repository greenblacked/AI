---
paths:
  - "**/sysctl.d/*.conf"
  - "**/sysctl.conf"
---

# Connection ceilings in sysctl files

Finding the exhausted resource belongs to the `connection-exhaustion-hunt` skill; this rule is
only the guard that loads when a sysctl file is open.

- Do not set `net.ipv4.tcp_tw_recycle`. It broke clients behind NAT and Linux 4.12 removed it, so
  advice that names it is out of date, and on a current kernel the line is an error.
- Put a comment directly above every `net.netfilter.nf_conntrack_max`,
  `net.ipv4.ip_local_port_range` or `ip_conntrack_max` line that records the evidence for it: the
  counter, its value at failure and the limit it hit. sysctl files allow comments only on a line
  of their own, so a trailing note is read as part of the value.
- Treat a raised ceiling as the last fix, after client pooling, a private endpoint or more NAT
  addresses, and DNS. A bigger table fills again at the next growth step.
- On a Kubernetes node kube-proxy sets `nf_conntrack_max` itself when it starts, so a sysctl
  file alone is overwritten. Change kube-proxy's conntrack settings instead.
- Record each raised ceiling in `connection-ceiling-register.md`, the register template that
  ships beside this rule.
