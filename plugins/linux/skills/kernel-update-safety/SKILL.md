---
name: kernel-update-safety
description: "Update kernels and reboot fleets safely. Use for \"patching kernels on production tomorrow\", \"DKMS module failed to build after upgrade\", \"how do I roll back a kernel\" or \"needs-restarting says reboot required\". Before rebooting confirm console access, keep a known-good kernel, check dkms status builds for the new kernel (NVIDIA, ZFS, storage drivers) and that the initramfs holds the storage and network modules root needs. Boot once with grub-reboot or a boot-loader entry with automatic fallback rather than changing the default. Canary one host, then batches ordered by redundancy; check uname -r, failed units, mounts, network and service health. Know the rollback and when livepatch suffices. Not for a host that already failed to boot (boot-failure-recovery), patch policy (host-hardening), application rollout (release-strategy) or cluster versions (k8s-upgrade)."
allowed-tools: Bash(dkms status:*), Bash(uname:*), Bash(lsinitramfs:*), Bash(needs-restarting:*), Bash(grubby --default-kernel), Bash(mokutil --sb-state), Bash(systemctl --failed), Bash(systemctl is-system-running:*), Bash(findmnt:*), Read, Glob, Grep
---

# Kernel Update Safety

This skill is done when the new kernel is running on every host in scope, each host booted it on the first try or fell back by itself, and the previous kernel is still installed until the new one has run a full cycle of the workload.

The usual failure is changing the default boot entry and rebooting, which turns any problem with the new kernel into a host that cannot come back without someone at the console. The common causes are an out-of-tree module that did not build for the new kernel, an initramfs that lacks the storage or network driver the root needs, and a Secure Boot policy that refuses an unsigned module. All three are checkable before the reboot.

## Scope

Use for: planning and running kernel updates and the reboots they need; DKMS or module build failures after an upgrade; rolling back to an earlier kernel; deciding between livepatch and a reboot.

Do not use for: a host that has already failed to boot (`boot-failure-recovery`); the patch cadence and policy (`host-hardening`); application rollout strategy (`release-strategy`); upgrading a cluster's version (`k8s-upgrade`).

## Workflow

### 1. Establish the way back

Confirm out-of-band access that works without the operating system: IPMI or BMC console, a hypervisor console, or the cloud provider's serial console. Test the login, not only the existence. Then confirm at least one known-good kernel stays installed: Debian-family systems keep old kernels until `apt autoremove` removes them, and Red Hat-family systems keep `installonly_limit` kernels (the default is three). Note the current kernel with `uname -r` and write it into the change record; it is the rollback target.

### 2. Check what the new kernel needs

Install the package without rebooting, then check the new kernel's version, not the running one.

```bash
dkms status                      # every module should show "installed" for the new kernel version
ls /boot                         # vmlinuz and initramfs for the new version both present
lsinitramfs /boot/initrd.img-NEWVER | grep -E 'nvme|ahci|virtio|mpt3sas|megaraid|raid|dm-|lvm|crypt|e1000|ixgbe|bnx|igb'   # Debian family
lsinitrd /boot/initramfs-NEWVER.img | grep -E 'nvme|ahci|virtio|dm-|lvm|crypt'                                          # Red Hat family
mokutil --sb-state               # if Secure Boot is enabled, DKMS modules must be signed
```

A `dkms status` line that shows `built` but not `installed`, or no line for the new version, means the module will be missing after the reboot. Typical victims are NVIDIA, ZFS, WireGuard on older kernels, and vendor storage or network drivers. Compare the modules the root device and the network need (`lsblk`, `lsmod`, `ethtool -i` against the initramfs listing) rather than trusting the grep above to be complete for your hardware. Rebuild the initramfs if the content is wrong, using the distribution's tool (`update-initramfs -u -k NEWVER`, `dracut --force`).

### 3. Boot once, with a fallback

Do not set the new kernel as the default first. Installing the package usually does that for you, so check straight after the install and put the running kernel back before the one-time boot. Red Hat-family systems ship `UPDATEDEFAULT=yes` in `/etc/sysconfig/kernel`, so the install makes the new kernel the saved default; Debian and Ubuntu use `GRUB_DEFAULT=0`, which boots the newest entry. Without this step `grub-reboot` gives no fallback and a reset boots the bad kernel again.

```bash
grubby --default-kernel          # Red Hat family: must name the rollback kernel
grub-editenv list                # GRUB: saved_entry must name the rollback entry
```

If it names the new kernel, set the old one back with `grubby --set-default /boot/vmlinuz-OLDVER` or `grub-set-default "ENTRY"`. On Debian-family systems with `GRUB_DEFAULT=0`, change it to `saved` in `/etc/default/grub`, run `update-grub`, then set the default. Boot once, then let the old default stand.

- GRUB with `GRUB_DEFAULT=saved`: `grub-reboot "ENTRY"` (`grub2-reboot` on Red Hat-family) selects the entry for the next boot only. List entry names with the `menuentry` lines in the GRUB configuration. This only works when the default is `saved`; confirm it before relying on it.
- systemd-boot: `bootctl set-oneshot ENTRY` for one boot, or boot counting by adding `+3` to the entry filename so that an entry that fails to reach a successful boot three times is skipped; `systemd-bless-boot` marks success.
- A kernel that hangs instead of resetting will not fall back. Make sure it resets: `panic=10` on the kernel command line and, where available, a hardware watchdog, so a hung boot restarts into the old kernel on its own.

Make the new kernel the default only after verification (step 5).

### 4. Order the fleet

1. One canary host of a representative role, left to run for a meaningful period.
2. Batches ordered by redundancy: replicas before primaries, one member of each cluster at a time, never both halves of a pair together, never all hosts behind one load balancer together.
3. Stop between batches and check the previous one. The batch size grows only when the last batch was clean.

Drain traffic first where the platform supports it, and use the platform's own safe-shutdown procedure for databases and queues.

### 5. Verify after the boot

```bash
uname -r                       # is it the new kernel
systemctl --failed             # no newly failed units
systemctl is-system-running    # "running", not "degraded"
findmnt --verify               # /etc/fstab parses and its entries are usable (not a mounted-state check)
findmnt /MOUNTPOINT            # repeat per fstab target: is it actually mounted (the --failed check above lists failed *.mount units)
ip -br addr                    # interfaces up with the expected addresses
dkms status                    # modules loaded for this kernel
```

Then check the service itself: its health endpoint, its queue depth or replication state, and the error rate, compared with before. A host that is up but not serving is not done. Only now make the entry the default (`grubby --set-default` on Red Hat-family, or the distribution's configuration) and record the date.

### 6. Roll back, or patch live

Rollback is selecting the previous entry at boot (from the console, or by `grub-reboot` to the old entry) and then holding the package version or excluding the kernel in the package manager so the next run does not reinstall it. Find out why it failed before the next attempt; the same update will fail the same way.

A livepatch (kernel live patching services, kpatch) applies selected security fixes to the running kernel without a reboot. It buys time for fixes the vendor chose to cover; it does not replace the reboot, which is still needed for everything else. Use it when a reboot cannot happen inside the exposure window, and schedule the reboot anyway.

## Output format

```markdown
## Preconditions
[Console tested, rollback kernel, Secure Boot state.]

## Checks on the new kernel
[dkms status, initramfs content, anything rebuilt.]

## Rollout order
[Canary, batches, drain method, stop conditions.]

## Verification
[Per host: uname -r, failed units, service health; default set on what date.]
```

## Anti-patterns

**Default first.** A failed boot then needs a person at the console.

**Removing the old kernel in the same run.** The rollback target is gone before it is needed.

**Trusting the package manager's exit code.** A DKMS failure can be reported as a warning while the package installs.

**Rebooting every replica together.** The redundancy is spent at once.

**Calling a livepatch a patched host.** It covers selected fixes only.

## Reference files

- `references/preflight-and-batches.md` - read at steps 2 and 4: a preflight checklist per distribution family and a batch plan template.
