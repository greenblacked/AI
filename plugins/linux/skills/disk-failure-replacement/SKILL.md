---
name: disk-failure-replacement
description: "Handle a failing or failed disk in mdadm, ZFS or LVM mirrors. Use for \"mdadm array is degraded\", \"SMART says reallocated sectors\", \"zpool shows DEGRADED\" or \"filesystem remounted read-only after I/O errors\". Confirm the failure from the kernel and the drive, not one tool: dmesg I/O errors, smartctl -a (reallocated, pending and CRC counts split media from cabling), mdadm --detail or zpool status. Identify the physical disk by serial number before pulling anything, check the surviving disks' SMART before a rebuild stresses them, and confirm a verified backup first. Then replace in order: fail and remove, copy the partition table, add, watch /proc/mdstat or the resilver. After a read-only remount do not fsck a degraded device until it is imaged. Record the serial and date. Not for space (disk-full-triage), growing volumes (volume-resize) or backup strategy (backup-recovery-design)."
allowed-tools: Bash(zpool status), Bash(zpool status -v), Bash(zpool status -x), Bash(zpool list:*), Bash(lsblk:*), Bash(lvs), Bash(lvs -a -o +devices), Read, Glob, Grep
---

# Disk Failure Replacement

This skill is done when the failed disk is identified by serial number, the array is back to full redundancy on a new disk with a completed rebuild or resilver, a scrub or check has passed, and the swap is recorded with the old and new serial numbers and the date.

The usual failure is pulling the wrong disk. A device name like `/dev/sdb` can change between boots, and a degraded array has no redundancy left to forgive the mistake. The second failure is starting a rebuild on survivors that are themselves failing: a rebuild reads every sector of every remaining disk, which is the load most likely to expose the next fault, and the second failure during a rebuild is how a single-disk problem becomes data loss.

## Scope

Use for: a degraded mdadm array, ZFS pool or LVM mirror; SMART warnings; I/O errors in the kernel log; a filesystem that went read-only after errors.

Do not use for: running out of space (`disk-full-triage`); growing a volume or filesystem (`volume-resize`); designing backups (`backup-recovery-design`). Hardware RAID controllers have their own vendor tools and are outside this procedure, though steps 1 to 3 apply.

## Workflow

### 1. Confirm the failure from more than one place

```bash
dmesg -T | grep -iE 'I/O error|blk_update_request|ata[0-9]+|nvme|medium error|reset'
smartctl -H /dev/sdX
smartctl -a /dev/sdX
mdadm --detail /dev/md0 ; cat /proc/mdstat      # md
zpool status -v                                  # ZFS
lvs -a -o +devices                               # LVM
```

Read the SMART attributes by what they say. `Reallocated_Sector_Ct` (5), `Current_Pending_Sector` (197) and `Offline_Uncorrectable` (198) rising point at failing media. `UDMA_CRC_Error_Count` (199) points at the cable, backplane or connector, not the disk; reseat or replace the cable and watch whether the count stops rising before condemning the drive. On NVMe, `smartctl -a /dev/nvme0` reports media and data integrity errors, available spare and percentage used. A `PASSED` overall health result does not clear a drive that has the counters above, and `FAILED` is rarely the first sign.

### 2. Stabilise before touching hardware

- Make sure a backup exists and has been restored from, or at least verified, recently. Starting a rebuild without one is a bet with the whole pool.
- Check the SMART data of the surviving disks the same way. If a survivor is also reporting pending sectors, plan for a second replacement and a copy of the data first.
- Reduce load where possible: pause batch jobs and heavy reads for the rebuild window.
- If the filesystem has gone read-only after errors, do not run `fsck` on a degraded or erroring device. Image it first (read `references/replacement-commands.md`), so the repair works on a copy.

### 3. Identify the physical disk

Names are not identities. Collect the serial number and match it to a slot.

```bash
smartctl -i /dev/sdX | grep -iE 'serial|model'
lsblk -o NAME,SERIAL,MODEL,SIZE,WWN
ls -l /dev/disk/by-id/ | grep -v part
```

Match the serial to the label on the drive, the enclosure's slot view, or by blinking the slot LED (`ledctl locate=/dev/sdX` from the `ledmon` package, or the controller's locate command). Have a second person confirm the slot when the host is production. If the serial cannot be matched to a slot, do not pull anything; offline the array member, see which activity light stops, and decide from that.

### 4. Replace, in order

mdadm, with the member names from `mdadm --detail`:

```bash
mdadm /dev/md0 --fail /dev/sdX1          # skip if already marked faulty
mdadm /dev/md0 --remove /dev/sdX1
# swap the disk, then copy the partition layout from a surviving member
sfdisk -d /dev/sdY | sfdisk /dev/sdX     # MBR only; it would copy GPT GUIDs and leave two disks with the same identifiers
# GPT: sgdisk -R=/dev/sdX /dev/sdY, then sgdisk -G /dev/sdX to randomise the GUIDs
mdadm /dev/md0 --add /dev/sdX1
watch -n 5 cat /proc/mdstat
```

Check the direction of the partition copy twice: the source is the healthy disk. Getting it backwards overwrites the surviving layout. ZFS:

```bash
zpool offline POOL OLD-DEVICE            # if not already offline
zpool replace POOL OLD-DEVICE NEW-DEVICE
zpool status -v POOL                     # resilver progress and errors
```

LVM mirrors and RAID logical volumes: add the new physical volume to the group and repair with `lvconvert --repair VG/LV`, then remove the missing device from the group with `vgreduce --removemissing VG` once the repair completes. Details are in the reference. If the failed disk held the boot loader or the EFI system partition, install the boot loader on the new disk too, or the host will not boot if the other disk fails next.

### 5. Watch the rebuild, keep the load low

Follow `/proc/mdstat` or `zpool status` until it reports completion. Rebuild speed is governed by `/proc/sys/dev/raid/speed_limit_min` and `speed_limit_max`; raising the minimum speeds the rebuild at the cost of foreground latency, so change it knowingly. Watch the kernel log and the survivors' SMART counters during the rebuild. A new error on a survivor means stop and reassess, not continue.

### 6. Verify, then record

When the rebuild ends, run a consistency check: for md, `echo check | sudo tee /sys/block/md0/md/sync_action` and read `mismatch_cnt` afterwards; for ZFS, `zpool scrub POOL`. Confirm the array reports a clean state and the monitoring alert for degraded redundancy has cleared. Update `mdadm.conf` or the equivalent if the configuration lists devices, and rebuild the initramfs if the distribution requires it. Record the old disk's serial and slot, the new disk's serial, the date, the SMART evidence and the rebuild duration in the asset log. Wipe or destroy the old drive according to the data policy before it leaves the building.

## Output format

```markdown
## Evidence
[Kernel messages, SMART attributes, array state.]

## Disk identification
[Serial, slot, how matched, who confirmed.]

## Safety checks
[Backup verified, survivor SMART, load reduced.]

## Replacement
[Commands run, rebuild duration, scrub result.]

## Record
[Old and new serials, date, follow-ups.]
```

## Anti-patterns

**Pulling by device name.** `/dev/sdb` is not a slot.

**Rebuilding on failing survivors.** The rebuild is the stress that kills them.

**Replacing a disk for a cable fault.** A rising CRC count with clean media counters points at the connection.

**fsck on a degraded device.** A repair on failing media can destroy what could be recovered.

**Forgetting the boot loader.** The next failure then takes the host down.

## Reference files

- `references/replacement-commands.md` - read at steps 2 and 4: imaging a failing disk, ZFS and LVM replacement details, and a SMART attribute table.
