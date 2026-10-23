# Preflight and batch plan

## Preflight checklist

Tick every line for each host class before the first reboot.

- [ ] After the install, the default boot entry still names the rollback kernel
      (`grubby --default-kernel` or `grub-editenv list`). `UPDATEDEFAULT=yes` on Red Hat family
      and `GRUB_DEFAULT=0` on Debian family move it to the new kernel on their own.

- [ ] Console access tested (BMC, hypervisor or serial console), with credentials that work
      today.
- [ ] Current kernel recorded (`uname -r`) and at least one older kernel installed and
      listed in the boot menu.
- [ ] New kernel package installed, files for its version present in `/boot`.
- [ ] `dkms status` shows every module installed for the new version.
- [ ] Initramfs for the new version contains the storage, RAID, LVM, encryption and network
      drivers this host's root needs.
- [ ] Secure Boot state known (`mokutil --sb-state`); if enabled, module signing key
      enrolled and modules signed.
- [ ] One-shot boot mechanism confirmed for this host (`GRUB_DEFAULT=saved` for GRUB;
      boot counting for systemd-boot).
- [ ] `panic=` on the command line (or a hardware watchdog) so a hung boot resets.
- [ ] Application owner informed; traffic drained or redundancy confirmed.
- [ ] Verified backup or snapshot of anything stateful on the host.

## Where each distribution keeps what you check

| Item | Debian family | Red Hat family |
| --- | --- | --- |
| Reboot required flag | `/var/run/reboot-required` | `needs-restarting -r` (exit status 1 means reboot needed) |
| Initramfs listing | `lsinitramfs FILE` | `lsinitrd FILE` |
| Rebuild initramfs | `update-initramfs -u -k VER` | `dracut --force FILE VER` |
| One-shot boot | `grub-reboot` | `grub2-reboot` |
| Set default | `GRUB_DEFAULT` and `update-grub` | `grubby --set-default FILE` |
| Kernels kept | until `apt autoremove` | `installonly_limit` in the package manager configuration |

## Batch plan template

| Batch | Hosts | Why this group | Traffic handling | Check before next batch | Stop if |
| --- | --- | --- | --- | --- | --- |
| 0 canary | one per role | representative, low blast radius | drained | soak period, health, error rate | any failed unit or fallback |
| 1 | replicas, one per cluster | cluster stays quorate | drained | same | any member does not rejoin |
| 2 | remaining replicas | | | | |
| 3 | primaries, one cluster at a time | after failover rehearsed | planned failover | | |

## When a host fell back

The old kernel came up because the one-shot or counting mechanism worked. That is the
design succeeding. Collect the evidence before trying again: the console log of the failed
boot, `journalctl -b -1 -k` from the fallback boot, `dkms status`, and the initramfs
listing. Fix the cause on that host, then repeat on it before rolling further.
