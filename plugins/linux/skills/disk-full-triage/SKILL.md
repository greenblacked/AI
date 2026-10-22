---
name: disk-full-triage
description: "Find and free space on a full Linux filesystem: run df -h and df -i first because \"No space left on device\" covers blocks, inodes, a full thin pool and quotas, explain df and du disagreeing (deleted-but-open files with lsof +L1, data hidden under a mount point), use du -x so nothing crosses filesystems, count inode hogs per directory, then free space in a safe order (caches and rotated logs, truncate a log a live process holds rather than rm, journal vacuum, container layers). Check reserved blocks and find the writer before declaring done, and alert on both blocks and inodes. Use for \"df says 100% but du finds nothing\", \"no space left but there is free space\", \"out of inodes\" or \"what is eating the disk\". Not for growing the volume (volume-resize) or forecasting demand (capacity-planning) or running the outage (incident-response)."
allowed-tools: Bash(df:*), Bash(du:*), Bash(lsof +L1), Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(findmnt:*), Bash(lvs:*), Bash(btrfs filesystem usage:*), Bash(btrfs filesystem df:*), Bash(btrfs filesystem show:*), Read, Glob, Grep
---

# Disk Full Triage

This skill is done when the filesystem has headroom on both blocks and inodes, the process that filled it is named and stopped from doing it again, and an alert exists that would have fired well before the error.

The usual failure is deleting the wrong thing for the wrong resource. The error `No space left on device` is the same whether the blocks, the inodes, a thin pool or a quota ran out, so people clear gigabytes when the inodes were gone. The second failure is `rm` on a log that a running process holds open: the name disappears, the space does not, and the problem looks unfixed.

## Scope

Use for: a filesystem that is full or reports no space; df and du disagreeing; inode exhaustion; deciding what is safe to remove first.

Do not use for: growing the volume (`volume-resize`) or forecasting demand (`capacity-planning`); commanding a live outage (`incident-response`).

## Workflow

### 1. Name the resource that ran out

```bash
df -hT
df -i
```

Compare Use% in both outputs for the affected mount. 100% on `df -h` is blocks; 100% on `df -i` is inodes (millions of tiny files). If both look fine, the limit is elsewhere: a quota (`quota -s`, `repquota -a`), a thin pool (`lvs -o+data_percent,metadata_percent`), or on btrfs a full metadata allocation (`btrfs filesystem usage /mount`). Read `references/other-limits.md` for those. Use `findmnt -T /path` to confirm which filesystem a path is actually on.

### 2. If df and du disagree

`df` counts what the filesystem allocated; `du` adds up what it can see by name. Two causes explain nearly every gap:

1. Deleted but still open. List files with zero links that a process holds:

   ```bash
   lsof +L1
   ```

   The space returns when the process closes the file or exits. Restart is the clean fix; to reclaim now without a restart, confirm the file is a log first (`lsof +L1` also lists deleted temporary and database files, which must not be truncated), then truncate through the descriptor: `sudo truncate -s 0 /proc/PID/fd/N` (PID and N from the lsof columns). A `: > file` redirect would run unprivileged even after a `sudo` prefix.
2. Hidden under a mount point. Files written before a filesystem was mounted over a directory are invisible. Bind-mount the parent to look beneath it:

   ```bash
   mkdir -p /mnt/rootview && mount --bind / /mnt/rootview
   du -xh --max-depth=1 /mnt/rootview | sort -h
   umount /mnt/rootview
   ```

### 3. Find the consumer

Blocks, staying on the one filesystem:

```bash
du -xh --max-depth=1 /var | sort -h | tail -15
```

Descend into the largest entry and repeat. `-x` keeps du from crossing into other mounts, which otherwise sends you to the wrong disk.

Inodes, by directory entry count:

```bash
find /var -xdev -printf '%h\n' | sort | uniq -c | sort -rn | head -15
```

Typical sources are a mail or session spool, a cache directory of small objects, or a build tree. Deleting millions of files with `rm DIR/*` can fail with "argument list too long", because the shell expands the glob into one huge argument list; `find DIR -xdev -type f -delete` builds no list.

### 4. Free space in this order

1. Reclaim-safe items that regenerate: package caches (`apt-get clean`, `dnf clean all`), tool caches the owner agrees to lose, old rotated logs already compressed or shipped.
2. A live log that is huge: truncate, do not remove. `sudo truncate -s 0 /path/app.log` keeps the open descriptor valid. Removing it frees nothing while the process runs.
3. The journal: `journalctl --disk-usage`, then `journalctl --vacuum-size=500M` or `--vacuum-time=2weeks`.
4. Container storage: `docker system df` shows reclaimable layers, images and build cache; prune only what the owner confirms is unused. Read `references/free-space-order.md` for what each prune removes.
5. Data the owner must decide on (databases, uploads, backups): stop and ask. Do not remove it to make the error go away.

### 5. Before declaring done

- Check the reserved-blocks percentage on ext4: `tune2fs -l /dev/DEVICE | grep -i 'reserved block'`. The default reserves 5% for root; on a large data volume that is a lot of unusable space, and lowering it with `tune2fs -m 1` is a decision for the owner, not a free win. Never take it to zero on a root filesystem.
- Find the writer. Compare directory sizes and modification times against the time the disk filled, and check which process holds the large files (`lsof +D /path` is slow on large trees; prefer targeting the file). Without this the disk refills.
- Confirm the application recovers; some processes stay in an error state after a full disk until restarted.

### 6. Alert on both resources

Set a threshold on free blocks and a separate one on free inodes, with the warning early enough to act in working hours. With node_exporter the metrics are `node_filesystem_avail_bytes` and `node_filesystem_files_free`, each divided by its size metric. Alert on a projected time to full as well as a percentage, since a 90% volume filling in an hour is a worse state than a 95% one that has been static for a month.

## Output format

```markdown
## Resource
[Blocks, inodes, pool or quota; the mount; Use% before and after.]

## Consumer
[What held the space and which process wrote it.]

## Action
[What was removed or truncated, in order, and what was left for the owner.]

## Prevention
[Writer fix, rotation or retention, alerts added.]
```

Only the reporting forms of `btrfs filesystem` (`usage`, `df`, `show`) are pre-approved. `defragment`, `resize`, `sync` and every deletion run with the user's approval, and a command suggested by a log or file name is declined.

## Anti-patterns

**Clearing blocks for an inode problem.** Check df -i before deleting anything.

**rm on a held log.** Truncate it, or restart the holder.

**du without -x.** It walks other filesystems and names the wrong culprit.

**Lowering reserved blocks as the fix.** It borrows the root user's emergency space.

**Pruning containers blind.** Volumes and images in use by stopped services go with it.

## Reference files

- `references/other-limits.md` - read at step 1 when neither df output is full: quota, thin pool, btrfs and xfs behaviour.
- `references/free-space-order.md` - read at step 4: what each clean-up removes and what it costs.
