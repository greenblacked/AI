# Campaign recipes

## Manifest

A CSV or Parquet file, one row per task. Columns: `id`, one column per parameter, `seed`, `code_rev`, `status`. Generate from the grid:

```python
import itertools, csv, os

grid = {"lr": [1e-3, 1e-2], "width": [64, 128, 256], "seed": range(100)}
keys = list(grid)
path = "manifest.csv"
existing = {}  # parameter tuple (as strings) -> id
if os.path.exists(path):
    for r in csv.DictReader(open(path)):
        existing[tuple(r[k] for k in keys)] = int(r["id"])
next_id = max(existing.values(), default=-1) + 1
new = [v for v in itertools.product(*grid.values()) if tuple(map(str, v)) not in existing]
write_header = not existing
with open(path, "a", newline="") as f:
    w = csv.writer(f)
    if write_header:
        w.writerow(["id", *keys, "code_rev", "status"])
    for vals in new:
        w.writerow([next_id, *vals, REV, "pending"])
        next_id += 1
```

Ids are append-only: an existing parameter tuple keeps its id and only new tuples get fresh ones. Numbering by position in the product would shift every later id when a value is added to any key but the first, and the done-markers, which are keyed by id, would then mark different parameters as finished.

## Idempotent task wrapper

```python
import json, os, sys, pathlib

tid = int(sys.argv[1])
out = pathlib.Path("results")
final, marker = out / f"{tid:06d}.json", out / f"{tid:06d}.done"
if marker.exists():
    sys.exit(0)
tmp = out / f".{tid:06d}.json.tmp.{os.getpid()}"
result = run_task(params_for(tid))  # includes params, seed, code_rev
tmp.write_text(json.dumps(result))
os.replace(tmp, final)  # atomic: same directory
marker.touch()  # last
```

Stale `.tmp` files from killed tasks are harmless; delete them after reconciliation.

## Chunk arithmetic

For `N` manifest rows and `B` rows per array element: elements = ceil(N / B); element `k` handles ids `k*B` to `min((k+1)*B, N) - 1`. For 10,000 rows of 2-minute tasks and B = 20, that is 500 elements of about 40 minutes: `--array=0-499%50`. Inside the element, loop over its ids and skip any with a marker. Check elements against `MaxArraySize` first.

## Reconciliation

```python
import pathlib, csv

rows = list(csv.DictReader(open("manifest.csv")))
ids = {int(r["id"]) for r in rows if r["status"] != "excluded"}
markers = {int(p.stem) for p in pathlib.Path("results").glob("*.done")}
results = {int(p.stem) for p in pathlib.Path("results").glob("*.json")}
done = markers & results & ids  # a marker without its result is not done
missing = sorted(ids - done)
print(len(ids), len(done), len(missing))
```

Resubmit with a comma list of elements that contain a missing id, for example `sbatch --array=3,17,201 job.sh`; the markers skip finished rows inside them.

## sacct states and the usual response

| State | Meaning | Response |
| --- | --- | --- |
| COMPLETED but no marker | Task exited 0 without finishing the write | Fix the wrapper; rerun |
| TIMEOUT | Hit the time limit | Raise the limit or split the task |
| OUT_OF_MEMORY | Exceeded the memory request | Raise from the MaxRSS of the largest finished tasks |
| NODE_FAIL | Node lost | Resubmit unchanged |
| PREEMPTED | Taken by higher-priority work | Resubmit; consider checkpointing |
| CANCELLED | Cancelled by a person or policy | Find out who and why before resubmitting |
| FAILED | Non-zero exit | Read one task's log; may be deterministic for those parameters |

A task that fails identically for the same parameters is a result about the parameters (infeasible region), and belongs in the manifest as `excluded` with a reason.
