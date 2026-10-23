# Rescue procedures

## Contents

- Chroot into an installed system
- Rebuild the initramfs
- Regenerate the bootloader configuration
- Debug options for one boot
- Slow-boot checks

## Chroot into an installed system

From a rescue image, a helper instance with the root volume attached, or a live medium. Names below are examples; confirm devices with `lsblk -f` first.

```bash
mount /dev/ROOT_DEVICE /mnt
mount /dev/BOOT_DEVICE /mnt/boot              # if /boot is separate
mount /dev/EFI_DEVICE /mnt/boot/efi           # on UEFI systems
for d in dev proc sys run; do mount --rbind /$d /mnt/$d; done
chroot /mnt /bin/bash
```

Edit `/etc/fstab` there, run `findmnt --verify`, then leave the chroot and unmount in reverse order before returning the volume.

## Rebuild the initramfs

Only after the cause is named (for example, a kernel installed without its image, or a new storage driver needed).

| Family | Command |
| --- | --- |
| Debian and Ubuntu | `update-initramfs -u -k VERSION` |
| RHEL, Fedora, derivatives | `dracut -f --kver VERSION` |
| Arch | `mkinitcpio -p PRESET` |

Rebuild only the kernel being repaired, named by VERSION (as in `uname -r` or the name under `/lib/modules`). Leave the known-good previous kernel's image alone: it is the fallback boot entry, and a rebuild of every kernel at once can break both entries on one bad change.

Check that the image exists in `/boot` for the kernel you intend to boot, and that the encryption or RAID configuration the root needs is present in `/etc/crypttab` or `/etc/mdadm`.

## Regenerate the bootloader configuration

| Family | Command |
| --- | --- |
| Debian and Ubuntu | `update-grub` |
| RHEL family on BIOS | `grub2-mkconfig -o /boot/grub2/grub.cfg` |
| RHEL family on UEFI | `grub2-mkconfig -o /boot/grub2/grub.cfg` (the path may differ by release; confirm under /boot/efi/EFI) |

Reinstalling the bootloader to the disk (`grub-install`) is a separate, heavier step; use it when the bootloader itself is missing or damaged, not for a bad configuration.

## Debug options for one boot

Edit the kernel line once at the bootloader (press `e`, then boot with the key shown):

| Option | Effect |
| --- | --- |
| `systemd.unit=rescue.target` | Boot to rescue mode |
| `systemd.unit=emergency.target` | Boot to minimal emergency shell |
| `rd.break` | Stop in the initramfs before root is switched (dracut-based systems) |
| `systemd.log_level=debug` | Verbose systemd logging |
| remove `quiet` | Show kernel and unit messages |

These apply to one boot and are not saved.

## Slow-boot checks

1. `systemd-analyze` splits time into firmware, loader, kernel, initrd and userspace; start with the largest.
2. `systemd-analyze critical-chain` for userspace; add the unit name to see the chain for a given unit.
3. Check device timeouts: `grep -E 'x-systemd|nofail' /etc/fstab`.
4. `systemctl list-jobs` during a stuck boot shows what is waiting.
