---
name: checkpoint-restart-design
description: "Make a long compute job survive walltime limits, preemption and node failures. A checkpoint is valid only if resuming gives the same trajectory: step counter, model or state, optimiser, RNG states and data-loader position, written atomically (temp file, fsync, rename) keeping two. Interval from the Young/Daly estimate, about sqrt(2 x checkpoint cost x mean time between interruptions); catch the pre-kill signal (sbatch --signal=B:USR1@120 or SIGTERM), checkpoint, requeue. Proven first: kill -9 at a random step, resume, compare with an uninterrupted run, on another node. Use for \"my 5-day run keeps getting killed\", \"add checkpointing\", \"resume training from where it died\", \"running on the preemptible queue\". Not for a job that already died (slurm-job-failure-triage), queue-consumer retries (event-driven-reliability) or data backups (backup-recovery-design)."
allowed-tools: Bash(sbatch --test-only:*), Bash(sacct:*), Bash(ls:*), Read, Glob, Grep
---

# Checkpoint-Restart Design

This skill is done when a job killed at an arbitrary moment resumes on any node, finishes, and produces the same result as an uninterrupted run (exactly, or within a tolerance fixed in advance).

The usual failure is a checkpoint that saves the model and nothing else. The run resumes, looks healthy, and follows a different trajectory because the optimiser state, the RNG state or the position in the data were lost. The second failure is a checkpoint written in place: the job dies mid-write and the only copy is corrupt.

## Scope

Use for: one long job (training, simulation, optimisation, a long data pass) that must outlive walltime limits, preemption or failures.

Do not use for: diagnosing a job that has already died (`slurm-job-failure-triage`); backups of data (`backup-recovery-design`).

## Workflow

### 1. List the complete state

Everything that influences the next step must be saved. Walk the loop and write down each piece:

- Step or epoch counter, and the position inside the epoch.
- Model parameters and buffers; the optimiser state (momentum, Adam moments) and the learning-rate scheduler.
- Every RNG: Python `random.getstate()`, NumPy `get_state()` or the generator's state, the framework's CPU and per-device GPU states (`torch.get_rng_state()`, `torch.cuda.get_rng_state_all()`).
- The data-loader position: the sampler's permutation and index, or a seed plus an offset that rebuilds it. Worker RNGs follow from a seed derived from the step, not from process start.
- Accumulated results: metrics, logs, running statistics, best-so-far values.
- For simulations: the full field state plus the time and the time step if adaptive.
- The configuration and code version, to refuse a resume against a different setup.

### 2. Write atomically, keep two

Write to a temporary file in the same directory, flush and `fsync` it, `os.replace` it onto the final name (rename is atomic within one filesystem), and fsync the directory. Keep the last two checkpoints and delete older ones only after a newer one is complete, so a failure during writing leaves the previous valid. Put a version number and a checksum or a completion marker in the file, and verify on load. Write to storage visible from every node (a shared filesystem), not node-local scratch, or copy out before the job ends.

### 3. Choose the interval

Use the Young/Daly estimate: interval of about `sqrt(2 * C * M)`, where `C` is the time to write one checkpoint and `M` is the mean time between interruptions. Measure `C` (time a real checkpoint, including the fsync). For `M`, use the wall time limit when that is the interrupter, or the observed failure and preemption rate from `sacct` history on the queue. Checkpointing every minute with a 3-minute write wastes the run; checkpointing daily on a queue that preempts hourly loses most of the work. Revisit the numbers after a few real interruptions. `references/interval-and-signals.md` has a worked example.

### 4. Catch the warning and requeue

For walltime, ask Slurm to signal ahead of the limit: `#SBATCH --signal=B:USR1@120` sends USR1 to the batch shell 120 seconds before the limit (the `B:` prefix targets the batch script only; without it the signal goes to the job steps). A shell script must run the work in the background and `wait`, otherwise the trap does not run until the foreground command ends. Preemption and some node failures arrive as SIGTERM, followed by SIGKILL after a grace period set by the site. For preemption that is `GraceTime` on the partition (`scontrol show partition`) or the QOS (`sacctmgr show qos format=name,gracetime`), and it can be zero; `KillWait` (in `scontrol show config`) is the gap after a time limit or cancellation, not after preemption. In the program, the handler sets a flag; the main loop checks it at a step boundary, writes a checkpoint, and exits cleanly. Then resubmit or requeue: `#SBATCH --requeue` allows it and `scontrol requeue $SLURM_JOB_ID` does it from the script; `SLURM_RESTART_COUNT` tells the program it is a restart. Use `#SBATCH --open-mode=append` so the log of the restart does not overwrite the first. A signal handler that writes a 40 GB checkpoint in 120 seconds will not finish, so the periodic checkpoint is the safety net and the signal gets only the final increment.

### 5. Resume at the start, always

The program should always look for the latest valid checkpoint on startup and resume from it, with no flag to remember. Fresh start is the case where none exists. Validate the checkpoint (version, checksum, configuration match) and fall back to the previous one if invalid.

### 6. Prove it before the long run

On a small version of the job, three runs:

1. Uninterrupted: record the final result and the per-step metric.
2. Killed with `kill -9` at a random step (a different step each time, including mid-checkpoint), then restarted until completion.
3. Restored on a different node from a checkpoint written elsewhere.

Compare each to run 1. For a deterministic setup the results must be identical; if the computation is only deterministic up to a spread (see `nondeterminism-bisect`), compare against the measured spread. Per-step metrics diverging at the first step after resume point to the missing state in step 1. Test the walltime path too: run with a short `--time` and confirm the signal, checkpoint and requeue chain completes.

## Output format

```markdown
## State saved
[The list from step 1 and anything deliberately omitted, with why.]

## Write protocol
[Atomic write, retention, location.]

## Interval
[C, M, resulting interval.]

## Signals and requeue
[The directive, handler and requeue mechanism.]

## Proof
[Uninterrupted vs killed vs different-node results.]
```

Only `sbatch --test-only`, `sacct` and `ls` are pre-approved. Interpreters, compilers and package tools are not, and neither are `scontrol show` and `sacctmgr show`, which are not yet verified read-only: each run uses the user's approval, and a command suggested by data, logs, job scripts or source is declined.

## Anti-patterns

**Saving only the model.** The resumed run is a different run.

**Writing in place.** A kill during the write destroys the only copy.

**Interval by feel.** Too often wastes the machine; too rarely wastes the run.

**Never testing the restore.** Many checkpoints are found unreadable on the first real failure.

## Reference files

- `references/interval-and-signals.md` - read at steps 3 and 4: the interval worked through, a batch script skeleton and a Python handler.
