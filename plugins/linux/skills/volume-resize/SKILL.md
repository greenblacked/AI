---
name: volume-resize
description: "Grow, or carefully shrink, a disk, partition, LVM volume or filesystem: \"extend /var after the EBS resize\", \"lvextend but df shows the old size\", \"can I shrink this xfs\". The ordering is the skill: capture lsblk and df first, confirm a snapshot or backup, then grow bottom-up (rescan the device, growpart, pvresize, lvextend -r, or resize2fs / xfs_growfs on the mounted path) and compare lsblk and df after. Know the asymmetries: xfs cannot shrink, ext4 shrinks only offline with the filesystem reduced before the volume, and shrinking is really a migration. Check thin-pool data and metadata percentages, LUKS layers and the cloud provider's resize cooldown. Use for any capacity change to an existing volume. Not for finding what filled the disk (disk-full-triage), a failing device (disk-failure-replacement) or Kubernetes PVC expansion (k8s-storage)."
allowed-tools: Bash(lsblk:*), Bash(df:*), Bash(findmnt:*), Bash(pvs), Bash(vgs), Bash(lvs), Bash(lvs -a -o +devices), Bash(pvdisplay), Bash(vgdisplay), Bash(lvdisplay), Bash(xfs_info:*), Bash(cryptsetup status:*), Bash(multipath -ll), Read, Glob, Grep
---

# Volume Resize

This skill is done when the new size shows at every layer (`lsblk` for the device and partition, `pvs`/`lvs` for LVM, `df` for the filesystem), the filesystem is mounted and clean, and a restore point existed before the first command.

The usual failure is a half-finished stack. The cloud console says 200 GiB, `lsblk` shows the disk grown, and `df` still shows 100 GiB because the partition, the physical volume or the filesystem was never extended; or the opposite, a volume shrunk below its filesystem. Growing is safe when done bottom-up and checked at each layer. Shrinking is where data is lost, because the order flips and several filesystems cannot do it at all.

## Scope

Use for: extending a disk, partition, physical volume, logical volume or filesystem after more space was added, and planning a reduction.

Do not use for: finding what consumed the space (`disk-full-triage`); a device that is failing or replacing a member (`disk-failure-replacement`); expanding a Kubernetes PersistentVolumeClaim, which goes through the storage class and the cluster (`k8s-storage`, in the platform plugin).

## Workflow

### 1. Capture the stack before changing anything

```bash
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
df -hT
findmnt -no SOURCE,FSTYPE /var
pvs; vgs; lvs -a -o +devices
```

Write down which layers exist between the physical disk and the mount: bare partition, LVM, LUKS (`TYPE crypt` in `lsblk`), software RAID, multipath. The commands differ per layer and the order is fixed by the stack: you grow from the bottom to the top. Note the filesystem type, which decides the tool: `ext4` uses `resize2fs`, `xfs` uses `xfs_growfs`, `btrfs` uses `btrfs filesystem resize`.

### 2. Make sure you can go back

Take a snapshot of the volume at the provider (EBS snapshot, managed-disk snapshot, persistent-disk snapshot) or confirm a backup restored successfully recently. An LVM snapshot lives on the same volume group and disappears with it; it is a way back from a bad edit, not a backup. For a shrink this step is not optional. Do not combine the resize with an unrelated change (a kernel update, a mount option edit, a repartition for another purpose): when something fails, the cause must be this change.

### 3. Grow the device

Cloud and virtual disks first: resize at the provider, and read the cooldown. On AWS, after modifying an EBS volume you must wait before modifying the same volume again (the documented minimum is six hours, and it may be in the `optimizing` state, which is usable). Other providers differ on online resize and whether it needs a stop; read theirs before starting.

Make the guest see the new size:

```bash
echo 1 | sudo tee /sys/class/block/sdb/device/rescan      # SCSI/virtio-scsi disks; NVMe and virtio-blk usually see it on their own
lsblk /dev/sdb                                             # the disk now shows the new size
multipath -ll                                              # multipath: resize each path, then multipathd resize map NAME
```

If `lsblk` still shows the old size, stop. Nothing above the device can grow until it does.

### 4. Grow the partition, if there is one

```bash
sudo growpart /dev/sda 3         # disk and partition number as separate arguments
lsblk /dev/sda
```

`growpart` (package `cloud-guest-utils` or `cloud-utils-growpart`) extends the partition into the free space following it; the partition must be the last on the disk or have free space directly after it. It moves the GPT backup header as well. On cloud images, cloud-init may already do this for the root partition at boot, so check before running it. A whole disk used as a physical volume or filesystem has no partition, so skip this step.

### 5. LUKS, if present

For a LUKS container on the partition, extend the mapping before anything inside it: `sudo cryptsetup resize NAME` (where NAME is the mapper name from `lsblk`; on LUKS2 it may ask for a passphrase, so have it to hand).

### 6. Grow LVM, then the filesystem

```bash
sudo pvresize /dev/sda3                    # on a LUKS stack the PV is the mapper device: pvresize /dev/mapper/NAME
vgs                                        # VFree now shows the new space
sudo lvextend -r -L +20G /dev/vg0/var      # or: -l +100%FREE
```

`-r` (`--resizefs`) runs the matching filesystem resize in the same step, which is what prevents the classic "lvextend worked but df shows the old size": the logical volume grew and the filesystem did not. Without LVM, or if you extended the LV without `-r`, grow the filesystem on its own:

```bash
sudo resize2fs /dev/vg0/var                # ext4: mounted or unmounted, growing works online
sudo xfs_growfs /var                       # xfs: takes the mount point, not the device
sudo btrfs filesystem resize max /var      # btrfs
```

If the volume group has no free space, add a disk with `pvcreate` and `vgextend` first.

### 7. Check thin pools before adding thin volumes

```bash
sudo lvs -a -o+data_percent,metadata_percent
```

Thin-provisioned volumes can promise more than the pool holds. A thin pool whose data or metadata reaches 100 percent stops writes or goes read-only, and metadata exhaustion is harder to repair than data. Extend the pool (`lvextend` on the pool's data and `--poolmetadatasize` for metadata) before extending or creating thin volumes, and check the `autoextend` settings in `lvm.conf`.

### 8. Verify against the capture

```bash
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
df -hT /var
```

Every layer shows the new size, the filesystem is mounted, and `dmesg -T | tail` has no filesystem errors. Compare with step 1. Use an application-level check as well: a write that was failing for lack of space now succeeds.

### 9. Shrinking, if you must

Shrinking is a migration, not an edit. xfs cannot be shrunk at all. ext4 shrinks only unmounted, with the filesystem reduced before the volume or partition, and a mistake in the order (volume first) truncates data that cannot be recovered.

Prefer the safe route: create a new, smaller volume, copy with `rsync -aHAX --numeric-ids`, stop writers, run a final sync, cut over the mount, keep the old volume until the new one has run through a full cycle. When a true in-place shrink is unavoidable (ext4 on LVM), read `references/shrink-and-pitfalls.md` for the sequence: unmount, `e2fsck -f`, `resize2fs` to a target below the new LV size, `lvreduce`, then grow the filesystem back to fill the LV. Never shrink the root filesystem of a running machine.

## Output format

```markdown
## Before
[lsblk, df, the layer stack, filesystem type.]

## Restore point
[Snapshot id or backup and when verified.]

## Steps run
[Each command in order with the layer it affected.]

## After
[lsblk and df at every layer; thin pool percentages if relevant.]
```

## Anti-patterns

**Resizing the filesystem first.** It cannot grow into space the layer below has not got.

**Passing a device to xfs_growfs.** It wants the mount point.

**Shrinking the volume before the filesystem.** The tail of the filesystem is cut off.

**Treating an LVM snapshot as the backup.** It dies with the volume group.

**Resizing and repartitioning for another reason together.** A failure then has two possible causes.

## Reference files

- `references/shrink-and-pitfalls.md` - read at step 9 and when a step fails: the ext4-on-LVM shrink sequence, the migration cut-over checklist, and common failure messages with causes.
