# Manifest and seeds

## Contents

- Manifest writer
- Environment record
- Seeding
- Rerun comparison

## Manifest writer

```python
import hashlib, json, subprocess, sys, platform
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def check_clean(allow_dirty=False):
    """Call once at pipeline start, before any output is written."""
    dirty = bool(git("status", "--porcelain"))
    if dirty and not allow_dirty:
        raise RuntimeError("working tree is dirty; commit before producing a result")
    return dirty


def write_manifest(output, inputs, params, seeds, env_record, dirty):
    manifest = {
        "output": str(output),
        "output_sha256": sha256(output),
        "inputs": {str(p): sha256(p) for p in inputs},
        "commit": git("rev-parse", "HEAD"),
        "dirty": dirty,
        "params": params,
        "seeds": seeds,
        "environment": str(env_record),
        "python": sys.version,
        "platform": platform.platform(),
    }
    Path(f"{output}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
```

Call `check_clean` once at the start of the pipeline, before anything is computed, so a dirty tree stops the run instead of wasting it, and pass its result to `write_manifest` for each output. The check must run before outputs exist: a freshly written output is untracked and an overwritten expected result shows as modified, so either would fail a later check. Output and scratch directories must be listed in `.gitignore` (or the status call limited to source paths) rather than loosening the check.

## Environment record

Run once per pipeline execution and store with the results:

```bash
{
  uname -a
  python3 -V
  pip freeze --all
  python3 -c "import numpy; numpy.show_config()"
  lscpu | grep -E 'Model name|Architecture|Flags' | head -3
  nvidia-smi --query-gpu=name,driver_version --format=csv 2>/dev/null || echo "no gpu"
  gcc --version | head -1
} > results/environment.txt
```

Add the CUDA version the framework reports (for PyTorch, `torch.version.cuda`), and the container image digest if one is used. `pip freeze` lists installed versions but not hashes; the hashed lockfile is the input, this file is the record of what resulted.

## Seeding

```python
import random, hashlib
import numpy as np


def task_seed(base_seed, *identity):
    key = f"{base_seed}:" + ":".join(map(str, identity))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")


seed = task_seed(1234, "bootstrap", fold)
random.seed(seed)
rng = np.random.default_rng(seed)  # pass rng into functions; do not call np.random.* directly
```

| Source | How to seed | Easily missed |
| --- | --- | --- |
| `random` | `random.seed(s)` | Libraries that call it internally |
| NumPy | `np.random.default_rng(s)` | Legacy `np.random.seed` affects only the legacy global state |
| PyTorch | `torch.manual_seed(s)` | CUDA state is seeded by it, but not all kernels are deterministic |
| DataLoader | `generator=torch.Generator().manual_seed(s)` and `worker_init_fn` | Workers each derive their own state; augmentation uses it |
| JAX | `jax.random.key(s)` split explicitly | Reusing a key gives identical draws |
| Hash order | `PYTHONHASHSEED=s` in the environment | Must be set before the interpreter starts |
| Parallel code | One seed per task from `task_seed`, not per worker | Results depend on scheduling if seeds follow worker order |

## Comparing a rerun

```python
import numpy as np

np.testing.assert_allclose(new, old, rtol=1e-6, atol=1e-12)
```

Set `rtol` per output from measured variation: run the pipeline on two machines, or with different thread counts, and take a margin above the spread observed. For stochastic results, compare a summary with its interval (the old estimate should lie within the new run's interval), and say so in the README.
