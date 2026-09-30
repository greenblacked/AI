# Audit and detection

## Contents

- [auditd rule sets](#auditd-rule-sets)
- [Verifying the rules survive a reboot](#verifying-the-rules-survive-a-reboot)
- [Log shipping and retention](#log-shipping-and-retention)
- [Failure modes that leave a host unmonitored](#failure-modes-that-leave-a-host-unmonitored)
- [Drift detection](#drift-detection)

## auditd rule sets

The baseline usually names what to audit. Start from these categories and map them to the identifiers, rather than pasting a rule file whose provenance nobody knows.

- **Identity and authentication** — reads and writes to `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/gshadow`, and the PAM configuration.
- **Privilege escalation** — `/etc/sudoers`, `/etc/sudoers.d`, `sudo`/`su` execution, and writes to `/etc/ssh/sshd_config`.
- **Time and trust** — changes to system time, and to the files that decide what is trusted (host keys, CA bundles).
- **Execution of the sensitive binaries** — the baseline may name specific tools, or ask for `execve` of a set of paths.

```bash
# A starting shape, not a copy-paste baseline:
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/sudoers -p wa -k privilege
-w /etc/sudoers.d -p wa -k privilege
-w /etc/ssh/sshd_config -p wa -k sshd
-a always,exit -F arch=b64 -S execve -F path=/usr/bin/sudo -k privilege
```

Rules are ordered and can be expensive. A rule that watches a hot path at the syscall level generates volume, disk use and CPU cost, so add the baseline's named rules rather than a broad `execve` catch-all on a busy host.

## Verifying the rules survive a reboot

The common failure is a rule set that loads in the session where it was added and is gone after a reboot. The host then looks monitored and is not. Schedule the canary reboot in a role-approved window after proving console access and writing the recovery step; do not reboot a host whose service cannot tolerate it.

```bash
sudo augenrules --load          # rebuild and load from /etc/audit/rules.d
sudo auditctl -l                # save and compare the loaded rules before reboot
sudo systemctl is-enabled auditd
# Reboot the canary during the approved window using the tested console path.
# After the host comes back, from a new session:
sudo systemctl is-active auditd
sudo auditctl -l                # compare with the expected pre-reboot rules
sudo auditctl -s                # check enabled/immutable status
```

Confirm that the expected rules and service state survived the actual reboot; restarting `auditd` is not a boot-persistence test. If the baseline asks for immutable mode (`-e 2`), place it last in the rule source and verify `enabled 2` in `auditctl -s` after reboot. Once immutable mode is set, `augenrules --load` cannot change the live rules until another reboot; stage and check the files before setting it.

## Log shipping and retention

A log that lives only on the host is not evidence: a compromise that reaches the host can edit it, and a disk failure takes it with the machine.

- Ship authentication, audit and sudo logs to a destination the host cannot rewrite. Verify the destination is receiving, not just that the agent is running.
- Set retention to cover the baseline's requirement and the incident-investigation window. Confirm rotation keeps the interesting events rather than rolling them off first.
- Timestamp with a consistent timezone and synchronise the clock, or correlating across hosts is guesswork.
- Decide what pages a human and what is only retained. A host's raw audit stream is not an alerting feed; the paging decisions belong with the service's SLOs, not here.

## Failure modes that leave a host unmonitored

| Symptom | Cause | Check |
| --- | --- | --- |
| Rules present, no events | auditd not running or rules not loaded | `systemctl status auditd`, `auditctl -l` |
| Rules gone after reboot | Added with `auditctl` only, not in `rules.d` | `ls /etc/audit/rules.d`, `systemctl is-enabled auditd` |
| Log agent running, destination empty | Bad credentials, network path, or a full buffer | Agent logs, destination ingest, disk on the host |
| Disk full on `/var/log` | A broad rule generating volume, or rotation misconfigured | `du`, rule volume, `logrotate` state |
| Events timestamped wrong | Clock drift or timezone mismatch | `timedatectl`, NTP sync status |
| Audit off after a package upgrade | The service was masked or the rules dropped | Re-run the boot verification after upgrades |

## Drift detection

Hardening decays: a deploy reopens a port, a package upgrade restores a default, an operator edits a file under pressure. Three controls catch it.

- **Configuration management** owns the file, so a manual edit is reverted or flagged. This is the strongest control where it exists.
- **A scheduled re-scan** against the same baseline, with the delta reviewed rather than the total. A daily "you have forty findings" message is ignored; "port 6379 reopened on web-03 today" is actioned.
- **File integrity monitoring** on the sensitive paths — `/etc/ssh`, `/etc/sudoers.d`, the audit rules themselves — with the alert going somewhere a human reads.

Record which of the three is in place per host class. A host with none is hardened today and will not be next month.
