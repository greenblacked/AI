---
name: linux-lockout-recovery
description: "Regain access to a Linux server you are locked out of: \"broke sudoers and cannot get root\", \"changed sshd config and now cannot log in\", \"lost the only SSH key\", \"firewall rule cut my own connection\". Take the least destructive door in order: a session still open (keep it), serial or hypervisor console, the cloud provider's agent or run-command, then rescue boot or detaching the root volume onto a helper instance. Repair with the safe checkers (visudo -c, sshd -t, nft -c, iptables-restore --test, chroot), fix ownership and SELinux labels after offline edits, keep an untouched copy, and do not reset the root password first. Then add the guard: a second admin, a timed rollback, a test login before closing. Use for any self-inflicted lockout. Not for logins failing with a way in open (ssh-access-debugging), baselines (host-hardening) or no boot (boot-failure-recovery)."
allowed-tools: Bash(visudo -c:*), Bash(visudo -cf:*), Bash(lsblk:*), Bash(findmnt:*), Bash(ls:*), Bash(stat:*), Bash(getenforce:*), Bash(id:*), Bash(ss -tn), Bash(who:*), Read, Glob, Grep
---

# Linux Lockout Recovery

This skill is done when you have a working administrative login by a method you tested from a fresh session, the broken file is repaired and passes its syntax checker, an untouched copy of what you found is kept, and a guard exists that would have prevented the lockout.

The usual failure is escalating too fast. A password reset, a reinstall or deleting a config file feels decisive and is destructive: it changes credentials that other systems rely on, loses the evidence of what broke, and often creates a second lockout (wrong SELinux label, wrong ownership, a locked account). Almost every self-inflicted lockout is a single broken file, and the checkers that would have caught it before the reload exist. The job is to find the lightest door that reaches that file.

## Scope

Use for: sudoers errors that remove root, sshd configuration that refuses every login, a lost or replaced key with no other authorised key, and firewall rules that block your own address.

Do not use for: a login that is failing while you still have a session or console and want the cause (`ssh-access-debugging`, `firewall-rule-tracing`); deciding what a hardened configuration contains (`host-hardening`); a machine that does not boot at all (`boot-failure-recovery`). Rotating credentials that leaked is `secret-rotation`.

Only recover hosts you are authorised to administer. Every door below assumes you own the machine or the account that does; if you do not, stop and ask the owner.

## Workflow

### 1. Stop and take stock

Do not close any session that is still open, even a half-working one, and do not make a second change to the broken thing. Write down what changed last, on which file, and when. That names the file to repair and, with the next step, the door to use.

```bash
who; ss -tn state established '( sport = :22 )'     # sessions still attached
```

A shell, even an unprivileged one, may be enough: see step 3.

### 2. Use the lightest door available

Work down this list and stop at the first that works. Each later door costs more downtime and more risk.

1. **An existing session** (ssh, console, a tmux or screen you left running, a web terminal). Keep it open and repair from it.
2. **Serial or hypervisor console.** Cloud serial console, IPMI or BMC, a virtual machine console. It bypasses the network and sshd. It needs a local login, so a password for some account must exist; if none does, move to the next door.
3. **The provider's agent or run-command path.** An installed agent can run a command as root with no network login: AWS Systems Manager Run Command or Session Manager (needs the agent running and an instance role), Azure `az vm run-command invoke`, a GCP startup script set in instance metadata (it runs as root at boot). For a lost key on AWS, EC2 Instance Connect can push a temporary public key to an instance that supports it. These are the least destructive doors for a remote host and the first to try when the box is up but unreachable.
4. **Rescue boot, or detach the root volume.** Boot rescue media, or stop the instance, detach its root volume, attach it to a helper instance in the same zone, mount it, repair, then reattach under the original device name. The most reliable door and the most disruptive: it needs downtime and a stop.

Read `references/doors.md` for the commands of each door, mounting a volume that shares an identifier with another, and recovering through a kernel boot parameter at a console.

### 3. Use what you have before reaching for more

A shell that cannot sudo may still reach root through other paths you legitimately hold: `su -` with the root password if it is set and known; `pkexec visudo` where polkit is running; membership of a group (`id`) that your sudoers fragments grant. A sudoers fragment can be fixed by anything that can run as root, including the run-command door above. Do not guess passwords or exploit the system: if no authorised path exists, use a door from step 2.

### 4. Preserve, then repair with the checker

Before editing anything, keep the broken state.

```bash
EV=/root/lockout-evidence.$(date +%Y%m%d%H%M%S); mkdir -p "$EV"
cp -a /etc/sudoers /etc/sudoers.d "$EV"/
cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.d "$EV"/ 2>/dev/null
grep -hiE '^\s*(Include|[#@]includedir?|@include)' /etc/sudoers /etc/sudoers.d/* /etc/ssh/sshd_config /etc/ssh/sshd_config.d/* 2>/dev/null
```

The evidence directory is timestamped, so a rerun cannot nest copies, and nothing ever restores from it: it is the broken state, kept for the post-incident write-up. The last command lists every `Include`, `@include` and `@includedir`/`#includedir` target; copy each one that is outside the paths above into `"$EV"`, because an included file that stays live keeps the fault if only the main file is restored. The rollback guard in step 8 uses a different directory, a known-good snapshot taken after the repair. Then repair the specific file and run its checker before any reload. A broken file left in place with a reload skipped is safe; a reload with a broken file is the lockout.

| Broken | Edit with | Check | Notes |
| --- | --- | --- | --- |
| sudoers | `visudo` or `visudo -f /etc/sudoers.d/NAME` | `visudo -c`, or `visudo -cf FILE` | Fragments must be mode 0440, owned by root; a file with a `.` or ending in `~` in its name is ignored |
| sshd_config or drop-in | an editor, then | `sshd -t` | Check `Include` targets too, and `sshd -T -C user=U,host=H,addr=A` for `Match` blocks |
| nftables | an editor, then | `nft -c -f FILE` | Applies atomically when loaded |
| iptables | `iptables-save` file | `iptables-restore --test < FILE` | Loads nothing, only parses |
| authorized_keys | add the public key | `ssh-keygen -lf FILE` | Home mode must not be group- or world-writable; `.ssh` 700, file 600, owned by the user |

If the cause is a firewall rule and you have a console, the fastest repair is to reload the saved good ruleset, or to remove the offending rule by handle. Setting a permissive policy to get in is a temporary measure: record it, and restore the intended rules before leaving. Do not leave the host open.

### 5. If you edited from outside (chroot or mounted volume)

```bash
mount /dev/xvdf1 /mnt                        # xfs with a duplicate UUID: mount -o nouuid
for d in dev proc sys; do mount --bind /$d /mnt/$d; done
chroot /mnt /bin/bash
visudo -c; sshd -t
exit
touch /mnt/.autorelabel                      # SELinux systems: relabel on next boot after offline edits
umount -R /mnt
```

Offline edits create files with the wrong owner or label. Check ownership (`root:root` for sudoers and sshd files; the user for `~/.ssh`) and, on SELinux systems, the label (`ls -Z`), then `touch /.autorelabel` on the real root so the first boot relabels. Expect a longer first boot after a relabel. If the repair is a key, `restorecon -Rv ~/.ssh` inside the chroot where available.

### 6. Do not reset the root password as the first move

Resetting root with a kernel boot parameter or from rescue media changes a credential other systems and people may rely on, and on some builds it also leaves root with a password where policy says none. If you need it, it is the last door, and the result is a temporary password that you rotate and then lock again. Prefer to fix the actual file.

### 7. Prove the fix from a fresh session

Open a new connection with the original method (not the console you used to repair), then run `sudo -l` and one privileged command. Only then close the recovery path. Check logs: `journalctl -u ssh -u sshd --since "20 min ago"` for the login, `journalctl _COMM=sudo` for the sudo line.

### 8. Add the guard that was missing

The lockout was possible because one change had no way back. Put at least these in place and record them:

- A second authorised administrator with an independent key, tested.
- A timed rollback armed before any risky edit, restoring from a known-good snapshot taken after the repair and the test login (never from the step 4 evidence, which is the broken state): `systemd-run --on-active=10min --unit=revert-ssh /usr/local/sbin/revert-ssh.sh`, or `at now + 10 minutes`, and cancelled only after the test login works (`systemctl stop revert-ssh.timer`).
- Edit sudoers only with `visudo`, in a fragment under `/etc/sudoers.d/`, and validate with `visudo -cf`.
- Run `sshd -t` before every reload, keep a session open, and test a new login from a second terminal before closing the first.
- Confirm the out-of-band path works now (console, run-command agent running), not during the next incident.

## Output format

```markdown
## What broke
[File, change, and the symptom that exposed it.]

## Door used
[Which of the four, why the earlier ones were unavailable.]

## Repair
[Exact change, checker output, untouched copy location.]

## Proof
[Fresh login by the original method; sudo check.]

## Guard added
[Second admin, rollback, test practice, out-of-band access confirmed.]
```

## Anti-patterns

**Closing the last session to "restart clean".** The open session is the lightest door you have.

**Resetting the root password first.** It is destructive and leaves the cause in place.

**Reloading with an unchecked file.** Every checker named here exists to prevent exactly this.

**Editing the file with a mount of the wrong volume.** Check the helper's mount point is the broken host's root, not the helper's own.

**Leaving the firewall open after getting in.** The temporary policy becomes the baseline.

**Skipping the relabel.** An SELinux system then refuses the repaired login with no message.

## Reference files

- `references/doors.md` - read at step 2 and step 5: the commands for each door on common clouds and consoles, duplicate-identifier mounts, a boot-parameter route, and a rollback script template.
