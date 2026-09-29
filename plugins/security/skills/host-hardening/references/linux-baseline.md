# Linux baseline

## Contents

- [Choosing and citing a baseline](#choosing-and-citing-a-baseline)
- [Controls that apply almost everywhere](#controls-that-apply-almost-everywhere)
- [Controls that break a specific role](#controls-that-break-a-specific-role)
- [Kernel and sysctl](#kernel-and-sysctl)
- [Filesystem and mounts](#filesystem-and-mounts)
- [Recording an accepted finding](#recording-an-accepted-finding)

## Choosing and citing a baseline

A finding is only a finding against something. Pick one of these and name its version in the output:

- **CIS Distribution Independent Linux** or the distro-specific benchmark — the common default, with Level 1 (broadly safe) and Level 2 (defence in depth, higher breakage risk).
- **NIST SP 800-123** (server security) and **SP 800-53** control families when the ask is compliance-shaped.
- **A vendor baseline** — the cloud provider's hardened image guide, the database vendor's hardening note — which is usually closer to the role than a general benchmark.
- **A short explicit list** the requester signed off, when a full benchmark is disproportionate for a single-purpose host.

Map each finding to a control identifier so the auditor and the engineer are arguing about the same thing. A finding with no identifier is a preference.

## Controls that apply almost everywhere

| Control | Check | Typical change |
| --- | --- | --- |
| Only one uid 0 | `awk -F: '$3==0 {print $1}' /etc/passwd` | Lock or remove extra root-equivalent accounts |
| No empty passwords | `awk -F: '$2=="" {print $1}' /etc/shadow` | Lock the account or set a password |
| SSH root login controlled | `sshd -T \| grep permitrootlogin` | `prohibit-password` or `no`, per baseline |
| Password auth off where keys work | `sshd -T \| grep passwordauthentication` | `no`, after keys are proven |
| Unused services disabled | `systemctl list-unit-files --state=enabled` | Disable, then confirm the consumer |
| Listening ports minimised | `ss -tulpn` | Bind to management/localhost or disable |
| Patches current | distro tool, `needrestart`/`dnf needs-restarting` | Patch and reboot for kernel/libc |
| Audit enabled | `systemctl status auditd`, `auditctl -l` | Load rules at boot, verify after restart |
| Logs shipped off-host | log agent status | Ship, and confirm the destination receives |
| Host firewall default deny | `nft list ruleset` / `iptables -S` | Deny inbound, allow the management path |
| No world-writable files | `find / -xdev -type f -perm -0002` | Fix mode or record why |
| No unexpected SUID | `find / -xdev -perm -4000 -o -perm -2000` | Remove the bit or record the package |

## Controls that break a specific role

Applying a general benchmark without reading this table is how a hardening change causes an outage.

| Role | Control that breaks it | Why |
| --- | --- | --- |
| Router or gateway | `net.ipv4.ip_forward=0`, disabling redirects | Forwarding is the function; turning it off stops routing |
| Container host | Restricting user namespaces, disabling overlay modules, `/tmp` `noexec` | Breaks the runtime or its storage driver |
| Kubernetes node | Tightening the kubelet's ports, disabling `br_netfilter`, sysctl conflicts | The CNI and kubelet need forwarding and bridge netfilter |
| Database host | `noexec` on data mounts, restrictive `vm.overcommit`, hugepage changes | Storage engines and memory mapping depend on them |
| Jump host | Disabling agent forwarding without replacing it | Users lose the workflow and route around the control |
| Anything with a legacy app | `noexec` on `/tmp`, closing a hardcoded port | The app runs from `/tmp` or dials a fixed port |
| Host with a console that is shared | Disabling magic SysRq, restricting single-user | Removes the recovery path the operator needs |

For each control that does not apply, write the reason rather than leaving the row blank. A blank row reads as "not checked".

## Kernel and sysctl

Put changes in a drop-in file (`/etc/sysctl.d/99-hardening.conf`) so the diff is reviewable and the revert is a file delete.

```text
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.tcp_syncookies = 1
net.ipv6.conf.all.accept_ra = 0
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 1
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
```

Verify the effective value, not the file:

```bash
sudo sysctl --system
sysctl net.ipv4.tcp_syncookies kernel.kptr_restrict
```

Two cautions. A malformed drop-in can stop a service or a boot from completing, so change kernel parameters on the canary first. And a value that a kernel module or a container runtime sets later will override yours, which is why the verification is at runtime rather than at boot only.

## Filesystem and mounts

```bash
find / -xdev -type f -perm -0002 -ls                 # world-writable files
find / -xdev -type d -perm -0002 -ls                 # world-writable directories
find / -xdev \( -perm -4000 -o -perm -2000 \) -ls    # SUID and SGID
```

Mount hardening, applied only where the role tolerates it:

```text
tmpfs /tmp     tmpfs rw,nosuid,nodev,noexec,relatime,size=2G 0 0
tmpfs /dev/shm tmpfs rw,nosuid,nodev,noexec,relatime,size=1G 0 0
```

A sticky bit on a shared writable directory limits deletion to the owner; it does not make the directory safe to write to.

## Recording an accepted finding

An accepted finding is not a skipped one. Record four things, or the next scan re-raises it with no context:

1. The control identifier and what it asks for.
2. The current state and the evidence that showed it.
3. Why it is accepted — the role, the compensating control, the platform already enforcing it elsewhere.
4. Who accepted it and when, with a review date.

A finding with a reason and an owner is a decision. A finding with neither is an omission, and the next auditor will treat it as one.
