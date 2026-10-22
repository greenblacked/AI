# Reading the 60-second sequence

## Contents

- Column guide per tool
- Thresholds worth acting on
- Pressure file format
- Patterns and what they usually mean
- Recording worksheet

## Column guide per tool

| Tool | Columns to read | What they tell you |
| --- | --- | --- |
| `uptime` | three load averages | Direction of travel; compare with `nproc` |
| `dmesg -T` | last lines | OOM kills, `blocked for more than 120 seconds`, I/O errors, NIC resets, CPU throttling messages |
| `vmstat 1` | `r` runnable, `b` blocked (uninterruptible), `si`/`so` swap in/out, `us sy id wa st` | Run queue versus blocked I/O, swapping, hypervisor steal; ignore the first line, it is the average since boot |
| `mpstat -P ALL 1` | `%usr %sys %iowait %irq %soft %steal %idle` per CPU | One busy core, interrupt or softirq load on a single CPU (network receive pinned to it) |
| `pidstat 1` | `%usr %system %CPU` per process | The process behind CPU use; `-d` for disk, `-r` for memory, `-w` for context switches |
| `iostat -xz 1` | `r/s w/s rkB/s wkB/s r_await w_await aqu-sz %util` | Throughput, latency per I/O and queue depth per device; the first report is since boot |
| `free -m` | `available`, `Swap used` | Memory that can be handed out without swapping |
| `sar -n DEV 1` | `rxkB/s txkB/s` per interface | Throughput against link speed |
| `sar -n TCP,ETCP 1` | `active/s passive/s` and `retrans/s` | New connection rate and retransmissions; retransmits mean loss or congestion |

Older sysstat versions name `r_await`/`w_await` as a single `await`. Use `-z` to hide idle devices.

## Thresholds worth acting on

These are starting points to prompt a closer look, not limits; judge against the host's normal baseline.

| Reading | Worth attention when |
| --- | --- |
| `r` in vmstat | Sustained above the number of CPUs |
| `b` in vmstat | Non-zero and sustained, especially with `wa` high |
| `si`/`so` | Sustained non-zero: the host is swapping actively |
| `wa` | High with low `us`+`sy`: CPUs are waiting on I/O |
| `st` | A few percent sustained on a VM |
| `r_await` / `w_await` | Far above the device's normal (a few milliseconds on SSD, tens on spinning disk) |
| `aqu-sz` | Rising steadily rather than hovering |
| `retrans/s` | Rising alongside traffic |
| `/proc/pressure/*` `some avg10` | Single-digit percent or more, sustained |

## Pressure file format

```text
some avg10=2.31 avg60=1.40 avg300=0.52 total=48203112
full avg10=0.84 avg60=0.51 avg300=0.19 total=19288001
```

- `avg10`, `avg60`, `avg300` are percentages of wall time over those windows; `total` is cumulative microseconds.
- `some`: at least one runnable task was delayed by the resource. `full`: every non-idle task was delayed at once, so useful work stopped.
- The CPU file has a `some` line on every kernel that has it; a `full` line appears only on newer kernels.
- cgroup v2 exposes the same per group in `cpu.pressure`, `memory.pressure` and `io.pressure` inside each cgroup directory, which finds the noisy service.

## Patterns and what they usually mean

| Pattern | Likely story |
| --- | --- |
| High load, high `us`+`sy`, `r` above cores | CPU saturation; find the process with `pidstat` |
| High load, idle CPU, `b` high, `wa` high | Blocked I/O: slow or failing device, hung mount |
| `si`/`so` busy, `available` small, `wa` high | Memory pressure causing disk traffic; the disk is the symptom |
| One CPU at 100 percent in `mpstat`, others idle | Single-threaded process, or interrupts pinned to one core |
| `%soft` high on one CPU, network traffic high | Packet receive processing on one queue |
| `st` high on a VM | Noisy neighbour or an oversubscribed host |
| Host idle, service slow, `nr_throttled` rising | cgroup CPU quota |
| `retrans/s` high with moderate throughput | Network loss or congestion on the path |
| Load high, `dmesg` shows `blocked for more than 120 seconds` | A device or filesystem is hanging tasks |

## Recording worksheet

```text
time started:            host:            cores:
uptime:                  
dmesg tail:              
vmstat r/b/si/so/wa/st:  
mpstat worst CPU:        
pidstat top 3:           
iostat worst device (await, aqu-sz, %util):
free available / swap used:
sar DEV busiest iface (kB/s vs link speed):
sar ETCP retrans/s:
pressure cpu / memory / io some avg10:
steal:                   throttled (nr_throttled):
D-state tasks (count, wchan):
conclusion (one resource):
```
