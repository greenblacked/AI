---
paths:
  - "**/*.sbatch"
  - "**/slurm/**/*.sh"
---

# Slurm batch scripts

Loads when a batch script is read or edited. A job the scheduler or the kernel kills often
writes nothing, so what the script requests is what the post-mortem will have to judge it by.

- Request memory explicitly with `--mem=`, `--mem-per-cpu=` or `--mem-per-gpu=`. A site
  default is a number nobody chose, and an `OUT_OF_MEMORY` against it cannot be read.
- Set `--time` from measured progress, not the partition maximum, and add
  `--signal=B:USR1@300` with a handler when the job can checkpoint before the limit.
- Name the logs per task: `--output=%x-%A_%a.out` for an array and `%x-%j.out` otherwise,
  so the first failing index has its own file. Keep `--error` separate when stderr matters.
- Put `module purge` and the exact `module load` lines in the script, and use
  `#!/bin/bash -l` only if the script needs the login profile. Do not rely on the
  submission environment, which `--export=NONE` or a site default removes.
- Throttle an array (`--array=0-499%50`) so one bad input does not fill the queue.
- When a job ends in a state other than `COMPLETED`, start from `sacct` and the step rows,
  not the log, with the `slurm-job-failure-triage` skill, and record it in its
  `failed-job-record.md` template.
