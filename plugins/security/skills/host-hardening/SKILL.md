---
name: host-hardening
description: "Audit or harden a Linux or Unix host — a VM, a bare-metal server or a bastion — against a named baseline: preserve a second way in before touching sshd or sudo, export the config either side, change one class at a time on a canary host, and verify over a path you did not edit. Covers SSH and keys, sudo and users, auditd and logging, sysctl, service and port minimisation, filesystem permissions, patch policy, and CIS/NIST mapping. Use when someone says \"harden the ubuntu hosts\", \"lock down ssh on the bastion\", \"the CIS scan has forty findings\", \"we still allow password login\", or \"we need auditd evidence by friday\". Not for a container image (image-hardening), a MikroTik or network device (routeros-config), the Ansible or Terraform that applies it (code-scaffold, iac-review), IAM permissions (access-review), a leaked key (secret-rotation), or a live compromise."
allowed-tools: "Bash(ssh:*), Bash(sudo:*), Bash(sshd:*), Bash(systemctl:*), Bash(sysctl:*), Bash(auditctl:*), Bash(ss:*), Bash(find:*), Read, Grep, Glob"
---

# Host Hardening

This is finished when the host matches a named baseline, every change was revertible on its own, you proved you can still get in over a path you did not edit, and the remaining findings are recorded with the reason each was accepted.

The dominant risk in this job is not the attacker. It is locking yourself and everyone else out: an `sshd_config` that fails to parse, a firewall rule applied before the accept for your own session, a `sudoers` file with a syntax error that disables `sudo` entirely, a kernel parameter that makes the box unbootable. All four take a working host to an unreachable one in a single command, and none of them fails loudly first. The second risk is treating a benchmark as a checklist and applying it wholesale: a hardening guide written for a general-purpose server will happily turn off the service this host exists to run. The order below exists to make both failure modes survivable rather than to make the list shorter.

## Scope

Use for: a new host before it takes traffic; an existing fleet against a benchmark; an audit that wants evidence (CIS, NIST SP 800-123, a vendor's own baseline); a specific control someone asked for — sshd, sudo, sysctl, auditd, services, permissions; or a host that failed a scan and needs the findings worked.

Do not use for: a container image, which is `image-hardening`; a MikroTik or other network device, which is `routeros-config`; writing the Ansible, Chef or cloud-init that applies the baseline, which is `code-scaffold`, or reviewing that change, which is `iac-review`; who holds which cloud or cluster permission, which is `access-review`; a credential that has leaked, which is `secret-rotation`; or a host that is compromised right now, where containment comes before hardening and destroying evidence by rebooting is the mistake.

## Hard gates

1. A second way in is proven before anything is changed: a second session already open, an out-of-band console, or a serial/IPMI path you have actually tested. "It should work" is not a second way in.
2. The current state is exported to a file you can restore from — the full `sshd_config`, `sudoers`, `sysctl -a`, the service list, the firewall ruleset — before the first edit.
3. One class of change at a time, on one canary host, with the rest of the fleet untouched until the canary has run production traffic for a full cycle.
4. The rollback command is written down before the change, not reconstructed during the incident. For sshd and sudoers this is a saved copy plus the exact restore command.
5. Every change is verified over a connection opened after it, not from the session that made it.
6. The baseline and the distro version are named. A finding is judged against that baseline, and a control that does not apply is recorded as accepted with a reason, not silently skipped.

## Workflow

### 1. Declare the mode and the baseline

Two modes, different deliverables. Say which is active in the first line.

| Mode | Trigger | Deliverable |
| --- | --- | --- |
| **Audit** | An existing host or fleet, a scan result, or a compliance request | Ranked findings with evidence, each with the control it maps to — do not change the host yet |
| **Harden** | A new host, or a finding set that has been agreed | The applied changes, each with its revert step and its verification |

Name the baseline before either: a CIS benchmark level, a vendor baseline, or a short explicit list the requester signed off. "Best practice" is not a baseline, and without one every finding becomes an argument.

### 2. Preserve access, then inventory

Before hardening, capture what you are about to change and prove the escape hatch.

```bash
sudo sshd -T > /root/sshd.effective.before      # the effective config, not the file
sudo cp -a /etc/ssh/sshd_config /root/sshd_config.bak
sudo cp -a /etc/sudoers /root/sudoers.bak
sudo visudo -c                                  # must pass before you edit
sudo sysctl -a > /root/sysctl.before
sudo ss -tulpn > /root/listening.before
```

Keep a root shell open, or a `tmux`/`screen` session on the console, for the whole of an sshd or firewall change. A session that survives your own rule change is the only proof that the rule did not cut you off.

### 3. Patch and package policy

An unpatched host is not hardened, whatever else is configured. This is also the change most likely to restart a service, so it goes first on the canary.

- Define the patch cadence and the reboot policy: kernel and libc updates need a reboot, so "patched" means "rebooted" for those.
- Enable automatic security updates where the role allows, and read what they will restart. `unattended-upgrades` on Debian/Ubuntu, `dnf-automatic` on RHEL-family.
- Remove or lock unused package managers and compilers on a host that only runs a service. A build toolchain on a production host is attack surface and a way to compile the next stage.
- Keep the package list as an artifact so drift is visible.

### 4. Users, keys, sudo and SSH

The class where a mistake costs the most access. Change it on the canary and keep the second session open.

- **Accounts.** Remove or lock accounts that are not needed; a service account gets a locked password and no shell (`/usr/sbin/nologin`). Audit `uid 0` — there should be exactly one.
- **SSH.** Disable password and keyboard-interactive auth once keys work; disable direct root login; restrict `AllowUsers`/`AllowGroups`; set `MaxAuthTries`, `LoginGraceTime`, `ClientAliveInterval`; decide `PermitRootLogin` and `X11Forwarding` deliberately. Always `sshd -t` before `systemctl reload sshd`, and never close the old session until a new one succeeds.
- **Keys.** Remove weak or unused key types, enforce a passphrase or an agent policy, and rotate keys with the same care as any credential. A key in `authorized_keys` is standing access.
- **sudo.** Prefer group-based rules over per-user; require a password unless the role genuinely needs `NOPASSWD`; never edit `sudoers` with a plain editor — use `visudo`, which validates before it saves. Log sudo separately and review it.

`references/ssh-and-access.md` has the directives that matter, the `sshd -T` verification loop, and the safe change sequence for a fleet.

### 5. Kernel and sysctl

Most sysctl findings are about network stack behaviour and information exposure. Change them in a drop-in file rather than editing `/etc/sysctl.conf`, so the intent is reviewable and reversible.

- Network: disable IP forwarding and source routing on a host that is not a router; enable SYN cookies; ignore ICMP redirects; disable IPv6 router advertisements where IPv6 is not used.
- Memory and crash: restrict `dmesg` to root, disable the magic SysRq where the console is not trusted, set `kernel.kptr_restrict` and `kernel.dmesg_restrict`.
- Apply with `sysctl --system`, verify with `sysctl -a`, and know that a typo in a drop-in can prevent a service or a boot from coming up cleanly.

`references/linux-baseline.md` maps the common controls to CIS and NIST, including the ones that break a router, a container host or a Kubernetes node if applied blindly.

### 6. Minimise services and ports

A smaller host is a smaller target, and this step is measured rather than argued.

```bash
sudo systemctl --failed
sudo systemctl list-unit-files --state=enabled
sudo ss -tulpn
```

- Disable every listening service the role does not need. If you cannot say who uses it, find out before disabling, not after.
- Bind management services to the management interface or to localhost, not to the world.
- Remove or firewall default ports that exist for convenience — a database, a metrics endpoint, an admin UI.
- Re-check the listening set after every change; a service that restarts and reopens a port is a finding that looks fixed.

### 7. Filesystem permissions and mounts

- Find world-writable files and directories and either fix the mode or record why they are needed: `find / -xdev -type f -perm -0002`.
- Ensure no unexpected SUID/SGID binaries: `find / -xdev -perm -4000 -o -perm -2000`.
- Set a default `umask` for services and shells.
- Mount `/tmp`, `/var/tmp` and `/dev/shm` with `noexec`, `nosuid` and `nodev` where the applications tolerate it, and check before enforcing.
- Protect the bootloader and the root filesystem from casual modification per the baseline.

### 8. Audit and logging

Hardening without a record of what happened is incomplete, and this is the control auditors ask for evidence of.

- Enable `auditd` with rules for authentication, privilege escalation, and the sensitive files the baseline names; verify the rules load at boot.
- Ship logs off the host. A log that lives only on the compromised host is not evidence.
- Set retention long enough to satisfy the baseline and the incident window, and confirm rotation is not silently dropping the interesting events.
- Decide what pages a human versus what is only retained, so the host's logs do not become another ignored feed.

`references/audit-and-detection.md` has the auditd rule sets, the log-shipping failure modes, and the drift checks that catch a host reverting.

### 9. Host firewall

The host firewall is the last line when a network control is misconfigured, and it is also where a careless change cuts your own session.

- Write the rules so the management path (your SSH source, the console) is accepted before the default deny, and keep the second session open while you apply them.
- Default deny inbound, allow established outbound, and name the ports that are genuinely needed.
- Persist the ruleset and verify it survives a reboot on the canary.
- Prefer the platform's own mechanism (security groups, a managed firewall) for fleet-wide rules, and keep the host firewall for the residual.

### 10. Verify, record and watch for drift

Close the job with evidence, or it reopens the moment someone reboots.

- Re-run the baseline scanner and compare against the first run. Findings that moved to accepted need a reason; findings still open need an owner.
- Verify access over a new session, a reboot on the canary, and the log pipeline.
- Record the drift controls: configuration management, a scheduled re-scan, and an alert when a critical file changes.
- Hand the fleet rollout its own change window and rollback, rather than treating the canary result as permission to change everything at once.

## Output format

```markdown
## Mode and baseline
[Audit or harden, and the named baseline with its version.]

## Access preserved
[The second way in, proven, and the exported state files.]

## Findings
[Ranked: control, current state, evidence, change, revert step. Accepted findings carry a reason.]

## Applied on the canary
[What changed, in what order, and the verification over a connection opened after it.]

## Verification
[Scanner re-run diff, new-session test, reboot test, log pipeline confirmed.]

## Fleet rollout
[Change window, order, and the abort condition.]

## Drift controls
[What will catch this host reverting, and who is paged.]
```

## Anti-patterns

**Editing sshd or sudoers in the session you are relying on.** The change reloads, the daemon refuses the config or the rule is wrong, and the only session closes. Keep a second session or a console, and run `sshd -t` / `visudo -c` first.

**Applying a benchmark wholesale.** A general-purpose baseline disables services the host needs, or turns off IP forwarding on the router, or enables a control the platform already enforces elsewhere. Map each control to this host's role and record the ones that do not apply.

**Hardening before patching.** A perfectly configured host with a known kernel exploit is not hardened. Patch and reboot first.

**Disabling a service before knowing who uses it.** The listener goes quiet, and a dependency fails an hour later with no obvious cause. Find the consumer, then disable.

**A hardening change with no revert step.** The change is correct today and wrong after the next deploy; without the recorded revert, the next person either leaves it or guesses.

**Rebooting or reimaging a suspected compromise.** Hardening and containment are opposite orders. If the host may be compromised, preserve evidence and contain first; a reboot destroys the volatile state the investigation needs.

**Leaving the audit rules unverified at boot.** The rules load in the session where they were added and vanish on restart, so the host looks monitored and is not.

## Reference files

- `references/linux-baseline.md` — read when auditing against CIS or NIST or deciding which controls apply: the common controls mapped to their source, the sysctl and mount settings, the ones that break a router, a container host or a Kubernetes node, and how to record an accepted finding.
- `references/ssh-and-access.md` — read before changing SSH, sudo, users or keys: the directives that matter and their trade-offs, the `sshd -T` verification loop, key and account hygiene, sudo rule design, and the safe fleet change sequence.
- `references/audit-and-detection.md` — read when setting up auditd, logging or drift detection: auditd rule sets for auth and privilege escalation, log shipping and retention, the failure modes that leave a host unmonitored, and the checks that catch configuration drift.
