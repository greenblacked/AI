# Benchmark and layouts

Contents: chunks touched per pattern, benchmark skeleton, starting shapes, results table.

## Chunks touched per pattern

For a read described by a half-open range along each dimension, the chunks touched is the product over dimensions of the number of chunk-grid cells the range overlaps.

```python
import math


def chunks_touched(read, chunk):
    """read: list of (start, stop) per dim; chunk: tuple of chunk sizes."""
    n = 1
    for (a, b), c in zip(read, chunk):
        n *= (b - 1) // c - a // c + 1
    return n


shape = (8760, 720, 1440)  # time, y, x
itemsize = 4
patterns = {
    "map": [(0, 1), (0, 720), (0, 1440)],
    "series": [(0, 8760), (300, 301), (700, 701)],
    "window": [(1000, 1100), (200, 264), (500, 564)],
}
candidates = [(1, 720, 1440), (8760, 1, 1), (64, 64, 64), (168, 32, 32)]

for chunk in candidates:
    mib = math.prod(chunk) * itemsize / 2**20
    row = {k: chunks_touched(v, chunk) for k, v in patterns.items()}
    print(chunk, f"{mib:.2f} MiB/chunk", row)
```

The first candidate (a map per chunk) serves the map in one chunk and the series in 8,760; the second is the reverse. A moderate cube serves all three within tens to low hundreds of chunks. Bytes read is chunks touched times chunk bytes (compressed on disk), against the bytes the pattern needs.

## Benchmark skeleton

```python
import time, statistics, numpy as np, h5py


def timed_read(path, dset, selection):
    t0 = time.perf_counter()
    with h5py.File(path, "r") as f:
        data = f[dset][selection]
    return time.perf_counter() - t0, data.nbytes


# Repeat per candidate file and per pattern; each file read for the first time,
# or evicted from the page cache between runs. Report the median of N runs.
```

Record next to each result the storage type, node, library versions and whether the cache was cold. If the page cache cannot be evicted on a shared node, use a set of identical files and read a different one each repeat.

## Starting shapes by access mix

| Dominant mix | Starting chunk (time, y, x), about 1 to 8 MiB | Cost to note |
| --- | --- | --- |
| Maps only | (1, all or large tile of y, x) | Series reads touch every time step |
| Series only | (all or long time block, small y, small x) | Maps touch every spatial tile |
| Maps and series, both common | Moderate in all, such as (64 to 128 in each dimension) | Neither is optimal, none is terrible |
| Random windows | Near the typical window size in each dimension | Larger reads touch more chunks |

Treat the table as a place to start the benchmark, not an answer.

## Results table

```markdown
| Layout | Chunk MiB | Map: chunks / ms / MiB read | Series: chunks / ms / MiB read | Window: chunks / ms / MiB read | File size |
| --- | --- | --- | --- | --- | --- |
```
