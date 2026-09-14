# Profiling Python

Read this when the slow code is Python. The runtime's specifics decide which tool tells the truth: function calls are expensive, the interpreter holds a lock, and the deterministic profiler in the standard library distorts exactly the workload people most often point it at.

## Start here: py-spy on the running process

`py-spy` samples another process by reading its memory. It needs no code change, no restart and no import, which makes it the right first tool in production and usually the right first tool locally too.

```bash
py-spy top --pid 1234                                   # live, like top, for a first look
py-spy record -o profile.svg --pid 1234 --duration 60   # a flame graph of a real minute
py-spy dump --pid 1234                                  # every thread's stack, once, for a hang
py-spy record -o profile.svg -- python manage.py import_orders   # profile a run from the start
```

Options worth knowing:

- `--subprocesses` follows workers, which is what you want for gunicorn, celery or multiprocessing; without it you profile the parent doing nothing.
- `--native` includes C extension frames, so time inside numpy, pydantic-core or a database driver stops appearing as one opaque frame.
- `--idle` includes threads that are not running, which turns the CPU profile into a wall-clock one. Use it when the process looks idle but the request is slow.
- `--gil` restricts samples to threads holding the interpreter lock, which is how you tell a genuinely CPU-bound Python program from one that is merely blocked.
- `--rate 250` raises the sample rate for a short window when the function you care about is brief.
- `--format speedscope` when you want an interactive viewer rather than an SVG.

In a container it needs `SYS_PTRACE`, and on a host with `kernel.yama.ptrace_scope` set to 1 it must run as root or attach to a child. That permission requirement is the whole reason a profile does not happen, and it is worth arranging before the incident.

## cProfile, and where it misleads

`cProfile` is an instrumenting profiler: it records entry and exit for every call. That gives exact call counts, which sampling cannot, and it costs a fixed overhead per call, which makes it worst on precisely the call-heavy code you are trying to fix.

```bash
python -m cProfile -o out.prof script.py
python -m pstats out.prof           # then: sort tottime / stats 20 / callers parse_line
```

Read `tottime` first — time in the function's own bytecode — and `cumtime` to find the subtree worth removing. A function with a million calls and a tiny `tottime` each is a call-count problem; the fix is at its caller.

Two honest limits. The overhead is roughly proportional to the number of calls, so a result showing many small functions at the top is partly measuring the profiler, and a sampled profile from py-spy is the cross-check. And `cProfile` profiles one thread: it is the calling thread's story, so a thread pool or a background worker needs `yappi`, which handles threads and asyncio and can report either CPU or wall clock.

For a line-level answer inside one function that you already know is hot, `line_profiler` decorates the function and reports per line, at high overhead. Use it on a single function, never on a program.

## asyncio

An `await` is not a call the profiler can attribute. Time spent awaiting shows up in the event loop's `select` or `epoll` frame, so a coroutine that waits three seconds on a downstream service looks free, and the slow thing looks like the loop.

Consequences worth internalising:

- Use `yappi` with wall-clock timing, or py-spy with `--idle`, when the question is where a request's latency went.
- A CPU profile of an async service answers a different question: which synchronous code is blocking the loop. That is often the real defect — one `requests.get`, one `time.sleep`, one heavy `json.loads` on a large body, stalling every other task.
- `asyncio.run(..., debug=True)` logs callbacks that take longer than 100ms, which finds the blocking call without a profiler at all.

## The GIL, threads and processes

CPU-bound Python does not scale across threads, so a thread pool on a parsing workload produces the same throughput with more context switching. The diagnostic is `py-spy top --gil --pid <pid>`: if threads are mostly holding the lock, the work is interpreter-bound and the answer is fewer Python-level operations, a C extension, or multiple processes.

Before reaching for multiprocessing, count the cost: every argument and result is pickled and copied, so a pool over small tasks spends its gain on serialisation. It pays for coarse work on large inputs, and not much else.

## Allocation and object churn

`tracemalloc` is in the standard library and attributes allocations to the line that made them, which is enough for churn in a hot path.

```python
import tracemalloc

tracemalloc.start(10)
before = tracemalloc.take_snapshot()
run_the_workload()
after = tracemalloc.take_snapshot()
for stat in after.compare_to(before, "lineno")[:20]:
    print(stat)
```

`memray` is the heavier tool and worth installing when `tracemalloc` is not enough: `memray run -o out.bin script.py` then `memray flamegraph out.bin`, and it sees native allocations too.

Read allocation counts alongside bytes. A million small dicts created per request is a GC pressure problem fixed by not creating them; `gc.freeze()` after startup and tuning `gc.set_threshold` are the follow-ups, not the first move.

## Benchmarking traps specific to this runtime

- `timeit` disables the garbage collector while timing, which is deliberate for comparing expressions and dishonest for a workload whose cost is allocation. Re-enable it in setup when GC is the thing you care about.
- Import time is real and invisible: `python -X importtime script.py` prints a per-module tree, and a CLI that takes 900ms before doing anything is usually importing a data-science stack it does not need.
- Attribute lookup, function calls and `isinstance` checks cost more than they look, so a hoist out of a loop is a genuine win in Python in a way it is not in a compiled language. This is a constant-factor fix, step four in the skill's order, and it comes after doing less work.
- `DEBUG = True` in Django keeps every SQL query in memory for the life of the request, which makes a profile of a development server wrong in both time and memory.
