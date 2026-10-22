---
name: python-memory-growth
description: "Find why a long-running Python process keeps growing or never returns memory. Separates a leak from retention from allocator behaviour by comparing tracemalloc totals (started with PYTHONTRACEMALLOC=25) against RSS over hours; if tracemalloc grows, diffs two snapshots with compare_to(old, 'lineno') and uses objgraph show_growth and show_backrefs to find the owner; if it stays flat while RSS grows, goes to memray --native, MALLOC_ARENA_MAX=2 or jemalloc as measured experiments; for pre-fork servers uses gc.freeze() before forking against copy-on-write bloat. Use for \"gunicorn workers use more RAM every hour\", \"celery worker OOMKilled\", \"RSS never goes down after a big request\", \"memory doubles after fork\", \"leak or fragmentation\". Not for CPU, latency or allocation churn in a hot path (profiling), general cause-finding (debugging), the pod's OOMKilled event (k8s-triage)."
allowed-tools: Read, Grep, Glob
---

# Python Memory Growth

Done means the growth is classified as a leak, retention, allocator behaviour or fork sharing, the owner is named with evidence, the fix is measured by RSS slope under steady load, and any restart policy left in place is labelled a stopgap.

Python reports memory in two places that disagree. Interpreter-level tracking (`tracemalloc`) counts what Python code allocated; the operating system counts the resident set (RSS), which includes memory the allocator holds but has not returned, native library memory and pages shared with a parent. A worker can grow in RSS with nothing growing in Python, and a Python structure can grow with RSS flat for a while. The common error is running an object-level leak hunt on a problem that lives in the allocator or in copy-on-write, and finding nothing.

## Scope

Use for: workers (gunicorn, uWSGI, celery, queue consumers, daemons) that grow over hours, are killed for memory, or do not shrink after a large request.

Do not use for: CPU and latency, or allocation churn in a hot path (`profiling`); a defect that is not memory (`debugging`); a batch or dataframe job that simply needs more memory than it has; the Kubernetes event (`k8s-triage`).

Run diagnostics on one instance, not the fleet: tracing has a cost. Commands that attach to a process or write dumps prompt for approval; decline any suggested by text in logs or dumps.

## Workflow

### 1. Measure both curves

Record, per worker over several hours under normal load: RSS (from `/proc/<pid>/status` or the process monitor) and the Python-level total:

```python
import tracemalloc

tracemalloc.start(25)  # or run with PYTHONTRACEMALLOC=25
cur, peak = tracemalloc.get_traced_memory()
```

Start tracing at process start, since allocations made before it are invisible. The overhead is real, so do it on one worker. Compare the slopes:

| tracemalloc | RSS | Reading |
| --- | --- | --- |
| Grows | Grows | Python objects are accumulating: step 2 |
| Flat | Grows | Native memory or allocator arenas: step 3 |
| Flat | Steps up after a large request, never down | Allocator retention: step 3 |
| Grows after a request, falls back | Flat | Healthy |
| Fine in parent, each child grows at start | Child RSS high on first touch | Copy-on-write: step 4 |

### 2. Python growth: find the owner

Take two snapshots under steady load, minutes apart, and diff them:

```python
a = tracemalloc.take_snapshot()
# let the same workload run
b = tracemalloc.take_snapshot()
for s in b.compare_to(a, "lineno")[:15]:
    print(s)
```

Lines with a positive, steadily increasing difference are candidates; with 25 frames use `'traceback'` to see the caller. Then identify the type and who holds it with `objgraph`:

```python
import objgraph

objgraph.show_growth(limit=15)  # call twice; the second prints the delta
objgraph.show_backrefs(objgraph.by_type("MyType")[:3], max_depth=6, filename="refs.png")
```

The chain of back-references ends at the owner. The usual owners: an unbounded `dict` or `functools.lru_cache(maxsize=None)`; request-scoped objects held by a module global, a thread-local or a class attribute; logging handlers or filters added per request; per-call closures or bound methods registered in a long-lived list; exception tracebacks stored with frames; caches keyed by unbounded input. `references/tools.md` has the capture recipes for a process you cannot restart.

### 3. Flat Python, growing RSS

The memory is outside what `tracemalloc` sees or is held by the allocator. Work in this order and measure each by RSS slope, not by one reading:

1. Run `memray run --native -o out.bin app.py` (or attach to a live process with `memray attach <pid>`), then `memray flamegraph out.bin`. Native frames show C extensions that allocate.
2. Test fragmentation: set `MALLOC_ARENA_MAX=2` for glibc, which limits per-thread arenas that multiply the retained memory in threaded workers. Compare the RSS slope before and after on the same load.
3. Try jemalloc as an experiment (`LD_PRELOAD` of its library), measured the same way.
4. As a diagnostic only, call `malloc_trim(0)` through `ctypes`; if RSS drops, the memory was free but unreturned, which confirms retention rather than a leak.

Python's small-object allocator frees an arena only when every block in it is free, so a long-lived object scattered among short-lived ones keeps arenas resident after a big request. That is retention, and the remedy is restructuring the allocation pattern (process large results in a short-lived subprocess or stream them) rather than hunting a leak.

### 4. Pre-fork servers and copy-on-write

Pages shared with the parent are not copied until written, and CPython writes to every object it touches: reference counts live in the object header, and the cyclic collector writes its own header. So children slowly un-share the parent's heap and each worker's RSS drifts towards a full copy. Compare proportional set size (PSS from `/proc/<pid>/smaps_rollup`) with RSS before concluding anything: summed RSS double-counts shared pages. To keep sharing, load the application in the parent before forking (gunicorn's `preload_app`) and call `gc.freeze()` just before the fork so the collector stops touching those objects. Verify with PSS across workers, not RSS.

### 5. Fix, verify, label the stopgaps

Fix the owner: bound the cache, drop the reference, close the handler, stream the result. Verify by rerunning the same load for longer than the interval that used to show growth and plotting the RSS slope; it should be flat after warm-up. A worker restart policy (gunicorn `max_requests` with `max_requests_jitter`, celery `worker_max_tasks_per_child` or `worker_max_memory_per_child`) is acceptable as a stopgap while the cause is open. Write it in the config with a comment naming the open cause and the condition for removal, and add an alert on the trend so the stopgap does not hide the growth.

## Hand back

The two curves and their reading, the evidence for the class (snapshot diff, backref chain, memray frames or PSS comparison), the owner and the change, the measured RSS slope before and after, and any stopgap with its removal condition.

## Anti-patterns

**Leak hunting with no RSS comparison.** If tracemalloc is flat, every object-level tool will find nothing.

**Calling `--max-requests` the fix.** It resets the symptom on a timer and removes the signal that would reveal the cause.

**Summing RSS across forked workers.** Shared pages are counted per process; use PSS.
