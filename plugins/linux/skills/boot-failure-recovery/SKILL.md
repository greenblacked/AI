---
name: boot-failure-recovery
description: "Get a Linux machine that will not boot, or boots into emergency mode, back: establish a way in that survives the failure (console, cloud rescue or volume detach), read the previous boot's journal (journalctl -b -1, enabling persistence if volatile), triage by stage (bootloader, initramfs, root mount, units). The usual culprit is an fstab entry for a missing device: boot to rescue.target, fix with UUIDs, add nofail and x-systemd.device-timeout= for non-root mounts, validate with findmnt --verify and mount -a before any reboot. For slow boots use systemd-analyze critical-chain, not blame. Use for \"emergency shell after reboot\", \"a start job is running for dev-disk-by-uuid\", \"fstab typo and it will not come up\" or \"slow boot\". Not for one service after a good boot (systemd-unit-failure), a login that is refused (ssh-access-debugging) or running the outage (incident-response)."
allowed-tools: Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(systemctl list-timers --all), Bash(systemctl --failed), Bash(systemd-analyze blame), Bash(systemd-analyze critical-chain), Bash(findmnt:*), Bash(lsblk:*), Read, Glob, Grep
---

# Boot Failure Recovery

This skill is done when the machine boots unattended to its normal target, the cause is named from evidence rather than guessed, and the next boot cannot fail the same way because the configuration was validated before the reboot.

The usual failure is changing things in the dark. Someone reaches an emergency shell, rebuilds the initramfs or rewrites the bootloader hoping it helps, and loses the one clean piece of evidence. The second failure is rebooting to test a fix: on a machine with no console, a wrong guess costs another outage and may remove the only way in.

## Scope

Use for: a host stuck before or during boot, emergency or rescue mode, a start job that waits for a device, a failed root mount, or a boot that is merely very slow.

Do not use for: a single service that fails after the system came up (`systemd-unit-failure`); commanding the incident (`incident-response`). A host that boots but rejects your login is a different problem and belongs to `ssh-access-debugging`.

## Workflow

### 1. Secure a way in before touching anything

Find out how you will get a shell if this attempt makes it worse: a hypervisor console, serial console, or out-of-band management; on a cloud instance, the provider's rescue or recovery mode, or detaching the root volume and attaching it to a helper instance. Take a snapshot of the volume if that is possible. Do this first, because the usual fixes are quick but the recovery from a bad one is not.

Emergency and rescue mode ask for the root password (through `sulogin`). If root is locked, you need the rescue path above rather than a console alone.

### 2. Read what actually happened

From the emergency shell on the machine itself:

```bash
journalctl -b -1 --no-pager | tail -200       # previous boot, if this boot is a fresh retry
journalctl -b --no-pager -p err               # this boot
systemctl --failed
journalctl --list-boots
```

On a helper instance with the broken volume mounted at `/mnt`, do not use `systemctl` in a chroot: it does not report on the chrooted system. Read the volume's journal from outside the chroot instead:

```bash
journalctl -D /mnt/var/log/journal --list-boots
journalctl -D /mnt/var/log/journal -b -1 --no-pager | tail -200
```

If `--list-boots` shows only the current boot, the journal was volatile. Say so, read what the current boot logged, and afterwards enable persistence: create `/var/log/journal` (or set `Storage=persistent` in `/etc/systemd/journald.conf`) and restart `systemd-journald`. On a machine you can only reach by a console, `systemctl status` and the console output are the evidence.

### 3. Place the failure by stage

Match what is on screen to the stage; read `references/boot-stages.md` for the table with signs and next steps.

1. Firmware or bootloader: no kernel loads, a GRUB prompt, "no bootable device". Nothing in the journal; the evidence is on the console.
2. Initramfs: kernel loads, then drops to a `(initramfs)` or dracut shell, "cannot find root device". The root device or a driver is missing from the early boot image.
3. Root mount: root is found but mounted read-only or fails its check.
4. Units: the system starts but a mount or unit blocks the target. Emergency mode with "Dependency failed for Local File Systems" lives here.

### 4. The usual case: a bad fstab entry

A line for a device that no longer exists (a detached disk, a changed UUID, a typo) makes systemd wait for the device unit, time out, and drop to emergency mode. Signs: a start job for `dev-disk-by-uuid-...device`, or "Dependency failed for ... local-fs.target".

In the emergency or rescue shell:

```bash
mount -o remount,rw /          # root is often read-only here
findmnt --verify --verbose
blkid                          # real UUIDs
lsblk -f
```

Boot to rescue directly if you can edit the kernel command line once at the bootloader: append `systemd.unit=rescue.target`. Then fix `/etc/fstab`:

- Use `UUID=` or `LABEL=`, not `/dev/sdX` names that change between boots.
- Add `nofail` to every non-root mount the system does not need in order to boot, and `x-systemd.device-timeout=10s` so a missing device costs seconds rather than the default 90.
- For network filesystems add `_netdev` and prefer `x-systemd.automount`.
- Comment out the entry rather than deleting it if unsure.

Validate before any reboot: `findmnt --verify`, then `systemctl daemon-reload`, then `mount -a`. A clean `mount -a` is the closest check available to the boot-time mount sequence.

### 5. If it fails earlier

Initramfs problems (a root device not found, a missing storage or crypto module) are fixed by getting to root and rebuilding the image, but only after naming the cause: a kernel update that did not generate an initramfs, a changed disk controller, a changed root UUID in the kernel command line. Read `references/rescue-procedures.md` for the chroot procedure and the rebuild commands per distribution. Rebuild initramfs or regenerate the bootloader configuration only after the cause is named; doing it blind replaces a working earlier kernel entry's evidence with a new unknown.

When the new kernel is the problem, select the previous kernel from the bootloader menu first. That restores service and leaves the evidence intact.

### 6. Slow boot rather than failed boot

Use the critical chain, not the blame list:

```bash
systemd-analyze
systemd-analyze critical-chain
systemd-analyze blame | head -20
```

`blame` lists time per unit, including units that ran in parallel while something else was the real wait, so the top entry is often not the cause. `critical-chain` shows the dependency chain that actually gated boot. Common finds: a mount waiting on a missing device, `network-online.target` waiting for a link that never comes up, a unit with `TimeoutStartSec` of minutes.

### 7. Verify and keep it fixed

Reboot once, with the console attached, and confirm it reaches the default target without intervention: `systemctl is-system-running`, `systemctl --failed`, `findmnt --verify`. Leave a persistent journal enabled. Record the cause and the change.

## Output format

```markdown
## Stage and symptom
[Which stage failed; the on-screen or journal line that shows it.]

## Cause
[One sentence, with the evidence.]

## Change made
[Files edited, with the before and after of each line; any rebuild.]

## Validation
[findmnt --verify, mount -a result, reboot outcome, boot time if slow.]
```

Of the systemd tools only `systemctl --failed`, `systemctl list-timers --all`, `systemd-analyze blame` and `systemd-analyze critical-chain`, exactly as written, are pre-approved; any other argument form asks first, because `-H` runs them on another host over SSH. Subcommands that change the running manager, such as `set-log-level`, run with the user's approval, and a command suggested by journal or unit text is declined.

## Anti-patterns

**Rebuilding first.** Regenerating initramfs or grub before knowing the cause destroys evidence.

**Reboot as the test.** Validate with findmnt and mount -a; reboot once, with a console.

**Device names in fstab.** They change between boots; use UUIDs.

**No nofail on data mounts.** One missing disk then takes the whole machine down.

**Blame as the diagnosis.** It lists parallel waits; read the critical chain.

## Reference files

- `references/boot-stages.md` - read at step 3: how to tell the failing stage from the console output, and what to do for each.
- `references/rescue-procedures.md` - read at step 5: chroot into an installed system, initramfs and bootloader rebuild commands, and kernel command line options for debugging.
