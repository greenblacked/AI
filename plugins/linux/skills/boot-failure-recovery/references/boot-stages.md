# Boot stages

## Contents

- Stage table
- Reading the console
- Targets and what blocks them

## Stage table

| Stage | Signs | Likely causes | Next step |
| --- | --- | --- | --- |
| Firmware | Nothing from the disk, "no bootable device" | Wrong boot order, missing EFI entry, detached disk | Check boot order, attached volumes; cloud: check volume attachment |
| Bootloader | GRUB prompt or "grub rescue", error about missing file | Damaged or moved /boot, config pointing at wrong device | Rescue environment; reinstall bootloader once the cause is known |
| Kernel | Kernel panic early, "VFS: Unable to mount root fs" | Missing root driver, wrong root= argument | Boot the previous kernel entry; compare root= with blkid |
| Initramfs | Drops to `(initramfs)` or dracut emergency shell, "cannot find root device" | Missing module, changed root UUID, encrypted volume not unlocked | See `rescue-procedures.md`; check `/proc/cmdline` against `blkid` |
| Root mount | Root mounted read-only, filesystem check failing | Dirty filesystem, hardware errors | Run fsck on the unmounted root from rescue; if I/O errors appear, escalate as hardware |
| Units | "Welcome to emergency mode", failed local-fs | fstab entry for a missing device, failed mount | See step 4 of SKILL.md |
| Late units | Login prompt present but services missing | Failed units after the target | Use `systemd-unit-failure` |

## Reading the console

- Kernel messages stay on screen only briefly; boot with `systemd.log_level=debug` or remove `quiet` from the kernel command line (edit once at the bootloader with `e`) to see more.
- `journalctl -xb` in emergency mode shows the failing unit's explanation.
- A line such as "A start job is running for /dev/disk/by-uuid/..." names the exact missing device; run `ls -l /dev/disk/by-uuid/` and compare.

## Targets and what blocks them

`emergency.target` gives a minimal root shell with nothing but root mounted. `rescue.target` starts basic services and local mounts. `local-fs.target` fails when a mount that is not `nofail` fails, which causes the fall to emergency mode. Mounts marked `nofail` do not block it. The kernel option `systemd.unit=rescue.target` selects the target for one boot only.
