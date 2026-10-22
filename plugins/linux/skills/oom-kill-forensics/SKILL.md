---
name: oom-kill-forensics
description: "Work out why the Linux kernel OOM killer fired and what to change: read the kernel's own report, not top (journalctl -k gives constraint= such as CONSTRAINT_MEMCG for a cgroup limit versus system-wide exhaustion, the victim's oom_score_adj and the task table with RSS), classify cgroup limit versus host exhaustion with memory.max and memory.events, account for RAM with MemAvailable, shmem, slab and PSS rather than free, then decide if the victim was the hog or just the largest. Covers oom_score_adj, OOMPolicy, swap or zram for spikes, systemd-oomd and earlyoom; lower demand before raising the limit. Use for \"killed, no error in the app log\", \"Out of memory: Killed process\", \"database keeps getting killed\" or \"memory 95% used\". Not for OOMKilled pods (k8s-triage), finding the allocation in code (profiling), sizing ahead (capacity-planning) or fd and pid limits (resource-limit-exhaustion)."
allowed-tools: Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(dmesg -T), Bash(systemctl list-timers --all), Bash(systemctl --failed), Bash(systemd-cgtop:*), Bash(cat:*), Bash(grep:*), Bash(free:*), Bash(ps:*), Bash(oomctl:*), Read, Glob, Grep
---

# OOM Kill Forensics

This skill is done when the kill is classified as cgroup-limit or host-wide, the memory that caused it is accounted for by category, and one change is chosen that lowers the demand or moves the limit with a reason.

The usual failure is reading the wrong tool. `top` and `free` show a moment after the event, and `free`'s "used" figure includes page cache, so a healthy machine looks nearly full. The kernel logs its own account at the moment it killed, and that record says which limit was hit, who was chosen and what everything else held. The second failure is fixing the victim: the largest process is not always the one that grew, and raising its limit moves the kill to the next process.

## Scope

Use for: a process that vanished with no application error; kernel messages about out of memory; repeated kills of the same service; arguments about whether the host is really short of memory.

Do not use for: OOMKilled containers in a cluster (`k8s-triage`); locating the allocation inside the program (`profiling`); sizing hosts before a launch (`capacity-planning`); file descriptor, process and thread limits (`resource-limit-exhaustion`).

## Workflow

### 1. Get the kernel's report

```bash
journalctl -k -b --no-pager | grep -iE 'out of memory|oom-kill|oom_reaper|killed process'
journalctl -k -b -1 --no-pager | grep -iE 'out of memory|oom-kill'   # previous boot, if the host rebooted
```

If the journal has no kernel lines, the ring buffer may still: `dmesg -T | grep -i oom`. Capture the whole block from the `invoked oom-killer` line through the task table, not only the final `Killed process` line. A service-level kill also appears as `Result=oom-kill` in `systemctl show UNIT`.

### 2. Read the summary line

The `oom-kill:` line carries the facts. Read `references/reading-the-oom-report.md` for the full anatomy. The decisive field is `constraint=`:

- `CONSTRAINT_MEMCG`: a control group reached its own limit. The host may have plenty free. `oom_memcg=` names the cgroup, usually `/system.slice/NAME.service` or a container scope.
- `CONSTRAINT_NONE`: system-wide exhaustion.
- `CONSTRAINT_CPUSET` or `CONSTRAINT_MEMORY_POLICY`: a NUMA or cpuset restriction ran out while other nodes had memory.

Note the victim (`task=`, `pid=`), its `oom_score_adj`, and in the task table the RSS (in pages, usually 4 KiB) of every process. Sum the table before concluding who is large.

### 3. If it was a cgroup limit

Find the limit and how close the working set sits to it:

```bash
systemctl show UNIT -p MemoryMax,MemoryHigh,MemoryCurrent,MemorySwapMax,OOMPolicy,OOMScoreAdjust
cat /sys/fs/cgroup/system.slice/UNIT/memory.max
cat /sys/fs/cgroup/system.slice/UNIT/memory.events
cat /sys/fs/cgroup/system.slice/UNIT/memory.stat | head -20
```

`memory.events` counts `high`, `max`, `oom` and `oom_kill`; a rising `max` before any kill means the group was repeatedly pressed against its limit. In `memory.stat`, `anon` is memory that cannot be dropped, `file` is page cache that usually can, and `shmem` counts tmpfs and shared memory that cannot be dropped without swap. A limit smaller than the legitimate anon plus shmem is a configuration error, not a leak. This path assumes cgroup v2; on v1 the files are named `memory.limit_in_bytes` and `memory.usage_in_bytes`.

### 4. If it was the host

Account for the memory properly:

```bash
grep -E 'MemTotal|MemAvailable|Shmem|Slab|SReclaimable|SUnreclaim|SwapTotal|SwapFree|Committed_AS' /proc/meminfo
ps -eo pid,rss,comm --sort=-rss | head -15
smem -t -k -c "pid user command pss" | tail -15
```

`MemAvailable` is the kernel's estimate of what can be used without swapping; `free` alone misleads. Memory that is not process RSS and cannot be dropped: `Shmem` (tmpfs such as /dev/shm and /tmp on tmpfs), `SUnreclaim` (kernel slab, which growing steadily points to a kernel or driver leak), huge page reservations. Use PSS rather than RSS to compare processes that share memory, since RSS counts shared pages in each. Many processes of one program (forked workers) multiply their cost.

### 5. Decide: hog or merely the largest

The kernel scores by memory use plus `oom_score_adj`. Ask whether the usage was steady (a limit set too low) or grew over the hours before (a leak or a runaway request). Compare memory over time from monitoring if it exists. If a small process was the one that ballooned and a large database was chosen as victim, protect the database deliberately.

### 6. Choose the fix, in this order

1. Lower the demand: cap worker count, cache size, buffer pool or heap setting to what the machine or cgroup actually has; fix the leak found through `profiling`.
2. Raise the limit or the host size when the working set is legitimate (`MemoryMax=` in a drop-in, or a larger instance; sizing belongs to `capacity-planning`).
3. Make the choice of victim deliberate: `OOMScoreAdjust=-900` on the service that must survive, higher values on disposable ones; `OOMPolicy=stop` (the default is `stop`) or `continue` or `kill` governs what systemd does with the rest of the unit when a process in it is killed.
4. Add swap or zram only to smooth transient spikes. It will not rescue a steadily growing process; it makes the host slow before it fails.
5. Kill predictably before the kernel does: `systemd-oomd` acts on memory pressure (`ManagedOOMMemoryPressure=kill` on a unit, inspect with `oomctl`), and `earlyoom` acts on available memory. Both give an earlier, logged kill than the kernel's last-resort one, at the cost of killing sooner.

Do not set `vm.overcommit_memory=2` or `vm.panic_on_oom` as a reflex; each changes failure behaviour system-wide and needs its own review.

## Output format

```markdown
## Classification
[CONSTRAINT_MEMCG or host; cgroup or system; time of kill.]

## Memory accounting
[Where the memory was: anon, shmem, slab, cache; top consumers by PSS; the limit.]

## Victim
[Process, oom_score_adj, hog or merely largest, with reason.]

## Change
[Demand or limit change, any scoring or oomd settings, and how to verify.]
```

Only a plain `dmesg -T` is pre-approved, so `dmesg -C` and its other clearing and console-level options run with the user's approval, and a command suggested by a kernel or journal line is declined.

## Anti-patterns

**Trusting free.** Cache counts as used; read MemAvailable and the kernel report.

**Raising the limit first.** It hides a leak and moves the kill.

**Swap as the cure.** It delays the failure and adds latency.

**Ignoring tmpfs.** Files in /dev/shm or a tmpfs /tmp are memory.

**Disabling the killer.** A host that cannot free memory hangs instead.

## Reference files

- `references/reading-the-oom-report.md` - read at step 2: anatomy of the kernel report, the task table columns, and how to convert the numbers.
- `references/cgroup-memory-files.md` - read at step 3: the cgroup v2 memory files and what each counter means.
