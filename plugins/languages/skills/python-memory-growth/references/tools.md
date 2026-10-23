# Capture recipes and tool notes

Contents: capturing from a live worker, tracemalloc settings, memray usage, allocator experiments, fork measurements.

## Capturing from a worker you cannot restart

Prefer a guarded diagnostic endpoint. A signal handler works but gunicorn and celery already use SIGUSR1 (log reopening; thread tracebacks), so check the server's signal table first and use a signal the server and its supervisor leave unhandled (SIGUSR2 is also taken by some of them, so confirm). The handler starts tracing and writes a snapshot on request:

```python
import os, signal, tracemalloc


def _dump(signum, frame):
    snap = tracemalloc.take_snapshot()
    snap.dump("/var/tmp/snap-%d.bin" % os.getpid())


tracemalloc.start(25)
signal.signal(signal.SIGUSR2, _dump)  # placeholder: use a signal your server leaves unhandled
```

Load two files later with `tracemalloc.Snapshot.load(path)` and call `compare_to`. Restrict the endpoint or signal to operators; a snapshot holds file names, line numbers and sizes, not object contents, but the path to it should still be private.

## tracemalloc notes

- `PYTHONTRACEMALLOC=25` starts tracing at interpreter start with 25 frames; more frames cost more memory and time.
- `snapshot.filter_traces([tracemalloc.Filter(False, tracemalloc.__file__)])` removes the tracer's own allocations.
- `compare_to(old, 'lineno')` groups by file and line; `'traceback'` groups by full stack and shows who called the allocating line.
- tracemalloc does not see memory allocated by C extensions through their own allocators.

## memray

```bash
memray run -o out.bin app.py
memray run --native -o out.bin app.py
memray attach <pid>
memray flamegraph out.bin
memray stats out.bin
```

Use `--native` to include native frames, which is what finds a C extension. A live-process attach needs ptrace permission, which a container may not grant. For forking servers, check the tool's options for following forks before relying on a parent-only trace.

## Allocator experiments

Change one thing per run, run the same load for the same time, and compare the RSS slope:

| Experiment | How |
| --- | --- |
| Limit glibc arenas | `MALLOC_ARENA_MAX=2` in the worker environment |
| jemalloc | Preload the library with `LD_PRELOAD`; confirm it is loaded in `/proc/<pid>/maps` |
| Return free memory | `ctypes.CDLL("libc.so.6").malloc_trim(0)` as a one-off diagnostic |

A change that moves RSS by less than the noise between two identical runs is not an effect.

## Fork measurements

```bash
grep -E '^(Rss|Pss|Shared_Clean|Shared_Dirty|Private_Dirty)' /proc/<pid>/smaps_rollup
```

Growth in `Private_Dirty` across children is copy-on-write un-sharing. Sum PSS across the master and workers to get the real footprint. After `gc.freeze()` in the parent and preloading the app, repeat the measurement after the same number of requests.

## Common owners checklist

Unbounded `lru_cache`, module-level dicts keyed by user or URL, a handler or listener appended per request, thread-locals in pooled threads, `sys.exc_info` or stored exceptions keeping frames alive, ORM identity maps or sessions that outlive a request, and metrics libraries creating a label set per unique value.
