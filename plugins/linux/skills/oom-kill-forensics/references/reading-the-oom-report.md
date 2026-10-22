# Reading the kernel OOM report

## Contents

- Shape of the report
- The summary line
- The task table
- Converting units

## Shape of the report

The block starts with `PROCESS invoked oom-killer: gfp_mask=..., order=N, oom_score_adj=N`. The process named there is the one whose allocation failed, not necessarily the victim. Next come a call trace, a memory summary (free, active and inactive lists, slab, shmem, swap), then the task table, then the `oom-kill:` summary line and `Out of memory: Killed process PID (NAME)` or `Memory cgroup out of memory: Killed process PID (NAME)` with the victim's `total-vm`, `anon-rss`, `file-rss` and `shmem-rss`.

## The summary line

Example shape:

```text
oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=/,mems_allowed=0,oom_memcg=/system.slice/app.service,task_memcg=/system.slice/app.service,task=worker,pid=1234,uid=1001
```

| Field | Meaning |
| --- | --- |
| constraint | What limit applied: NONE (whole system), CPUSET, MEMORY_POLICY, MEMCG |
| oom_memcg | The cgroup whose limit was hit (MEMCG only) |
| task_memcg | The cgroup the victim belonged to |
| task, pid, uid | The victim |

`oom_memcg` differing from `task_memcg` means a parent group's limit was hit and a process in a child was chosen.

## The task table

Columns: `pid uid tgid total_vm rss pgtables_bytes swapents oom_score_adj name`. Values for `total_vm` and `rss` are in pages. `rss` counts shared pages in every process that maps them, so summing it over-counts for forked workers; use it for ranking, and PSS from a live system for fairness. `swapents` is pages swapped out. `oom_score_adj` is -1000 to 1000: -1000 exempts the process, positive values make it likelier.

In a cgroup kill, the table lists only tasks in the limited group; in a system kill it lists every task, and the sum of the `rss` column approximates what was resident.

## Converting units

Pages are 4 KiB on most x86 and many arm64 systems; confirm with `getconf PAGESIZE`. So `rss=262144` pages is 1 GiB. When the memory summary lists `shmem:` and `unevictable:` figures, those are memory that cannot be dropped the way page cache can (shmem can only leave RAM by being swapped out).
