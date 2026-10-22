---
name: kernel-crash-forensics
description: "Make an unexplained reboot, kernel panic, soft lockup or hung task diagnosable. Use for \"server rebooted by itself\", \"BUG: soft lockup\", \"hung_task blocked for more than 120 seconds\" or \"how do I get a vmcore\". Separate crash from power loss, watchdog reset or admin action using last-boot evidence (journalctl -b -1 -k, last -x, pstore, BMC event log) before theorising. Then make the next crash capturable: persistent journal, kdump with a tested crashkernel reservation, panic and softlockup_panic set deliberately, netconsole. Read an oops from the first warning, with taint flags and module list, and check EDAC memory errors and disk or NVMe resets before blaming software. Classify hardware, driver or known kernel bug against the vendor tracker. Not for a host that fails to boot (boot-failure-recovery), the OOM killer (oom-kill-forensics) or application crashes (debugging)."
allowed-tools: Bash(journalctl --list-boots), Bash(last -x:*), Bash(ras-mc-ctl --summary), Bash(ras-mc-ctl --errors), Bash(kdumpctl status:*), Bash(kdump-config show:*), Bash(uname:*), Read, Glob, Grep
---

# Kernel Crash Forensics

This skill is done when the event is classified as a kernel crash, a watchdog reset, a power loss or a deliberate action, with the evidence line that shows it, and, if it was a crash or can recur, the host is configured so the next occurrence leaves a journal, a console log or a vmcore.

The usual failure is theorising first. "It must be a memory leak" or "it must be the new driver" is stated before anyone has established that the host crashed at all; many unexplained reboots are power events, a hardware watchdog, a hypervisor action or a person. The second failure is capturing nothing: a volatile journal and no kdump mean the evidence of the first crash is gone, and the investigation waits for a second.

## Scope

Use for: a host that restarted with no known reason; panics, oopses, soft or hard lockups, hung-task warnings; setting a host up to capture the next crash; reading a vmcore or an oops.

Do not use for: a host that fails to boot (`boot-failure-recovery`); the OOM killer (`oom-kill-forensics`); a crashing application process (`debugging`).

## Workflow

### 1. Establish what happened, from last-boot evidence

```bash
journalctl --list-boots                      # how many boots survive; a single entry means the journal is volatile
journalctl -b -1 -k -e --no-pager            # kernel log of the previous boot, end first
journalctl -b -1 --no-pager | tail -100      # what everything was doing at the end
last -x reboot shutdown | head               # a reboot with no shutdown record before it means no clean shutdown
ls /sys/fs/pstore /var/lib/systemd/pstore    # crash records kept across the reboot, if the platform has pstore
ipmitool sel elist                           # BMC system event log: power loss, watchdog reset, thermal, ECC
```

Decide with these cues:

- The previous boot's log ends abruptly with no shutdown messages and no panic text: power loss, a hardware watchdog reset, a hypervisor action or a hard lockup that could not log. The BMC event log and the hypervisor's own log settle which.
- The log ends with `Kernel panic`, `BUG:` or `Oops:`: a kernel crash. Keep the whole block.
- Shutdown messages appear before the end: someone or something asked for it. Check `last -x`, the journal for `systemd-logind` and the unit that requested it, and the change record.

If the journal holds only one boot, say so: the storage is volatile, and step 3 comes before any conclusion.

### 2. Read the evidence, from the top

An oops is a cascade. Read from the first warning, not the final trace, because the last lines show the system falling over after the original fault. In order:

1. The first `WARNING`, `BUG` or `Oops` line and the function it names.
2. The `Tainted:` flags. `P` or `O` mean a proprietary or out-of-tree module is loaded, which changes who can accept the report; `W` means an earlier warning already happened; `D` means the kernel died with an oops; `M` means a machine check. `cat /proc/sys/kernel/tainted` shows the live mask. Read `references/taint-and-messages.md` for the full table.
3. The `Modules linked in:` list, for third-party or recently changed modules.
4. The kernel build, from the `Hardware name` and version line, since a known bug is tied to an exact version.
5. For `BUG: soft lockup - CPU#N stuck for Ns!` a CPU ran in kernel code without scheduling; for `INFO: task X blocked for more than 120 seconds` a task was in uninterruptible sleep, usually on storage or a lock; the stack shows what it waited for.

### 3. Check the hardware before the software

Memory, disk and bus faults produce panics that look like software bugs.

```bash
ras-mc-ctl --summary                         # corrected and uncorrected memory errors by controller (rasdaemon)
ras-mc-ctl --errors                          # individual error records
journalctl -k -b -1 | grep -iE 'mce|machine check|edac|nvme.*reset|blk_update_request|I/O error|ata[0-9]+.*(error|reset)'
```

Corrected memory errors that repeat on one DIMM, any uncorrected error, repeated NVMe or SATA link resets, and thermal throttling events in the BMC log all point at hardware. Replace or reseat the part before chasing a kernel bug, and keep the host out of the critical path meanwhile.

### 4. Make the next crash capturable

Do this whenever the cause is not yet known, even when the crash looks like hardware. Propose the change; applying it is the owner's call.

- **Persistent journal.** Create `/var/log/journal` or set `Storage=persistent` in `journald.conf`, then restart `systemd-journald`. Without it, boots earlier than the last are lost.
- **kdump.** Install the distribution's kdump package, reserve memory with `crashkernel=` on the kernel command line (the size depends on memory and distribution defaults; use the distribution's documented value, then test), enable the service, and confirm with `kdumpctl status` or `kdump-config show` and `cat /sys/kernel/kexec_crash_loaded` (1 when loaded). Test it once, on a drained host in a window, by deliberately crashing it with `echo c > /proc/sysrq-trigger`; an untested kdump is a guess. The dump lands in `/var/crash` by default.
- **Panic behaviour, set deliberately.** `kernel.panic=N` reboots N seconds after a panic (0 waits forever). `kernel.softlockup_panic=1`, `kernel.hung_task_panic=1` and `kernel.panic_on_oops=1` turn those conditions into panics so kdump fires; set them only where a restart is better than a stuck host, and understand that a hung-task panic can fire on a slow disk that would have recovered.
- **Remote logging.** `netconsole` sends kernel messages over UDP to a collector; a serial console or the BMC's serial-over-LAN does the same for early and late messages. The last lines before a hard hang rarely reach local disk.

### 5. Analyse a vmcore, if there is one

Open it with the `crash` utility and the matching `vmlinux` (from the debug-symbol package for that exact kernel build). `makedumpfile --dump-dmesg VMCORE OUTFILE` extracts the kernel log without the symbols. Inside `crash`, `log` prints the log, `bt` the backtrace of the panicking task and `ps` the task states. The symbols must match the running build or the output is wrong.

### 6. Classify, and verify against the vendor

Place the event in one class and state the evidence: **hardware** (BMC or EDAC records, repeated device resets), **driver or module** (the faulting function is in a third-party or recently updated module, taint flags show it), or **known kernel bug** (the first warning matches a bug report for this kernel build). For the third, search the distribution's bug tracker and the kernel changelog with the exact build string, not just the symptom. If nothing matches, the next step is the capture in step 4, not a guess.

## Output format

```markdown
## What happened
[Crash, watchdog, power, or deliberate; the evidence line.]

## Fault
[First warning, function, taint flags, modules, kernel build.]

## Hardware checks
[EDAC, disk and NVMe resets, BMC events.]

## Classification
[Hardware, driver or kernel bug; the bug reference or why none.]

## Capture configuration
[Persistent journal, kdump tested or not, panic settings, remote logging.]
```

## Anti-patterns

**Starting from the last trace.** The final lines are the collapse, not the cause.

**Blaming software before hardware.** Uncorrected memory errors produce arbitrary panics.

**An untested kdump.** A reserved size that is too small produces no dump on the day it matters.

**Panic settings applied fleet-wide as a reflex.** A hung-task panic can turn a slow disk into a reboot.

**Searching the symptom, not the build.** Kernel bugs are fixed per version.

## Reference files

- `references/taint-and-messages.md` - read at step 2: taint flag letters, what the lockup and hung-task messages mean, and the sysctls that govern them.
