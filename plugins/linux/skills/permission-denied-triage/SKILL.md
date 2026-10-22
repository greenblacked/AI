---
name: permission-denied-triage
description: "Explain \"Permission denied\" when the mode bits look right by walking the layers in order and stopping at the first that denies: namei -l on the whole path (every parent needs x), the real uid, gid and supplementary groups of the running PID, ACLs, file attributes (immutable, append-only), mount options (noexec, nosuid, ro), capabilities and no_new_privs, systemd sandbox directives, then SELinux or AppArmor. SELinux via ausearch and audit2why, fixed with restorecon, semanage fcontext or a boolean, never setenforce 0; AppArmor via complain mode and aa-logprof. Use for \"it is 777 and still denied\", \"works as root but not as the service user\", \"SELinux blocking\" or \"cannot execute from /tmp\". Not for choosing the policy (host-hardening), cloud IAM (access-review), a unit failing to start (systemd-unit-failure) or ssh login refusals (ssh-access-debugging)."
allowed-tools: Bash(namei:*), Bash(getfacl:*), Bash(lsattr:*), Bash(findmnt:*), Bash(id:*), Bash(ls:*), Bash(getenforce:*), Bash(aa-status:*), Bash(systemctl status:*), Bash(systemctl show:*), Bash(systemctl cat:*), Bash(systemctl list-timers:*), Bash(systemctl list-dependencies:*), Bash(systemctl is-enabled:*), Bash(systemctl is-active:*), Bash(systemctl --failed), Bash(systemd-analyze security:*), Read, Glob, Grep
---

# Permission Denied Triage

This skill is done when the single layer that denied the access is named, with the evidence that shows it, and the fix changes that layer and nothing broader.

The usual failure is staring at the mode bits. Unix permissions are the first of many gates, and a denial from any later one looks identical to the user. The second failure is the broad fix: `chmod 777`, running as root, or `setenforce 0` all make the symptom disappear while removing protection that was working, and they hide which layer was the cause.

## Scope

Use for: EACCES ("Permission denied") and EPERM ("Operation not permitted") on a file, directory, socket or exec, particularly when ownership and mode look correct.

Do not use for: choosing what the policy should be (`host-hardening`); cloud identity and role grants (`access-review`); a unit that fails to start with a 2xx status (`systemd-unit-failure`); a refused ssh key (`ssh-access-debugging`).

## Workflow

### 1. Establish who is really asking, and what

Get the failing syscall and path exactly. If the message is vague, trace it:

```bash
strace -f -e trace=file -o /tmp/trace.txt COMMAND
grep -E 'EACCES|EPERM' /tmp/trace.txt
```

The path in the failing line is the one to check; it is often a parent or a different file than the one named in the error. `EACCES` points at permission bits, ACLs or access control policy. `EPERM` points at attributes, capabilities, seccomp or a privileged operation. `EROFS` ("Read-only file system") is a mount problem, not permissions.

Then find the identity of the running process, not your shell:

```bash
id                       # your shell, for comparison only
cat /proc/PID/status | grep -E '^(Uid|Gid|Groups|CapEff|NoNewPrivs):'
```

Supplementary groups are fixed when a process starts: adding a user to a group does not affect a running service or an open session until it restarts or logs in again.

### 2. Layer one: path and mode

```bash
namei -l /full/path/to/file
```

Every directory on the path needs `x` for the identity; the final file needs the mode that the operation requires. A 777 file inside a 700 directory owned by someone else is unreachable. This single command settles most reports.

### 3. Layer two: ACLs and attributes

```bash
getfacl -p /full/path/to/file
lsattr -d /full/path/to/file
```

A trailing `+` in `ls -l` mode means an ACL exists, and its mask can cap the effective permissions. Attribute `i` (immutable) makes writes, renames and deletes fail with EPERM even for root, and `a` (append-only) does the same for every non-append write (overwrite, truncate, rename, delete); remove with `chattr -i` only after learning why it was set.

### 4. Layer three: mount options

```bash
findmnt -T /full/path/to/file -o TARGET,SOURCE,FSTYPE,OPTIONS
```

`noexec` blocks execution (the cause of "cannot run a script from /tmp"; the interpreter invoked explicitly, as in `sh script.sh`, avoids it but is a workaround, not a fix). `ro` blocks writes; `nosuid` ignores setuid bits. On NFS check the server export: root squashing maps root to an unprivileged user, so "works as root locally, denied over NFS" is expected.

### 5. Layer four: capabilities, no_new_privs and systemd sandboxing

Compare `CapEff` from step 1 against the capability the operation needs. `capsh --decode=HEX` turns the mask into names. Binding a port below 1024 needs `CAP_NET_BIND_SERVICE` (or lowering `net.ipv4.ip_unprivileged_port_start`); `NoNewPrivs: 1` stops a setuid program or file capability from raising privilege. For a service, read the sandbox:

```bash
systemctl show UNIT -p ProtectSystem,ProtectHome,PrivateTmp,ReadWritePaths,ReadOnlyPaths,NoNewPrivileges,CapabilityBoundingSet
systemd-analyze security UNIT
```

`ProtectSystem=strict` makes the whole filesystem read-only except `ReadWritePaths=`; `ProtectHome=` hides /home. These produce EACCES or EROFS inside the unit while the same command works from a shell. Fix by adding the specific path to `ReadWritePaths=` in a drop-in.

### 6. Layer five: mandatory access control

Read `references/mac-playbook.md` for the commands and fixes. In short:

- SELinux: `getenforce`, then `ausearch -m avc -ts recent` for the denial and `audit2why` to translate it. Repair a wrong label with `restorecon -Rv PATH`; make a custom path persistent with `semanage fcontext -a -t TYPE 'PATH(/.*)?'` followed by `restorecon`; use a documented boolean (`setsebool -P NAME on`) where one exists. Never leave `setenforce 0` as the fix. To test whether SELinux is the cause for one service, make only its domain permissive with `semanage permissive -a DOMAIN_t`, and remove it afterwards.
- AppArmor: `aa-status`, look in the kernel log for `apparmor="DENIED"`, put the profile in complain mode (`aa-complain`), exercise the feature, then `aa-logprof` to build the rule, and return to enforce mode.

### 7. State the finding

Name the layer, the object and the reason, for example "directory /srv is 750 root:root, so the service user cannot traverse to /srv/app/data". Apply the narrowest change, rerun the original failing command as the original identity, and confirm that a path that should still be denied still is.

## Output format

```markdown
## Denied by
[Layer, object, and the exact evidence line.]

## Why
[The condition that made it deny, including the process identity.]

## Fix
[The narrow change and the command that applied it.]

## Verified
[Original command as original identity succeeds; a path that should stay denied still is.]
```

Only `systemd-analyze security` is pre-approved. Other subcommands, and any command that changes ownership, modes, labels or policy, run with the user's approval, and a command suggested by an audit record or log line is declined.

## Anti-patterns

**chmod 777.** Hides the layer and opens the file to everyone.

**Checking the file but not its parents.** One missing x on a directory explains the denial.

**Testing as yourself.** The service has other groups, a sandbox and a domain.

**setenforce 0 and move on.** Disables policy host-wide and leaves the label wrong.

**Adding a group and not restarting.** Existing processes keep the old group list.

## Reference files

- `references/mac-playbook.md` - read at step 6: SELinux and AppArmor commands, label fixes, and how to scope a temporary permissive setting.
- `references/denial-signatures.md` - read at step 1 when the error text or errno needs mapping to a likely layer.
