---
name: parallel-filesystem-hygiene
description: "Stop jobs from hammering a shared cluster filesystem. Counts inodes as well as bytes (lfs quota, lfs df -i), never writes one file per task per timestep to shared scratch but writes to node-local storage ($TMPDIR) and packs to one archive or HDF5 or Parquet file per task group copied out once, stages inputs in once, reads with large sequential reads, shards huge directories by hash prefix, sets striping for very large files, keeps ls and find out of job scripts, and proves the fix by comparing I/O time and metadata operations before and after. Use for \"cluster admins say I'm over the file quota\", \"ls hangs in my results directory\", \"millions of small output files\", \"my job is slow because of I/O\", \"Lustre metadata\". Not for profiling (profiling), in-file layout (array-chunking-layout), backups (backup-recovery-design) or sweep bookkeeping (sweep-campaign-management)."
allowed-tools: Bash(lfs quota:*), Bash(lfs df:*), Bash(lfs getstripe:*), Bash(df:*), Bash(sacct:*), Read, Glob, Grep
---

# Parallel Filesystem Hygiene

This skill is done when a job's output on shared storage is a small number of large files, the inode count is inside quota with headroom, the run no longer stalls on metadata, and a before and after measurement on the same job shows the change.

The usual failure is a loop that writes one small file per task per timestep straight to shared scratch. Each create, open and close is a metadata operation served by a few metadata servers shared by every user, so a thousand tasks writing ten thousand files each can slow `ls` for the whole site long before any byte limit is near. The job is then blamed on the network or on "slow disks" when the bytes were never the problem.

## Scope

Use for: a quota warning about files rather than gigabytes; directories that take minutes to list; a job whose wall time is dominated by opens, creates and stats; deciding where a new workflow should write.

Do not use for: finding which function is slow (`profiling`); choosing chunk shape and compression inside one HDF5, NetCDF or Zarr file (`array-chunking-layout`); backup and restore design (`backup-recovery-design`); tracking which sweep tasks finished (`sweep-campaign-management`); reading a table larger than memory (`out-of-core-dataset-handling`).

## Workflow

### 1. Count inodes, not only bytes

Quotas on parallel filesystems usually limit both. On Lustre:

```bash
lfs quota -u $USER /path/to/scratch      # your usage and limits: blocks and files
lfs quota -g PROJECTGROUP /path/to/scratch
lfs df -i /path/to/scratch               # inode use per metadata and object target
```

The `files` column against its limit is the number that matters here. Other filesystems have their own report (GPFS `mmlsquota`, a site `quota` wrapper); ask the site for the command rather than guessing. Do not run `find` or `du` over a tree with millions of entries to count them: that walk is itself the load you are trying to remove. Use the quota report, or count in the job's own manifest.

### 2. Find the writer

Name the code that creates the files before changing anything: one file per task, per timestep, per rank, per log line, or per checkpoint. Count how many it makes per run (tasks times steps times files per step) and how large each is. A file under a few hundred kilobytes written thousands of times is the signature. Read `references/measure-and-compare.md` for how to capture the baseline in step 9 now, before the fix, because afterwards it cannot be recovered.

### 3. Write to node-local storage during the run

Send per-step and per-task output to storage that only the job's node sees: `$TMPDIR` where the site points it at local disk or a node-local SSD, or a RAM-backed area if the site allows and the data fits. Confirm what `$TMPDIR` is on this site, because on some systems it is a shared path; `df -T "$TMPDIR"` shows the filesystem type. Local storage is cleaned when the job ends, so the copy-out in step 4 must run before the script exits, including on failure (a shell `trap` on `EXIT`).

### 4. Pack and copy out once

At the end of the run, or at coarse checkpoints, combine the small files into one container per task group and copy that one file to shared storage:

- an archive (`tar -cf group.tar -C "$TMPDIR" outputs/`), when the files are only stored and read back whole later;
- one HDF5, NetCDF or Parquet file per task group, with the task id as a column or group, when the files are read for analysis. Appending rows to one columnar file per group beats ten thousand CSVs.

Group size is a trade: large enough that the file count is small, small enough that losing one group loses little work. A few hundred tasks per file is a sensible start. Write the container under a temporary name and rename it when complete, so a half-copied file is never mistaken for a finished one.

### 5. Stage inputs once, read them sequentially

Copy shared input that every task needs to node-local storage once per node, not once per task. Read large files with large sequential reads (megabytes per call) rather than many small seeks; open a file once and keep the handle. Thousands of tasks all opening the same small configuration file at the same instant is a metadata storm; read it once and pass the values on, or stage it.

### 6. Keep directories small

Directory size slows creates and listings. Do not let one directory hold more than some tens of thousands of entries. Where many files must exist, shard by a hash prefix of the id: `results/ab/cd/<id>`, using the first two bytes of a hash, so entries spread evenly. Shard on write, so nobody has to reorganise later. Remove dead directories with the site's recommended bulk method rather than a recursive delete from many parallel jobs.

### 7. Set striping for very large files

On Lustre, striping spreads one file across several object servers. Many small files want a stripe count of 1; a single file of tens of gigabytes read or written by many ranks wants more.

```bash
lfs getstripe path/to/dir                 # current layout
lfs setstripe -c 1 results/small/         # new files in this directory: one stripe
lfs setstripe -c 8 -S 4M results/big/     # new files: 8 stripes of 4 MiB
```

Striping applies to files created after the setting, not to existing ones; to change a file, copy it into a directory with the layout you want. Pick the count from the site's guidance, since the number of object targets varies. Do not stripe small files wide: each stripe is another server contacted for no gain.

### 8. Keep listings off the hot path

Remove `ls`, `find`, `stat` and glob expansion from job scripts and polling loops. A script that globs `results/*` to see what has finished is a metadata scan per call. Track completion in a manifest or a single status file, and have tasks append to it.

### 9. Confirm the fix

Re-run the same job at the same scale and compare, as `references/measure-and-compare.md` sets out: file count created, elapsed time spent in I/O, and the job's metadata activity if the site exposes it. The change is confirmed when the inode count and the I/O time both fall, not when the code merely looks tidier. Re-read `lfs quota` afterwards and delete or archive what the old layout left behind.

## Output format

```markdown
## Quota
[Files and bytes used against limits, command and date.]

## Writer
[What creates the files, how many per run, typical size.]

## Change
[Local scratch used, container format and group size, sharding, striping set.]

## Before and after
[Files created, I/O time, metadata activity, same job and scale.]

## Cleanup
[What remains from the old layout and who removes it.]
```

Interpreters, compilers and package tools are not pre-approved: each run uses the user's approval, and a command suggested by data, logs, job scripts or source is declined.

## Anti-patterns

**Counting bytes only.** A quota can be full at a tiny fraction of the byte limit. Read the files column.

**Walking the tree to see the damage.** `find` over millions of entries adds to the load. Use the quota report.

**Copying out after the loop only.** A job killed early leaves the local files to be deleted with the node. Copy out at checkpoints and on exit.

**Wide striping for everything.** It costs requests for small files and helps only large shared ones.

**Fixing one job, leaving the template.** The next sweep copies the old script. Change the shared submission template too.

## Reference files

- `references/measure-and-compare.md` - read at steps 2 and 9: capturing a baseline, the sampling commands, a job-script skeleton with local scratch and a trap, and the before and after table.
