# Queue diagnosis

Contents: pending reasons, priority factors, request shapes, pilot record template.

## Pending reasons

Shown in the `REASON` column of `squeue`. Names vary slightly by Slurm version and site policy; `scontrol show job JOBID` gives the full text.

| Reason | Meaning | What to change |
| --- | --- | --- |
| Priority | Higher-priority jobs are ahead | Look at `sprio`; shorter or smaller requests backfill sooner |
| Resources | Next in line, no free resources that fit | Reduce the memory, cores or time; consider a larger partition |
| Dependency | Waiting on another job | Check the dependency chain |
| AssocGrpCPUMinutesLimit, AssocGrpBillingMinutes or similar | Account allocation limit reached | Ask the project owner or site |
| QOSMaxJobsPerUserLimit or similar | A per-user job cap | Use an array or wait |
| ReqNodeNotAvail | Requested nodes down or reserved | Drop pinned node requests; check `sinfo -R` |

## Priority factors

`sprio -l -u $USER` splits the priority into age, fair-share, job size, partition and QOS components. Fair-share falls with recent usage relative to your share (`sshare -U` shows it), so a stretch of large requests that went mostly unused lowers the factor for later jobs. Age grows with waiting time. Job size can favour large or small jobs depending on the site's configuration.

## Request shapes

| Shape | Effect on wait | Use when |
| --- | --- | --- |
| Short walltime, few cores | Backfills quickly | Tasks that are independent and checkpointable |
| One large long job | Waits for a big gap | Truly tightly coupled work |
| Job array of small tasks | Many small starts; individual tasks backfill | Parameter sweeps, per-file work |
| Different partition | Shorter queue possible | A less contended partition satisfies the hardware needs |

Do not request GPUs, high-memory nodes or exclusive nodes unless the pilot shows a need; each narrows the set of places the job can start.

## Pilot record template

```markdown
| Run | Input size | Cores | Elapsed | TotalCPU | CPU eff. | MaxRSS (step) | Node type |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

Keep one row per pilot, and add the production run as the last row after it finishes.
