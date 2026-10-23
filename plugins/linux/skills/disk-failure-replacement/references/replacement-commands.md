# Replacement commands and reading SMART

## SMART attributes that matter

| Attribute | Meaning | What a rising value suggests |
| --- | --- | --- |
| 5 `Reallocated_Sector_Ct` | Sectors the drive has remapped | Failing media; replace once it keeps growing |
| 187 `Reported_Uncorrect` | Errors the drive could not correct | Failing media |
| 197 `Current_Pending_Sector` | Sectors waiting to be remapped | Unreadable sectors now; a rebuild may hit them |
| 198 `Offline_Uncorrectable` | Sectors that failed an offline scan | Failing media |
| 199 `UDMA_CRC_Error_Count` | Transfers corrupted on the link | Cable, backplane or controller, not the media |
| 9 `Power_On_Hours` | Age | Context for the decision, not a fault |

Attribute numbers and names vary by vendor; read the raw values and the vendor's
documentation. For a SAS drive, read the error counter log that `smartctl -a` prints.
`smartctl -t long /dev/sdX` starts a long self-test (needs approval; it adds load).

## Imaging a failing disk before any repair

`ddrescue` copies what it can and records what it could not read in a mapfile, so the
copy can resume and retry.

```bash
ddrescue -f -n /dev/sdX /mnt/spare/sdX.img /mnt/spare/sdX.map     # first pass, skip scraping
ddrescue -f -r3 /dev/sdX /mnt/spare/sdX.img /mnt/spare/sdX.map    # then retry bad areas three times
```

The destination must be a different, larger device. Run any `fsck` against the image or a
loop device, not the original.

## ZFS

- `zpool status -x` lists only unhealthy pools; `zpool status -v` includes files with
  permanent errors.
- Replace in place when the new disk goes in the same slot: `zpool replace POOL DEVICE`.
  With a different device: `zpool replace POOL OLD NEW`. Use `/dev/disk/by-id/` names so the
  pool does not depend on enumeration order.
- During a resilver the pool is usable but has reduced redundancy. After it completes run
  `zpool scrub POOL`, and `zpool clear POOL` only once the cause is fixed.

## LVM

- For an LVM mirror or RAID logical volume, `lvs -a -o +devices` shows which physical
  volume each leg sits on and the health attribute.
- Add the replacement: `pvcreate /dev/sdX1`, `vgextend VG /dev/sdX1`.
- Repair: `lvconvert --repair VG/LV`, then `vgreduce --removemissing VG` after the repair
  succeeds.
- A plain linear volume has no redundancy; there is nothing to repair, only a restore.

## mdadm details

- `mdadm --detail /dev/md0` shows state, failed and spare counts and each member's role.
- `mdadm --examine /dev/sdX1` shows the superblock on a member, useful to confirm which
  array a loose disk belonged to before adding it.
- Add a hot spare in advance by adding a disk to a healthy array; it takes over
  automatically on a failure.

## Boot loader on the replacement

For a BIOS install, run the distribution's boot loader installer against the new disk. For
UEFI, make sure the EFI system partition is mirrored or copied and that a boot entry points
at it. Test by confirming the firmware lists the entry; a full test needs a window with
console access.
