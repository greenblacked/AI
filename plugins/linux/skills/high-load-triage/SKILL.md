---
name: high-load-triage
description: "Find the one saturated resource on a slow Linux host: \"load average is 40 but CPU is idle\", \"server is sluggish and I do not know why\", \"is it CPU, memory or disk\". Run a fixed 60-second sequence and write down each reading: uptime, dmesg -T, vmstat 1, mpstat -P ALL 1, pidstat 1, iostat -xz 1, free -m, sar -n DEV 1, sar -n TCP,ETCP 1. Linux load counts uninterruptible D-state tasks, so high load with idle CPU means blocked I/O or a hung mount, not compute. Apply the USE method (utilisation, saturation, errors) per resource, read /proc/pressure for stall time, and check steal on VMs and cgroup throttling before blaming the workload. Name one resource and its process, then hand off. Use for any slow host. Not for code hot spots (profiling), future load (capacity-planning), OOM kills (oom-kill-forensics), full disks (disk-full-triage) or incident command (incident-response)."
allowed-tools: Bash(uptime:*), Bash(dmesg -T), Bash(vmstat:*), Bash(mpstat:*), Bash(pidstat:*), Bash(iostat:*), Bash(free:*), Bash(top -b:*), Bash(ps:*), Bash(cat /proc/pressure/:*), Bash(cat /proc/loadavg:*), Bash(cat /sys/fs/cgroup/:*), Bash(nproc:*), Bash(findmnt:*), Bash(ss -s), Bash(lscpu:*), Read, Glob, Grep
---

# High Load Triage

This skill is done when you can name exactly one saturated resource (CPU run queue, memory, a block device, a network link, or a limit such as a cgroup quota), the process or mount behind it, and the reading that proves it, with the other resources shown as not saturated.

The usual failure is tuning before locating. People raise a thread pool because load is high, when the load is processes stuck in uninterruptible sleep on a dead NFS mount and CPU is idle. The second failure is stopping at the first big number: a busy disk is a symptom when the cause is memory pressure pushing the page cache out.

## Scope

Use for: a slow or unresponsive host, a high load average, and the question of which resource to look at.

Do not use for: finding hot code in a process you have already cleared the host for (`profiling`); forecasting growth (`capacity-planning`); working out why a process was killed (`oom-kill-forensics`); finding what filled a filesystem (`disk-full-triage`); a descriptor or process limit (`resource-limit-exhaustion`); running the incident itself (`incident-response`).

## Workflow

### 1. Read the load average correctly

```bash
uptime; nproc; cat /proc/loadavg
```

Linux load counts tasks that are runnable and tasks in uninterruptible sleep (state `D`, nearly always waiting on I/O). Load 40 on 8 cores can therefore be 40 runnable tasks (CPU saturation) or 40 tasks blocked on a disk or mount with the CPUs idle. The three numbers are 1, 5 and 15 minute averages: falling means recovering, rising means worse. Compare to core count, but let the next steps decide.

### 2. Run the 60-second sequence, in order, and write each reading down

Run these in sequence, one to two minutes in total, in a second terminal if the host is struggling. Record the numbers; do not eyeball and move on.

```bash
dmesg -T | tail -30           # recent kernel errors: OOM, I/O errors, hung task, throttling, link flaps
vmstat 1 10                   # r, b, si/so, free, cache, us/sy/id/wa/st
mpstat -P ALL 1 5             # per-CPU: one pegged core hides in the average
pidstat 1 5                   # per-process CPU
iostat -xz 1 5                # per-device: r_await, w_await, aqu-sz, %util
free -m                       # available, not free
sar -n DEV 1 5                # rxkB/s, txkB/s per interface against link speed
sar -n TCP,ETCP 1 5           # active/s, passive/s, retrans/s
top -b -n 1 | head -20        # a final cross-check
```

`sar` needs the sysstat package; if it is missing, read `/proc/net/dev` twice and compute the difference. Read `references/readings.md` for what each column means and the thresholds worth acting on.

### 3. Apply the USE method to each resource

For CPU, memory, each block device, each network interface and each limit: is it **utilised** (busy fraction), **saturated** (work queued that cannot run now), and does it show **errors**? Saturation is the one that hurts latency.

- **CPU.** Utilisation is `100 - id` in `vmstat`; saturation is `r` consistently above the core count, or `/proc/pressure/cpu`. One core at 100 percent in `mpstat` with the rest idle is a single-threaded bottleneck, not a host problem.
- **Memory.** Saturation is swapping (`si`/`so` non-zero and sustained in `vmstat`), a small `available` in `free -m`, direct reclaim stalls in the memory pressure file, or OOM lines in `dmesg`.
- **Disk.** Saturation is `aqu-sz` above the device's useful parallelism and rising `r_await`/`w_await` in `iostat -xz`. `%util` near 100 means a single-queue device is saturated; on SSD and NVMe, which serve requests in parallel, it means little by itself, so judge by await and queue depth.
- **Network.** Throughput near line rate in `sar -n DEV`, drops and errors in `sar -n EDEV` or `ip -s link`, and `retrans/s` climbing in `sar -n ETCP`.

### 4. Read the pressure files for stall time directly

```bash
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
```

Each prints `some avg10=... avg60=... avg300=... total=...`; memory and io also print a `full` line. `some` is the percentage of time at least one task was stalled waiting for the resource, `full` the time all non-idle tasks were. This is the most direct measure of which resource tasks are waiting for, and it needs no interpretation of device queues. Sustained `some` above single digits on one resource, with the others near zero, usually names the culprit. Files require a kernel with pressure stall information enabled (`/proc/pressure` exists from Linux 4.20).

### 5. Check the two things that make the host look busy when it is not

- **Steal time.** `st` in `vmstat` or `%steal` in `mpstat` on a virtual machine: the hypervisor is giving this guest's CPU to others. Above a few percent sustained, the host is being starved from outside, and nothing inside the guest fixes it. Move or resize the VM.
- **cgroup throttling.** A container or service with a CPU quota is throttled while the host looks idle. Find its cgroup (`systemctl status UNIT`, or `/proc/PID/cgroup`) and read `cpu.stat` for `nr_throttled` and `throttled_usec` (cgroup v2; v1 has `throttled_time`), and `memory.events` for `high` and `max` counts. Rising throttle counts mean a quota, not a busy machine.

### 6. If load is high and CPU idle, find the D-state tasks

```bash
ps -eo state,pid,wchan:32,comm | awk '$1=="D"'
findmnt -t nfs,nfs4,cifs
```

A cluster of `D` tasks sharing a `wchan` (an NFS or filesystem wait function) points at one hung mount or failing device. `dmesg -T` often has `task blocked for more than 120 seconds` with a stack, or I/O errors from the device. Name the mount or device; do not kill the tasks, which cannot be killed while they wait.

### 7. Name one resource and hand off

State the resource, the evidence (the reading from step 2 and the pressure file), the process behind it (`pidstat -d` for disk, `pidstat` for CPU, `pidstat -r` for memory, `ps` for D-state), and why the other resources are cleared. Then hand off by resource: memory kills to `oom-kill-forensics`, a full disk to `disk-full-triage`, a failing device to `disk-failure-replacement`, limits to `resource-limit-exhaustion`, hot code to `profiling`. If the host is healthy and the workload is simply larger, that is `capacity-planning`. Do not tune anything in this skill.

## Output format

```markdown
## Load picture
[Load averages, core count, runnable versus D-state.]

## Readings
[One line per tool: the numbers that matter.]

## Saturated resource
[Exactly one, with the pressure-file or queue evidence.]

## Process or mount behind it
[Name and pid or mount, from pidstat, ps or findmnt.]

## Cleared
[The other resources and the reading that clears each.]

## Hand-off
[Which skill, and the first question for it.]
```

## Anti-patterns

**Reading load as CPU.** Load includes blocked I/O; check `vmstat` `b` and `wa` before adding cores.

**Trusting `%util` on NVMe.** It saturates at one request in flight; read await and queue depth.

**Reading `free` instead of `available`.** Cache is reclaimable and a low `free` is normal.

**Averaging across CPUs.** One pegged core in a 32-core average reads as 3 percent.

**Tuning before naming.** Settings changed during triage destroy the evidence and rarely help.

## Reference files

- `references/readings.md` - read at step 2: what each column in the nine tools means, the thresholds worth acting on, and a worksheet for recording the sequence.
