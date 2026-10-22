# Measure and compare

Contents: baseline, job-script skeleton, hash sharding, before and after table.

## Baseline

Record these for one representative run, before any change, at the production scale (or a stated fraction of it):

| Measure | How |
| --- | --- |
| Files created per run | Count from the code or manifest: tasks times steps times files per step |
| Quota files used before and after | `lfs quota -u $USER /path/to/scratch` |
| Elapsed time and where it goes | Timers around the write calls, or the code's own I/O timer; `sacct -j JOBID --format=JobID,Elapsed,TotalCPU,AllocCPUS` for the whole job |
| Time for a directory listing | One `ls -f dir` timed by hand on a quiet moment, noted as a symptom, not a benchmark |
| Metadata operations | The site's per-job I/O statistics, where available; ask support what they expose |

Run the baseline job twice; shared filesystems are noisy and a single run can mislead. Note the time of day and the number of other users busy if the site shows it.

## Job-script skeleton

```bash
#!/bin/bash
set -Eeuo pipefail
SCRATCH_OUT=/path/to/shared/results
WORK="${TMPDIR:?TMPDIR is not set}/run_${SLURM_JOB_ID}"
mkdir -p "$WORK/outputs"

pack_and_copy() {
  status=$?
  trap - EXIT
  tar -cf "$WORK/group_${SLURM_ARRAY_TASK_ID}.tar.part" -C "$WORK" outputs
  mv "$WORK/group_${SLURM_ARRAY_TASK_ID}.tar.part" "$WORK/group_${SLURM_ARRAY_TASK_ID}.tar"
  cp "$WORK/group_${SLURM_ARRAY_TASK_ID}.tar" "$SCRATCH_OUT/group_${SLURM_ARRAY_TASK_ID}.tar.part"
  if [ "$status" -eq 0 ]; then
    mv "$SCRATCH_OUT/group_${SLURM_ARRAY_TASK_ID}.tar.part" "$SCRATCH_OUT/group_${SLURM_ARRAY_TASK_ID}.tar"
  else
    mv "$SCRATCH_OUT/group_${SLURM_ARRAY_TASK_ID}.tar.part" "$SCRATCH_OUT/group_${SLURM_ARRAY_TASK_ID}.tar.failed"
  fi
  exit "$status"
}
trap pack_and_copy EXIT

cp /path/to/shared/input.bin "$WORK/input.bin"     # staged once per job
./simulate --input "$WORK/input.bin" --out "$WORK/outputs"
```

The `.part` name then rename means a reader never sees a half-copied archive, and the trap keeps the exit status so a failed run is copied out as `.tar.failed` and never takes the final name; the rename guarantees the copy is whole, not that the computation succeeded, which is what the status test is for. The trap runs on normal exit and on an error that `set -e` turns into an exit; it does not run if the node is lost or the job is killed with SIGKILL, so also copy out at coarse checkpoints for long runs.

## Hash sharding

```python
import hashlib, pathlib


def shard_path(root, task_id):
    h = hashlib.sha1(str(task_id).encode()).hexdigest()
    return pathlib.Path(root) / h[:2] / h[2:4] / f"{task_id}.h5"
```

Two levels of two hex characters give 65,536 leaf directories, which keeps each small up to hundreds of millions of files. One level is enough for a few million.

## Before and after

```markdown
| Measure | Before | After |
| --- | --- | --- |
| Files created per run | | |
| Quota files used | | |
| I/O time (s) | | |
| Elapsed (s) | | |
| Listing time of output directory (s) | | |
```

State the job id of each run and that scale and node type were the same. If elapsed time did not fall but the file count did, say so: the quota problem is fixed and the slowness has another cause, which is a question for `profiling`.
