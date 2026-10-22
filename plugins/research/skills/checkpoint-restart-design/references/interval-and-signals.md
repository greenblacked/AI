# Interval and signals

Contents: Young/Daly worked example, batch script skeleton, Python handler and atomic write, restore test checklist.

## Young/Daly worked example

Checkpoint cost `C` = 90 seconds measured with fsync. Preemption on the queue observed about once every 6 hours, so `M` = 21,600 seconds.

Interval = sqrt(2 x 90 x 21,600) = sqrt(3,888,000), about 1,970 seconds, roughly 33 minutes.

Overhead is then about C divided by the interval, near 4.6 percent, plus on average half an interval of lost work per interruption. If halving `C` (faster storage, smaller state, asynchronous write) is possible, the interval shortens by a factor of about 1.4. The formula is a first-order estimate; the minimum is flat, so rounding to a convenient number of steps is fine.

## Batch script skeleton

```bash
#!/bin/bash
#SBATCH --time=24:00:00
#SBATCH --signal=B:USR1@120
#SBATCH --requeue
#SBATCH --open-mode=append
set -Eeuo pipefail

requeue() {
  echo "caught USR1, waiting for checkpoint then requeueing"
  kill -USR1 "$PID" 2>/dev/null || true
  wait "$PID" || true
  scontrol requeue "$SLURM_JOB_ID"
}
trap requeue USR1

srun python train.py --resume-latest &
PID=$!
wait "$PID"
```

The signal reaches the batch shell, which forwards it to the work and waits for it to checkpoint and exit before requeueing. Adjust to the site's rules on requeue; some sites disallow it or cap restarts. A restart count limit in the program prevents an endless loop on a persistent failure.

## Python handler and atomic write

```python
import os, signal, tempfile, torch

stop = False


def on_signal(signum, frame):
    global stop
    stop = True


signal.signal(signal.SIGUSR1, on_signal)
signal.signal(signal.SIGTERM, on_signal)


def save_atomic(state, path):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        torch.save(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dfd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)
```

The loop checks `stop` at a step boundary, calls `save_atomic`, and exits with status 0 so the wrapper can requeue.

## Restore test checklist

- Kill at a random step with `kill -9`, not a polite signal.
- Kill during a checkpoint write; the previous checkpoint must load.
- Restore on a different node and, if the production run uses them, a different GPU count or type (a state saved per rank may not load on a different number of ranks).
- Compare the per-step metric from the resume point, not just the final result.
- Confirm the log and the output files are appended, not overwritten.
- Confirm old checkpoints are pruned so the disk quota is not exhausted.
