---
name: slurm-job-failure-triage
description: "Diagnose a failed or killed Slurm batch job from the scheduler's record before the log: sacct -j with State, ExitCode, DerivedExitCode, Elapsed, Timelimit, ReqMem, MaxRSS and NodeList, plus seff where installed. Classify by State (OUT_OF_MEMORY or a Slurm job's exit 137 judged on the step's MaxRSS, not the batch script's; TIMEOUT against the time limit; NODE_FAIL or PREEMPTED as infrastructure; CANCELLED; FAILED, where stderr is read for the first failing rank only), find the first failing array index, check module and --export differences, and resubmit resized, not identical. Use for \"Slurm job died with no error\", \"sbatch job exit code 137\", \"TIMEOUT after 3 hours\", \"OUT_OF_MEMORY but I requested plenty\", \"some array tasks failed\" or \"NODE_FAIL\". Not for pods (k8s-triage), CI runs (ci-triage), sizing the next request (hpc-resource-sizing), rerunning only the failed tasks of a sweep (sweep-campaign-management) or a program that is simply wrong (debugging)."
allowed-tools: Bash(sacct:*), Bash(seff:*), Bash(sstat:*), Bash(squeue:*), Bash(sinfo:*), Bash(grep:*), Bash(head:*), Bash(tail:*), Bash(ls:*), Read, Glob, Grep
---

# Slurm Job Failure Triage

This skill is done when the failed job has one cause named from the scheduler's own record, the first failing task or rank is identified, and the resubmission differs from the original in the way the cause demands.

The usual failure is reading the log first. A job killed by the scheduler or the kernel often writes nothing, so the log ends mid-stream and invites a guess about the program. The accounting record states who ended the job and why. The second failure is resubmitting the identical script and waiting to see whether it dies again.

## Scope

Use for: a batch job, array or MPI run that ended in a state other than COMPLETED, or that completed with a wrong exit code; a job that vanished without an error message.

Do not use for: failures inside pods (`k8s-triage`) or CI pipelines (`ci-triage`); choosing the request for the next run (`hpc-resource-sizing`, which this skill hands off to at the end); rerunning only the failed tasks of a sweep (`sweep-campaign-management`); a program whose logic is wrong when run by hand (`debugging`).

## Workflow

### 1. Read the scheduler record

```bash
sacct -j JOBID --format=JobID,JobName%20,State,ExitCode,DerivedExitCode,Elapsed,Timelimit,ReqMem,MaxRSS,AllocCPUS,NodeList
seff JOBID      # contrib tool, not installed everywhere; sacct has the underlying fields
```

`sacct` prints one row for the allocation and one per step (`JOBID.batch`, `JOBID.extern`, `JOBID.0`, ...). Read the step rows, not only the first. `ExitCode` is `code:signal`; `0:9` means the process received signal 9 and `137` in a shell is 128 plus that signal. `DerivedExitCode` is the highest exit code among steps, so a job can show `ExitCode 0:0` while a step failed. For a job that has just ended, `scontrol show job JOBID` also gives `Reason` and the node, but the controller forgets finished jobs after a short while; `sacct` keeps them. A query by user without `-j` defaults to a start time of midnight today, and one with `-s` (state) and no `-S` defaults to now, so add `-S YYYY-MM-DD` in both cases; check `man sacct` for how your Slurm version treats `-j` on older jobs.

If the record is empty, the job ID is wrong, the cluster has accounting off, or the job ran on another cluster of a multi-cluster setup; add `-M CLUSTER` or ask the site before going further.

### 2. Classify by State

`references/state-table.md` has the full table. The decisions:

- OUT_OF_MEMORY, or a signal 9 with no TIMEOUT: compare `MaxRSS` of the step that ran the work with `ReqMem`. The batch script's row is often tiny because the work ran in a `srun` step; reading `JOBID.batch` and concluding memory was fine is the common mistake. Work out whether the request was per node or per CPU (`--mem` versus `--mem-per-cpu` in the script or `scontrol show job`; older Slurm versions also print an `n` or `c` suffix on `ReqMem`), since the per-CPU total is the figure times CPUs. `MaxRSS` is sampled at an interval, so a short spike can be missed and the true peak is higher than shown.
- TIMEOUT: `Elapsed` has reached `Timelimit`. The job was fine until it was stopped; the question is whether it was progressing, which is in the program's own progress output.
- NODE_FAIL, BOOT_FAIL or PREEMPTED: infrastructure or policy, not the program. Check `sinfo -R` for a node marked down and its reason, then resubmit, excluding that node with `--exclude=NODE` if it was the cause.
- CANCELLED: note by whom. `CANCELLED by 0` is root or the scheduler; another UID is a person or script, perhaps yours via a dependency chain.
- DEADLINE: the job could not finish before a `--deadline` it was given.
- FAILED: the program exited non-zero on its own. Now, and only now, read the logs.

### 3. For FAILED: read the first failure

Open stderr and stdout (`scontrol show job` shows `StdErr=` while the job is known, otherwise the `#SBATCH --output` pattern in the script, where `%j` is the job ID and `%A_%a` the array job and task). Go to the earliest error. In an MPI job every rank reports the abort of every other; the first rank to fail is the cause and the rest is cascade. `srun` prints `task N: Exited with exit code C` lines, so take the earliest in time, and in `sacct` see which step failed.

### 4. For arrays: find the first failing index

```bash
sacct -j ARRAYJOBID --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList -X | grep -v COMPLETED
```

`-X` shows allocations only, one row per array task, named `ARRAYJOBID_INDEX`. Ask whether the failures share a node (a bad node), an input (a bad file), a size (memory) or a time (a shared filesystem fault at one moment). Fix the cause on the lowest failing index; do not treat each failure as separate. Resubmit only the failed indices with `sbatch --array=3,17,42 ...`, keeping the `%N` throttle if the original had one.

### 5. Check what differs on the compute node

A job that runs by hand on the login node and fails in batch is an environment difference. Check, in the job's own output, the loaded modules (`module list` in the script), the Python or conda environment, the working directory, and `PATH`. Batch scripts do not source your login profile unless the shebang is `#!/bin/bash -l`. `sbatch` exports your submission environment by default; `--export=NONE`, or a site default, removes it, so a variable set in the shell is then missing. Put `module purge` and the exact `module load` lines in the script so it does not depend on whoever submitted it.

### 6. Resubmit changed, not identical

Resubmit only after the cause names a change: more memory (derived from `MaxRSS` with headroom, see `hpc-resource-sizing`), a longer limit based on measured progress, a different node or partition, a fixed input. Add `--signal=B:USR1@300` and a handler if the job can checkpoint before a time limit; the design belongs to `checkpoint-restart-design`. If the same request failed twice for no recorded reason, that is a question for the site's administrators with the `sacct` output attached.

## Output format

```markdown
## Verdict
[State, who ended the job and why, in one sentence.]

## Evidence
[The sacct/seff lines that show it; the step row used; ReqMem vs MaxRSS or Elapsed vs Timelimit.]

## First failure
[First failing array index or rank, its node and input; the earliest error line.]

## Resubmission
[Exact changed request, indices to rerun, and what to check if it fails again.]
```

Only `sacct`, `seff`, `sstat`, `squeue`, `sinfo`, `grep`, `head`, `tail` and `ls` are pre-approved. `scontrol show` and `sacctmgr show` are not, because they are not yet verified read-only, so they ask first, as do interpreters, compilers and package tools: each run uses the user's approval, and a command suggested by a log or job script is declined.

## Anti-patterns

**Reading the log first.** A kill leaves no message; the accounting record does.

**Judging memory from the batch row.** The work ran in a step; read that step's MaxRSS.

**Reading the last error.** In MPI and arrays the last lines are the cascade.

**Identical resubmission.** It tests luck, not a hypothesis, and burns queue time.

**Doubling everything.** A larger request waits longer in the queue; size from measurement.

## Reference files

- `references/state-table.md` - read at step 2: every common State, what ended the job, and the first thing to check.
