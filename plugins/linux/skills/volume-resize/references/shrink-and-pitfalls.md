# Shrinking and common failures

## Contents

- Decision: can this shrink in place
- ext4 on LVM, offline shrink
- Migration cut-over checklist
- Failure messages and causes
- Cloud resize notes

## Decision: can this shrink in place

| Filesystem | In-place shrink | Notes |
| --- | --- | --- |
| xfs | No | Migrate to a smaller volume (copy with `xfsdump`/`xfsrestore` or `rsync`) |
| ext4 | Yes, unmounted only | Needs a clean `e2fsck -f` first |
| btrfs | Yes, online | `btrfs filesystem resize -10G /mnt`; then shrink the underlying device to no less than the filesystem |
| zfs, others | Not covered here | Follow the filesystem's own documentation |

The root filesystem of a running system cannot be unmounted; shrinking it means booting from rescue media. At that point a migration is usually safer.

## ext4 on LVM, offline shrink

Target: reduce a logical volume to 50 GiB, with data well below that.

```bash
df -h /data                       # data in use must fit with margin
umount /data                      # stop services first; lsof +f -- /data shows holders
e2fsck -f /dev/vg0/data           # required before resize2fs will shrink
resize2fs /dev/vg0/data 48G       # filesystem a little smaller than the target LV
lvreduce -L 50G /dev/vg0/data     # now the volume
resize2fs /dev/vg0/data           # grow the filesystem to fill the 50G LV exactly
e2fsck -f /dev/vg0/data
mount /data
```

The two-step sizing leaves a safety margin: the filesystem is reduced below the final LV size, the LV is reduced, and the filesystem is expanded to the exact LV size. Shrinking the LV before the filesystem, or to a size smaller than the filesystem, destroys data. `lvreduce -r -L 50G` performs the filesystem step for you (it calls the filesystem's resize tool, `fsadm`) and refuses when the filesystem does not fit; it is still worth the snapshot and the unmount.

## Migration cut-over checklist

1. Create the new volume at the target size, make the filesystem, mount it at a temporary path.
2. First copy while live: `rsync -aHAX --numeric-ids /data/ /mnt/new/` (the trailing slashes matter).
3. Stop writers (service stop, or remount read-only).
4. Final copy with `--delete` to catch the delta, then compare: `rsync -aHAXn --delete --itemize-changes /data/ /mnt/new/` should list nothing.
5. Swap the mount: edit `/etc/fstab` (use UUID from `blkid`), `umount` both, mount the new volume at the real path, `mount -a` to prove the fstab line.
6. Start the service and run the application check.
7. Keep the old volume untouched and unmounted for a full operating cycle before deleting it.

## Failure messages and causes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `lvextend` succeeded, `df` shows the old size | Filesystem not grown | `resize2fs` or `xfs_growfs`; use `lvextend -r` next time |
| `growpart` reports `NOCHANGE` (the partition cannot be grown) | Disk not yet resized in the guest, or something sits after the partition | Rescan and recheck `lsblk`; move or remove the later partition |
| `Insufficient free space` from `lvextend` | VG has no free extents | `pvresize` the grown PV, or `vgextend` with a new PV |
| `resize2fs: Please run 'e2fsck -f'` | Filesystem flagged for check before resize | Run `e2fsck -f` unmounted, then retry |
| `xfs_growfs: ... is not a mounted XFS filesystem` | Passed a device, or not mounted | Give the mount point; mount first |
| `Thin pool ... is 100% full` or metadata at 100 percent | Overcommitted pool | Extend the pool data and metadata; do not add volumes |
| Device grew but `lsblk` unchanged | No rescan, or multipath maps not updated | Rescan each path, resize the multipath map |
| Duplicate UUID when mounting a cloned xfs volume | Two volumes share an identifier | `mount -o nouuid`, or `xfs_admin -U generate` on the clone |

## Cloud resize notes

- Resize the disk at the provider, never by detaching and recreating unless that is the plan.
- AWS: after a modification, wait the documented cooldown (six hours minimum) before modifying the same volume again, so size the request with headroom for the next period. Instance types on the Nitro system present volumes as NVMe devices named `/dev/nvme*n1`, regardless of the name given at attach time.
- Check whether the provider supports online growth for the disk type and the instance; some changes need a stop and start.
- After resizing the root disk of an instance built from a cloud image, confirm the cloud-init growpart step ran (`cloud-init status`, `lsblk`), to avoid growing twice.
