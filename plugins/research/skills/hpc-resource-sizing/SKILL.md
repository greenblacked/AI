---
name: hpc-resource-sizing
description: "Choose cores, memory, GPUs and walltime for a cluster job to cut queue wait and waste. Runs a short representative pilot (one task, a fraction of the data) and reads seff and sacct for peak MaxRSS, CPU efficiency and elapsed time, then requests a stated margin over measured peak memory and projected walltime, since the scheduler backfills smaller, shorter jobs first. Requests cores only where the scaling curve still pays, checks squeue --start, sprio and sshare to tell a priority problem from a request-shape problem, considers another partition or a job array, and re-measures after the first production run. Use for \"my jobs sit in the queue for days\", \"how much memory should I request\", \"what walltime\", \"my CPU efficiency is 12 percent\". Not for server capacity (capacity-planning), spend (cost-review) or a job that already died (slurm-job-failure-triage)."
allowed-tools: Bash(sacct:*), Bash(seff:*), Bash(squeue:*), Bash(sprio:*), Bash(sshare:*), Bash(sinfo:*), Bash(sbatch --test-only:*), Bash(sstat:*), Read, Glob, Grep
---

# HPC Resource Sizing

This skill is done when the request for a job (cores, memory, GPUs, walltime, partition, array shape) rests on measurements from a pilot run, each number has a stated margin, and the request will be revisited after the first production run.

The usual failure is a defensive request: the maximum memory "to be safe", the longest walltime allowed, and every core on the node. The job then waits longer, because the scheduler fills gaps with smaller and shorter jobs, it consumes fair-share on resources it never used, and its efficiency is poor. The opposite failure, a guess too low, is killed late and wastes the run.

## Scope

Use for: sizing the next submission of a batch job, array or GPU job; long queue waits; low CPU or memory efficiency.

Do not use for: planning capacity of services or servers (`capacity-planning`); reducing a cloud bill (`cost-review`); working out why a job already died (`slurm-job-failure-triage`).

## Workflow

### 1. Run a pilot

Run one representative task: the real code on a fraction of the data, or one array element, or a few iterations, on the same type of node and with a generous request so it is not killed. Choose a pilot big enough to hit the real memory behaviour (loading the full index, say), because memory often scales with input size while time scales with something else. Run at least two input sizes if the scaling is unknown, so a line can be drawn.

### 2. Read the accounting

```bash
seff JOBID
sacct -j JOBID --format=JobID,State,Elapsed,TotalCPU,AllocCPUS,ReqMem,MaxRSS,AveRSS,AllocTRES%40
```

CPU efficiency is `TotalCPU / (Elapsed x AllocCPUS)`; `seff` prints it. Peak memory is `MaxRSS`, to be read from the step rows (`JOBID.0`, not only `JOBID.batch`), because the work usually runs in a step. `MaxRSS` is sampled at an interval, so a short spike can be missed; pad accordingly and note the sampling. Establish whether `ReqMem` was per node or per CPU (`--mem` versus `--mem-per-cpu`; older Slurm versions mark it with `n` or `c`). For GPU jobs the accounting shows allocation, not use: watch utilisation from inside the job (`nvidia-smi`) or the site's job statistics, and size the GPU count and memory from that.

### 3. Project to the production job

Scale memory by the input size using the pilot points (fit a line through two sizes; do not assume proportional). Scale time by the work done per unit and the number of units. Then add the margin, stated as a number: a common starting point is 15 to 25 percent over measured peak memory and over projected walltime, widened when the pilot was small or timing varies (shared filesystem, mixed node types). The margin is site- and workload-specific; write down what you chose and why. A job that runs twice as long as projected on a busy filesystem is a reason for a wider margin on the time, not for the maximum.

### 4. Choose the cores by the scaling curve

Run the pilot at two or three core counts and record elapsed time. Request cores up to where adding more still gives a worthwhile speedup, and no further; CPU efficiency below roughly 70 percent at the chosen size usually means too many cores, or a serial part dominating. Check that the code uses the cores requested: set `OMP_NUM_THREADS` (or the equivalent) to match `--cpus-per-task`. A strong-scaling measurement belongs to a scaling study; use its result here. Request memory per node or per CPU consistently with the site's convention (`--mem` or `--mem-per-cpu`).

### 5. Read the queue evidence

Before blaming the request, look at the queue:

```bash
squeue -u $USER --start        # estimated start times and the pending reason
sprio -u $USER                 # priority factors: age, fair-share, job size, partition
sshare -U                      # your fair-share usage and factor
sbatch --test-only job.sh      # where it would be scheduled, without submitting
```

The pending `Reason` tells the class of problem: `Priority` means others rank higher (a fair-share or age matter), `Resources` means it is next in line but nothing fits, `QOSMaxJobsPerUserLimit` or similar means a policy limit. A low fair-share factor with a modest request is a usage problem, not a shape problem. See `references/queue-diagnosis.md`.

### 6. Reshape the request

Options in the order of effect: shorter walltime (it fits more backfill gaps), less memory per core, fewer cores, a different partition that is less loaded (check `sinfo`), a job array of small independent tasks in place of one large job (`--array=1-100%10` caps concurrency), splitting a long job with checkpointing (see `checkpoint-restart-design`). Test candidates with `sbatch --test-only` to compare estimated starts.

### 7. Re-measure after the first production run

Compare actual `MaxRSS`, `Elapsed` and efficiency with the request, and adjust: tighten margins that were too generous, and widen them if the job nearly hit a limit. Record the numbers next to the submission script so the next person starts from measurements.

## Output format

```markdown
## Pilot
[What ran, size, node type, job ID.]

## Measured
[MaxRSS, Elapsed, CPU efficiency, scaling points.]

## Request
[Cores, memory, GPUs, walltime, partition, array shape, each with its margin.]

## Queue evidence
[Pending reason, priority factors, what shape change was chosen.]

## Review
[What to compare after the first production run.]
```

## Anti-patterns

**Requesting the maximum.** It lengthens the wait and spends fair-share for nothing.

**Reading the batch row.** The step row holds the real MaxRSS.

**More cores for a serial program.** Efficiency collapses and the wait grows.

**Sizing once, forever.** Inputs grow; the request should follow a measurement.

## Reference files

- `references/queue-diagnosis.md` - read at step 5: pending reasons, priority factors and what each implies for the request.
