# State table

Contents: states, exit codes, useful commands.

## States

| State | Who ended it | First check | Usual action |
| --- | --- | --- | --- |
| COMPLETED with nonzero DerivedExitCode | A step failed, the batch script carried on | `sacct` step rows | Treat as FAILED for the step that failed |
| FAILED | The program exited non-zero | Earliest error in stderr | Debug the program; `debugging` |
| OUT_OF_MEMORY | The cgroup memory limit, enforced by the kernel | Step `MaxRSS` against `ReqMem` | Resize; find why memory grew |
| TIMEOUT | The scheduler, at the time limit | `Elapsed` against `Timelimit`, progress output | Longer limit or checkpoint |
| NODE_FAIL | The node stopped responding | `sinfo -R`, `NodeList` | Resubmit, exclude the node |
| BOOT_FAIL | The node failed to boot for the job | Same | Resubmit; tell the site |
| PREEMPTED | A higher-priority job took the nodes | Partition and QOS policy | Resubmit; `--requeue` if safe |
| CANCELLED | A user or an administrator | The UID in `CANCELLED by` | Ask who; check dependency scripts |
| DEADLINE | The job could not finish before its deadline | `--deadline` in the script | Remove or move the deadline |
| REQUEUED, RESIZING | The scheduler moved it | `scontrol show job` | Wait, or check requeue count |

## Exit codes

- `ExitCode` is `exit:signal`. `0:9` is killed by signal 9; `0:15` by SIGTERM, which is what a time limit or `scancel` sends first.
- A shell reports 128 plus the signal: 137 is 9 (SIGKILL), 143 is 15 (SIGTERM), 139 is 11 (segmentation fault).
- SIGKILL with State TIMEOUT is the scheduler; SIGKILL with OUT_OF_MEMORY is the kernel; SIGKILL with FAILED and no memory pressure is worth a look at the log for an external `kill`.
- The kernel's out-of-memory kill often appears in the job's stderr as a `slurmstepd` line mentioning an oom-kill event; the matching host-level record is `oom-kill-forensics` territory if you have the node's logs.

## Useful commands

```bash
sacct -j JOBID --format=JobID,State,ExitCode,Elapsed,Timelimit,ReqMem,MaxRSS,MaxRSSNode -P
sacct -u $USER -S now-3days -s F,TO,OOM,NF -X --format=JobID,JobName%20,State,Elapsed,NodeList
sstat -j JOBID.batch --format=JobID,MaxRSS,AveCPU    # while it is still running
sinfo -R                                              # nodes down or drained, with reasons
scontrol show node NODENAME                           # one node's state and Reason
```

`-P` prints pipe-separated output that survives pasting; `-s` filters by state; `now-3days` is a valid relative start time.
