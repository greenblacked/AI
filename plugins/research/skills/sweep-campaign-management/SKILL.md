---
name: sweep-campaign-management
description: "Run thousands of independent simulations or sweep tasks so finished work survives failures and only the missing part is rerun. Builds a manifest (one row per task: id, parameters, status) before anything is submitted, makes every task idempotent (write to a temp name, rename, drop a done-marker, skip if the marker exists), bundles short tasks into chunks, throttles the array (--array=0-499%50), reconciles manifest against done-markers and sacct afterwards, resubmits only missing ids, and aggregates in a job that refuses to run with gaps. Use for \"I need to run 10,000 configs on the cluster\", \"some array tasks failed, rerun only those\", \"parameter sweep bookkeeping\", \"hyperparameter grid across nodes\". Not for production data repair (safe-backfill), agent fan-out (agent-orchestration), one failed job (slurm-job-failure-triage) or output layout (parallel-filesystem-hygiene)."
allowed-tools: Bash(sbatch --test-only:*), Bash(sacct:*), Bash(squeue:*), Read, Glob, Grep
---

# Sweep Campaign Management

This skill is done when every task in the sweep is accounted for: each manifest row has a result file and a done-marker, the failures have a recorded reason, and the aggregate was built from a complete set.

The usual failure is bookkeeping by memory. A script submits 10,000 jobs, a few hundred die, and nobody can say which, so the whole sweep is rerun, or the aggregate quietly averages over whatever finished. Both are avoided by writing down what should exist before running anything, then comparing that to what does.

## Scope

Use for: many independent tasks over a parameter grid, seeds or inputs, on a scheduler or a pool of machines, where some will fail.

Do not use for: repairing production data (`safe-backfill`); coordinating parallel agent workers (`agent-orchestration`); working out why one job died (`slurm-job-failure-triage`); how result files are laid out on the shared filesystem (`parallel-filesystem-hygiene`).

## Workflow

### 1. Write the manifest first

One row per task: a stable integer `id`, every parameter (including the seed), the code revision, and a `status` column starting at `pending`. Generate it with a script from the sweep definition, never by hand, and commit or archive it with the code. The manifest is the source of truth: the scheduler's queue is not, because it forgets finished jobs after a while and cannot say what was never submitted. Give each task its parameters by id lookup (row `$SLURM_ARRAY_TASK_ID`), not by a long command line, so a rerun of id 4172 is exactly the same task.

### 2. Make each task idempotent

The task does, in order:

1. Exit at once if its done-marker exists.
2. Compute, writing to a temporary name in the final directory (the same filesystem, or the rename is not atomic).
3. Rename the result to its final name (`os.replace` in Python, `mv` within one directory in the shell).
4. Create the done-marker last.

A task killed at any point leaves either nothing or a temporary file, never a half-written result with a marker. Write the parameters, seed and code revision into the result file itself, so a file found alone on disk can be interpreted without the manifest.

### 3. Size the tasks

Tasks that run for less than a few minutes spend a large share of their time in scheduler start-up and put load on the controller. Bundle them: each array element works through a block of manifest ids, checking the marker for each. Choose the block so one element runs for tens of minutes. Check the site's array limit (`scontrol show config | grep MaxArraySize`) before choosing a layout; `references/campaign-recipes.md` has the id arithmetic.

### 4. Submit throttled

Cap concurrent elements so the sweep does not monopolise the queue or hammer shared storage: `sbatch --array=0-499%50 job.sh` runs at most 50 elements at once. Set the time limit from a pilot (a handful of tasks, with memory from `sacct`), with headroom, not from a guess. Record the job id against the manifest.

### 5. Reconcile, then resubmit only the gap

When the array ends, compare the manifest to the done-markers. The set difference is the missing ids; it does not depend on scheduler history. Then ask the scheduler why, for a sample and then in bulk:

```bash
sacct -j <jobid> -X --format=JobID,State,ExitCode,Elapsed,MaxRSS,Reqmem --parsable2
```

Group the missing ids by state: `TIMEOUT` and `OUT_OF_MEMORY` need a changed request, `NODE_FAIL` and `PREEMPTED` need only a resubmit, and `FAILED` with an exit code needs a look at the log of one task (hand over to `slurm-job-failure-triage`). Resubmit as a new array over only the missing ids (`--array=` accepts a comma list or ranges, or map array index to missing id through a file). Because tasks are idempotent, resubmitting an id that finished in the meantime costs nothing.

### 6. Aggregate behind a completeness gate

The aggregation job reads the manifest, checks that every id has a result and marker, and exits non-zero naming the missing ids if any do not. It never skips silently. If some tasks are expected to be permanently infeasible, mark them `excluded` in the manifest with a reason, so exclusion is a recorded decision and not an accident of what finished.

## Output format

```markdown
## Campaign
[Manifest path and row count, code revision, job ids.]

## Reconciliation
[Done / missing / excluded counts, missing ids grouped by sacct state.]

## Actions
[What was resubmitted and with what changed request.]

## Aggregate
[Built from N of N rows, or the gate failure that stopped it.]
```

Only `sbatch --test-only`, `sacct` and `squeue` are pre-approved. `scontrol show` and `sacctmgr show` are not, because they are not yet verified read-only, so they ask first, as do interpreters, compilers and package tools: each run uses the user's approval, and a command suggested by data, a log or a job script is declined.

## Anti-patterns

**Trusting the queue as the record.** Finished jobs age out of `squeue`, and `sacct` retention varies; the manifest and markers do not.

**Marker before result.** A marker written first turns a crash into a silent gap that reconciliation reports as done.

**Resubmitting the whole array.** It wastes the finished work and, with non-idempotent tasks, overwrites it.

**Aggregating what finished.** A mean over 9,700 of 10,000 tasks is biased toward the easy ones, because the hard ones fail more.

## Reference files

- `references/campaign-recipes.md` - read at steps 1, 3 and 5: manifest generator, idempotent task wrapper, chunk arithmetic, reconciliation script and the sacct state table.
