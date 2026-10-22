# Sweep and metrics

Read this at steps 1 to 3 of `SKILL.md`.

## Contents

- [Cross-platform hash check](#cross-platform-hash-check)
- [The parallel sweep](#the-parallel-sweep)
- [The percentile report](#the-percentile-report)

## Cross-platform hash check

Add a command-line entry point to the game or a test build: `gen --seed S --version V --out FILE`, writing the serialised content with a canonical field and entry order. Then:

```bash
set -Eeuo pipefail
outdir=$(mktemp -d)
for s in 0 1 2 3 42 1000003 4294967295; do
  ./gen --seed "$s" --version 3 --out "$outdir/out-$s.bin" || exit 1
  sha256sum "$outdir/out-$s.bin"
done > hashes-$(uname -s)-$(uname -m).txt
```

The fresh directory and the `|| exit 1` mean a failed generation stops the run instead of hashing a file left over from an earlier one. The hashes include the output path, so strip it (`sed 's| .*||'` on each file) before the `diff`, or hash from inside `$outdir`.

Run it on every supported platform and compiler, then `diff` the files. Include seeds at the edges (0, 1, the maximum). A single differing hash is a determinism bug; bisect by hashing intermediate stages (layout, then placement, then loot) to find the stage where the platforms diverge.

## The parallel sweep

A sweep reads a range of seeds, runs the generator and each invariant, and prints failures with the seed. The shape below is a sketch; adapt the import to the project.

```python
import signal
import sys
from multiprocessing import Pool

from gen import generate  # project generator: (seed, version) -> level
from invariants import INVARIANTS  # list of (name, fn(level) -> list[str])

VERSION = 3
SEED_SECONDS = 30  # per-seed budget; a retry-until-valid loop must not hang the sweep


class SeedTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise SeedTimeout(f"no result after {SEED_SECONDS}s")


def check(seed):
    # A crash or a hang is a failure too: report the seed instead of killing
    # or stalling the sweep. SIGALRM is POSIX only; on Windows run the
    # generator in a child process and terminate it on a deadline instead.
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(SEED_SECONDS)
    try:
        level = generate(seed, VERSION)
    except SeedTimeout as exc:
        return [(seed, "timeout", str(exc))]
    except Exception as exc:
        return [(seed, "generate", repr(exc))]
    finally:
        signal.alarm(0)
    found = []
    for name, fn in INVARIANTS:
        try:
            found.extend((seed, name, msg) for msg in fn(level))
        except Exception as exc:
            found.append((seed, name, repr(exc)))
    return found


if __name__ == "__main__":
    start, count = int(sys.argv[1]), int(sys.argv[2])
    failures = []
    with Pool() as pool:
        for found in pool.imap_unordered(check, range(start, start + count), chunksize=500):
            failures.extend(found)
    for seed, name, msg in sorted(failures):
        print(f"FAIL seed={seed} version={VERSION} {name}: {msg}")
    sys.exit(1 if failures else 0)
```

Run `python sweep.py 0 100000` in CI. The per-seed alarm covers the generator call only; keep the invariants cheap, or wrap them the same way. Print enough to reproduce: seed, version and invariant name. For a nightly job, sweep a different range each night and record the ranges covered.

## The percentile report

For each soft metric, write one row per seed to a CSV during the same sweep, then summarise.

```text
metric              p0.1    p1     p50    p99    p99.9   accepted
rooms                 3      6      14     22      26     5 to 24
dead_end_ratio      0.00   0.05   0.22   0.48    0.61     below 0.55
steps_to_first_reward 2     5      31    190     420      below 120
```

The numbers are examples. Read the rows at both ends: the p0.1 row of `rooms` and the p99.9 row of `steps_to_first_reward` name the seeds to render and look at. Add those seeds to a gallery in the review, and set the accepted range only after looking at them.
