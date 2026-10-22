# Taint flags, messages and sysctls

## Taint flags

`cat /proc/sys/kernel/tainted` prints a bitmask; an oops prints the letters after
`Tainted:`. A space or `G` (for "good") means no flag is set. The ones that matter most:

| Letter | Meaning | Why it matters |
| --- | --- | --- |
| `P` | A proprietary module was loaded | Upstream and many vendors will not accept the report |
| `F` | A module was force-loaded | The version check was bypassed |
| `S` | Running on an unsupported configuration (SMP with unsupported CPUs) | Behaviour not guaranteed |
| `R` | A module was force-unloaded | The state may be inconsistent |
| `M` | A machine check exception occurred | Hardware fault; start with the hardware |
| `B` | A bad page was seen | Memory fault |
| `D` | The kernel has died recently (an oops or BUG) | Later errors may be fallout |
| `W` | A warning was issued | An earlier fault already happened; find it |
| `O` | An out-of-tree module was loaded | Report to the module's maintainer first |
| `E` | An unsigned module was loaded | Secure Boot and support implications |
| `L` | A soft lockup occurred | Lockup preceded this message |

Take the exact list from the kernel documentation for the running version; letters are
added over time.

## Messages

- `BUG: soft lockup - CPU#N stuck for Ns!`: a CPU ran kernel code for several seconds
  without yielding. The reported task and stack show where. Common causes are a driver
  looping, a lock held too long, an interrupt storm, or a hypervisor that did not schedule
  the virtual CPU (check steal time).
- `INFO: task NAME:PID blocked for more than 120 seconds.`: a task has been in
  uninterruptible sleep (state D) beyond `kernel.hung_task_timeout_secs`. Look at the stack
  for the wait: storage I/O, a mutex, a network filesystem. Several tasks blocked on the
  same call point at the shared resource.
- `NMI watchdog: Watchdog detected hard LOCKUP on cpu N`: the CPU stopped taking
  interrupts. Often hardware or firmware, sometimes a driver disabling interrupts.
- `Kernel panic - not syncing: ...`: the text after the colon names the reason (for example
  an attempt to kill init, fatal exception, hung task, or an explicit panic_on_oops).
- `Machine check` or `mce:` lines, `EDAC` lines: hardware reported an error. Corrected
  errors are counted; uncorrected ones usually bring the host down.

## Sysctls

| Setting | Effect |
| --- | --- |
| `kernel.panic` | Seconds to wait after a panic before rebooting; 0 means never |
| `kernel.panic_on_oops` | Turn an oops into a panic |
| `kernel.softlockup_panic` | Panic on a soft lockup |
| `kernel.hardlockup_panic` | Panic on a hard lockup |
| `kernel.hung_task_panic` | Panic when a hung task is detected |
| `kernel.hung_task_timeout_secs` | Seconds before a blocked task is reported (default 120) |
| `kernel.hung_task_warnings` | How many warnings to print before going quiet |
| `kernel.sysrq` | Which magic SysRq functions are enabled; `c` triggers a crash |

Persist settings in a file under `/etc/sysctl.d/`, and record why each is set, since the
reason is the first thing forgotten.

## kdump sizing and checks

- The `crashkernel=` reservation must be large enough for the capture kernel, its initramfs
  and the dump tooling. Follow the distribution's documented sizes, then test.
- The dump target (local path, NFS or SSH) must have enough free space for the dump
  filtered by `makedumpfile`; check it before the day it is needed.
- Confirm loading with `cat /sys/kernel/kexec_crash_loaded` and service state with
  `kdumpctl status` on Red Hat-family systems or `kdump-config show` on Debian-family.
