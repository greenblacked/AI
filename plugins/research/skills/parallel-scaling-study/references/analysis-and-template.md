# Analysis and template

Contents: analysis script, Slurm skeleton, results table, interpreting the numbers.

## Analysis script

```python
import statistics

# cores -> list of compute-phase times in seconds, one per repeat
runs = {
    1: [812.0, 809.5, 815.2],
    2: [418.1, 416.0, 420.3],
    4: [215.2, 216.8, 214.9],
    8: [114.0, 113.1, 115.5],
    16: [66.2, 65.9, 67.0],
    32: [44.8, 45.5, 44.1],
    64: [38.9, 39.6, 41.2],
}
p0 = min(runs)
t0 = statistics.median(runs[p0])
print("cores  median   range         S      E     KarpFlatt")
for p in sorted(runs):
    t = statistics.median(runs[p])
    lo, hi = min(runs[p]), max(runs[p])
    s = t0 / t
    e = s * p0 / p
    kf = ((1 / s) - (1 / (p / p0))) / (1 - 1 / (p / p0)) if p > p0 else float("nan")
    print(f"{p:5d}  {t:7.1f}  {lo:6.1f}-{hi:6.1f}  {s:6.2f}  {e:5.2f}  {kf:8.4f}")
```

Speedup and efficiency are taken against the smallest core count run, which is only the true serial baseline when that count is 1. For weak scaling report only the efficiency E = t0 / t and skip the speedup and Karp-Flatt columns, which assume a fixed problem size.

## Slurm skeleton for repeats

```bash
#!/bin/bash
#SBATCH --exclusive
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=00:30:00
set -Eeuo pipefail
lscpu > topology_${SLURM_JOB_ID}.txt
srun --cpu-bind=cores ./solver --input case.in --steps 200 --timing timing_${SLURM_JOB_ID}.json
```

Submit it for each core count and repeat, changing `--ntasks` (and `--nodes` past one node) on the command line, for example `sbatch --ntasks=32 --nodes=2 run.sh`. Keep the same input and step count. For a hybrid MPI and OpenMP code, add `--cpus-per-task` and set `OMP_NUM_THREADS` to match it, and treat the split between ranks and threads as a parameter of the study.

## Results table

```markdown
| Cores | Nodes | Median compute (s) | Range (s) | Speedup | Efficiency | Compute / comm / I/O (s) |
| --- | --- | --- | --- | --- | --- | --- |
```

Record beside it: code version, compiler and flags, MPI library, node type, pinning settings, steps timed, date, and whether nodes were exclusive.

## Reading the numbers

| Pattern | Likely meaning |
| --- | --- |
| Efficiency falls smoothly within one node | Memory bandwidth or cache sharing |
| Step down at the first multi-node point | Network cost; check message sizes and counts |
| Karp-Flatt constant | Fixed serial fraction |
| Karp-Flatt rising with cores | Growing communication, imbalance or synchronisation |
| Efficiency above 100 percent at moderate counts | Per-core data fits cache; real but not extendable |
| Large repeat-to-repeat range | Shared nodes, unpinned processes or filesystem noise |
