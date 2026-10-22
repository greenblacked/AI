# Doors, in order of disruption

## Contents

- Door 1: an existing session
- Door 2: console
- Door 3: provider agent and run-command
- Door 4: volume detach and rescue boot
- Rollback script template
- Repair recipes

## Door 1: an existing session

Keep it. If it is an ssh session, do not run anything that restarts the network or the daemon from it. If it is unprivileged, read `sudo -l` and `id` to see what it can do. A terminal multiplexer session left on the host (`tmux ls`, `screen -ls`) may already be root.

## Door 2: console

| Environment | How |
| --- | --- |
| VM hypervisor | The hypervisor's console window; it works with no network |
| Bare metal | IPMI or BMC remote console, or a physical console |
| Cloud serial console | AWS EC2 Serial Console (must be allowed for the account and the instance type), Azure Serial Console, GCP serial console for the instance |

A serial console gives a login prompt. If you have no valid account password there, step to door 3 or 4. At a bootloader prompt on a console you can append a kernel parameter such as `init=/bin/bash` to the kernel line for a single boot to get a root shell with the root filesystem read-only; run `mount -o remount,rw /`, repair the file, `touch /.autorelabel` on SELinux systems, and reboot with `exec /sbin/init` or a hard reset. Some distributions use `rd.break` instead. This route is allowed only on a machine you administer, and a bootloader password, where set, is the control that governs it.

## Door 3: provider agent and run-command

These run a command as root without a network login, provided the agent was installed and running before the lockout.

```bash
# AWS Systems Manager: instance needs the agent and an instance profile with SSM permissions
aws ssm send-command --instance-ids i-0123456789abcdef0 \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["visudo -c","sshd -t"]'

# Azure
az vm run-command invoke -g RG -n VM --command-id RunShellScript --scripts "visudo -c"

# AWS EC2 Instance Connect: pushes a temporary key (valid for a short window) for a user
aws ec2-instance-connect send-ssh-public-key --instance-id i-0123456789abcdef0 \
  --instance-os-user ec2-user --ssh-public-key file://key.pub
```

Check each against the provider's current documentation before relying on it: the document names, the agent prerequisites and the timeouts differ. On GCP, set the `startup-script` metadata key to a script that repairs the file and reboot (or reset) the instance; it runs as root at boot, and you remove the metadata afterwards.

Use these to repair precisely: restore the saved `sshd_config`, run `sshd -t`, add a public key to `authorized_keys`, or remove a bad sudoers fragment. Run read-only checks first and capture output.

## Door 4: volume detach and rescue boot

1. Note the original root device name (for example `/dev/xvda`) and the instance's zone.
2. Stop the instance, snapshot the root volume, detach it.
3. Attach it to a helper instance in the same zone as a secondary volume.
4. Mount it: `lsblk -f` to find the partition, `mount /dev/xvdf1 /mnt`. A cloned xfs volume shares its UUID with the helper's root, so mount with `-o nouuid`.
5. Repair and, on SELinux systems, `touch /mnt/.autorelabel`.
6. `umount`, detach, reattach to the original instance with the original device name, start it.

For a physical machine, boot rescue media and mount the root the same way (`lsblk -f`, `mount`, `chroot`). With LVM, activate first: `vgscan; vgchange -ay`. With LUKS, `cryptsetup open /dev/sdX2 NAME` before mounting.

## Rollback script template

Arm this before the risky edit:

```bash
#!/bin/bash
set -Eeuo pipefail
# restore the known-good snapshots (see below), never the broken-state evidence from SKILL.md step 4
test -f /root/ssh.good/sshd_config
test -f /root/sudoers.good/sudoers
# replace the drop-ins wholesale so files the edit created disappear too
cp -a /root/ssh.good/sshd_config /etc/ssh/sshd_config
rm -rf /etc/ssh/sshd_config.d
cp -a /root/ssh.good/sshd_config.d /etc/ssh/sshd_config.d
cp -a /root/sudoers.good/sudoers /etc/sudoers
rm -rf /etc/sudoers.d
cp -a /root/sudoers.good/sudoers.d /etc/sudoers.d
# Include targets outside those paths were saved under include/ with their full paths.
# Restore files and symlinks one by one, never a directory: copying a saved directory
# onto / or /etc would stamp the snapshot's mode and timestamps onto the live one.
# A missing or empty include/ restores nothing and is not an error.
for snap in /root/ssh.good/include /root/sudoers.good/include; do
  test -d "$snap" || continue
  (cd "$snap" && find . \( -type f -o -type l \) -print0) |
    while IFS= read -r -d '' f; do cp -a "$snap/$f" "/${f#./}"; done
done
# validate before reloading; under set -e a failed check leaves sshd running as it is
visudo -c
/usr/sbin/sshd -t
systemctl reload ssh || systemctl reload sshd
```

```bash
install -m 0755 revert-ssh.sh /usr/local/sbin/revert-ssh.sh
systemd-run --on-active=10min --unit=revert-ssh /usr/local/sbin/revert-ssh.sh
# after a successful test login from a second terminal:
systemctl stop revert-ssh.timer
```

Take the known-good snapshots right before each risky edit, once the repair is done and a fresh login has been tested, and only after `visudo -c` and `sshd -t` both pass on the live files:

```bash
rm -rf /root/ssh.good /root/sudoers.good; mkdir -p /root/ssh.good/include /root/sudoers.good/include
cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.d /root/ssh.good/
cp -a /etc/sudoers /etc/sudoers.d /root/sudoers.good/
# every Include target that step 4 of SKILL.md lists and that sits outside those paths,
# saved under include/ with its full path so the rollback can copy it straight back:
cp -a --parents /PATH/FROM/INCLUDE /root/ssh.good/include/       # sshd Include targets
cp -a --parents /PATH/FROM/INCLUDE /root/sudoers.good/include/   # @include and @includedir targets
```

An included file that stays live keeps the fault if only the main file is restored, which is why the snapshot, like step 4, covers every target. A copy-back restore only overwrites; it does not remove a file the edit newly created inside an `@includedir` or sshd `Include` directory outside `sudoers.d` and `sshd_config.d`, and that file stays live. After the restore, list each such directory against its snapshot with `diff -rq /root/sudoers.good/include/DIR /DIR` (or `/root/ssh.good/include/DIR`) and remove every file reported as `Only in /DIR`, since it was not in the snapshot. The snapshots live apart from the evidence directory of SKILL.md step 4, which holds the broken state and is never restored from. Both must exist before the timer is armed, and the script restores sudoers as well as sshd because step 8 arms one rollback for any risky edit, not only an sshd one. Use absolute paths inside the script. A timer or `at` job runs with a minimal environment.

## Repair recipes

- **Bad sudoers fragment:** `visudo -cf /etc/sudoers.d/NAME`; fix or move the file out of `/etc/sudoers.d/`, then `visudo -c`. Mode 0440, owner root.
- **Locked out by AllowUsers or PermitRootLogin:** restore the saved config, `sshd -t`, `systemctl reload`. Confirm with `sshd -T -C user=U,host=H,addr=A | grep -iE 'allowusers|permitroot|passwordauth|pubkeyauth'`.
- **Only key lost:** append a new public key to the user's `authorized_keys`; set the modes and, on SELinux, `restorecon`. Remove the old key from every host where it was authorised.
- **Firewall cut you off:** at a console, reload the saved good ruleset (`nft -f /root/ruleset.before.nft`, `iptables-restore < /root/ipt.before`), or delete the bad rule by handle (`nft -a list ruleset`, `nft delete rule ... handle N`). Test the ruleset first with `nft -c -f` or `iptables-restore --test`.
- **Account locked or expired:** `passwd -S USER`, `chage -l USER`; unlock deliberately with `usermod -U USER` or `chage -E -1 USER`, and note why it locked.
