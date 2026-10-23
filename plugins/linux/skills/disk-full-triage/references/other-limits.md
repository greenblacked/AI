# Other limits behind "No space left on device"

## Contents

- Quota
- LVM thin pool
- btrfs
- XFS
- Deleted-open files on a network filesystem

## Quota

Per-user or per-project limits report the same error while `df` shows free space.

```bash
quota -s -u USER
repquota -a
```

On XFS project quotas use `xfs_quota -x -c 'report -p' /mount`. The fix is a higher limit or removing that owner's data; free space on the filesystem does not help.

## LVM thin pool

A filesystem on a thin volume can believe it has space while the pool underneath is full, and writes then fail or the volume goes read-only.

```bash
lvs -o lv_name,vg_name,lv_size,data_percent,metadata_percent
```

Check both the data and the metadata percentage. A full metadata area fails writes even when data is low. Extend the pool or free blocks the pool can reclaim (discard, `fstrim -v /mount`) before anything else; do not keep writing into a pool at 100%.

## btrfs

`df` is unreliable on btrfs. Use:

```bash
btrfs filesystem usage /mount
btrfs filesystem df /mount
```

An error with apparent free space is often fully allocated chunks with no room for new metadata. A filtered balance of data chunks (`btrfs balance start -dusage=10 /mount`) returns nearly empty chunks to the pool; run it only when there is some headroom, and expect I/O load. Snapshots also hold space that deleting the live files does not free: list them with `btrfs subvolume list /mount`.

## XFS

XFS allocates inodes dynamically, so inode exhaustion is rarer, but an `inode64` mismatch or a tiny `maxpct` can still produce it. Check `xfs_info /mount` and `df -i`. XFS cannot be shrunk, which matters when the answer is a resize.

## Deleted-open files on a network filesystem

On NFS an open deleted file becomes a `.nfsXXXX` file in the directory rather than disappearing. Those are removed when the last client closes them; do not delete them by hand while a client holds them.
