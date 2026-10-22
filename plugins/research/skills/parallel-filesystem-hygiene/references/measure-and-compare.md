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
NAME="group_${SLURM_ARRAY_TASK_ID:-$SLURM_JOB_ID}"
WORK=$(mktemp -d "${TMPDIR:?TMPDIR is not set}/run_${SLURM_JOB_ID}.XXXXXX")
mkdir -p "$WORK/outputs"

pack_and_copy() {
  status=$?
  trap - EXIT TERM
  set +e                       # every step below must run, so the rename and exit are reached
  ok=1
  tar -cf "$WORK/$NAME.tar.part" -C "$WORK" outputs \
    && mv "$WORK/$NAME.tar.part" "$WORK/$NAME.tar" \
    && cp "$WORK/$NAME.tar" "$SCRATCH_OUT/$NAME.tar.part" || ok=0
  if [ "$status" -eq 0 ] && [ "$ok" -eq 1 ]; then
    mv "$SCRATCH_OUT/$NAME.tar.part" "$SCRATCH_OUT/$NAME.tar" || status=1
  else
    mv "$SCRATCH_OUT/$NAME.tar.part" "$SCRATCH_OUT/$NAME.tar.failed"
    [ "$status" -ne 0 ] || status=1
  fi
  exit "$status"
}
trap 'exit 143' TERM            # Slurm sends SIGTERM on TIMEOUT, preemption and scancel
trap pack_and_copy EXIT

cp /path/to/shared/input.bin "$WORK/input.bin"     # staged once per job
./simulate --input "$WORK/input.bin" --out "$WORK/outputs"
```

The `.part` name then rename means a reader never sees a half-copied archive. The final name is taken only when the computation exited 0 and the pack and copy both succeeded; any other outcome leaves at most a `.tar.failed` (absent or incomplete if the pack or copy itself failed) and a non-zero exit. The rename guarantees the copy is whole, not that the computation succeeded, which is what the status test is for.

Three details carry the guarantee. Slurm ends a job that hits its time limit, is preempted or is cancelled with SIGTERM, and without the `TERM` trap bash runs the `EXIT` trap with `$?` equal to 0, so partial output would be published under the final name; the trap turns that into status 143. `set +e` at the top of the handler stops a failed `tar` or `cp` from aborting it before the rename and `exit`. The `${SLURM_ARRAY_TASK_ID:-$SLURM_JOB_ID}` default keeps a job that is not an array element from aborting under `set -u`.

Limits: bash runs a trap only after the foreground command it is waiting on has finished, so a program that ignores SIGTERM keeps the handler from running until Slurm's SIGKILL, which no trap catches (the delay is the cluster's `KillWait` for a timeout or `scancel`, and the partition or QOS `GraceTime` for preemption; check both with the site docs). The pack and copy must also fit in that window, so for long runs copy out at coarse checkpoints as well. The trap does not run at all if the node is lost.

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
