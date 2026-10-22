---
name: reproducible-analysis-environment
description: "Make an analysis rerunnable by others later, with every derived file traceable to raw data, and prove it on a clean machine. One command (make, snakemake or just) from raw data to every figure and table, run clean; a hash-locked lockfile plus what lockfiles miss (OS, compiler, BLAS build, CUDA and driver, CPU architecture); each RNG source seeded separately; raw data content-addressed and read-only; a sidecar manifest per derived file with input hashes, commit with a dirty flag that blocks the run, parameters and environment. Use for \"I can't reproduce my own results\", \"it worked on my laptop\", \"make this analysis reproducible\" or \"which data version made this figure\". Not for pipeline scheduling (ci-pipeline-design), upgrades (dependency-upgrade), compose files (docker-compose) or reruns that already differ (nondeterminism-bisect)."
allowed-tools: Bash(git rev-parse:*), Bash(sha256sum:*), Bash(diff:*), Bash(lscpu:*), Bash(nvidia-smi -L), Bash(uname:*), Read, Write, Edit, Glob, Grep
---

# Reproducible Analysis Environment

This skill is done when a person who has only the repository and the raw data can run one command on a clean machine, obtain every figure and table within stated tolerances, and pick any output at random and trace it to the raw file and code revision that made it in ten minutes.

The usual failure is a claim of reproducibility that was never tested. The analysis works because of an unrecorded state: a package installed by hand, a notebook cell run out of order, a cached intermediate file whose inputs have since changed, a raw file edited in place. A requirements file with loose pins records intent, not the environment. The only evidence that counts is a rerun from nothing.

## Scope

Use for: a research or data analysis project that must be rerun by others, by a reviewer, or later by its author; tracing a figure back to its inputs.

Do not use for: putting a job into production scheduling (`ci-pipeline-design`); changing dependency versions (`dependency-upgrade`); writing compose files (`docker-compose`); explaining why two runs of the same code differ (`nondeterminism-bisect`, which starts where this skill ends).

## Workflow

### 1. Fix the entry point

Create one command that goes from raw data to every figure and table the work reports: a `Makefile`, a `Snakefile` run with `snakemake --cores N`, or a `justfile`. Each rule names its inputs and outputs so the tool rebuilds only what changed. A notebook may explore, but the outputs that appear in the write-up come from scripts the entry point calls, or from notebooks run top to bottom by it (for example with `jupyter nbconvert --to notebook --execute`). A figure made by hand-run cells is not reproducible, whatever the file says.

### 2. Make raw data immutable and content-addressed

Put raw data in one directory marked read-only (`chmod -R a-w data/raw`). Record a SHA-256 for every file at ingest, recursively and in a stable order (`find data/raw -type f -print0 | sort -z | xargs -0 sha256sum > data/raw.sha256`), and have the first rule of the pipeline regenerate that listing and compare it (`find data/raw -type f -print0 | sort -z | xargs -0 sha256sum | diff - data/raw.sha256`). Comparing the whole listing fails on a changed, missing or newly added file; `sha256sum -c` alone checks only the files already listed. If the data cannot be committed, record where it came from (URL or accession, retrieval date, version) in the same file. A raw file that changes must change its hash, so a result can always say which data it used.

### 3. Pin the environment, and record what pinning misses

Resolve to exact versions with hashes: `pip-compile --generate-hashes` (pip-tools) or `uv pip compile --generate-hashes`, installed with `pip install --require-hashes -r requirements.txt`; or a conda lock file from `conda-lock`. A container image pinned by digest, not tag, pins the user space as well.

A lockfile does not record the operating system and its libc, the compiler, the BLAS and LAPACK implementation and version (OpenBLAS, MKL), the CUDA toolkit and GPU driver, or the CPU architecture. Floating-point results can depend on all of these. Write them to a file the pipeline produces on every run: `uname -a`, `python3 -c "import numpy; numpy.show_config()"`, `lscpu`, `nvidia-smi`, and the framework's reported CUDA version. See `references/manifest-and-seeds.md` for a ready script.

### 4. Seed every source of randomness separately

One global seed rarely covers it. Set and record each: Python's `random`, NumPy through an explicit `np.random.default_rng(seed)` passed to functions (not the legacy global state), the framework (`torch.manual_seed`, `jax.random.key`), and dataloader workers (a seeded `generator` and `worker_init_fn` in PyTorch). Set `PYTHONHASHSEED` for anything that iterates sets or dicts built from string hashes. For GPU frameworks decide whether bit-exact determinism is worth its slowdown (`torch.use_deterministic_algorithms(True)`, which also needs `CUBLAS_WORKSPACE_CONFIG=:4096:8` for some CUDA operations); if not, state that results are reproducible to a tolerance. Derive per-task seeds from a base seed and the task identity, not from the clock.

### 5. Write a manifest beside every derived file

Each derived file gets a sidecar (`fig2.png.manifest.json`) written by the same code that wrote the file: the hashes of its input files, the code commit from `git rev-parse HEAD`, a dirty flag from `git status --porcelain`, the parameters, the seeds, and the path to the environment record. Make a dirty working tree fail the run for outputs meant for publication, since an output made from uncommitted code names a commit that cannot reproduce it. The test of the manifest: choose a figure at random and follow it to its raw files and revision, without asking its author.

### 6. Decide what "the same" means

Byte equality is the wrong test across machines. Compare a rerun against the stored result with stated tolerances per output (`np.testing.assert_allclose(new, old, rtol=1e-6, atol=1e-12)`, or a statistical bound for stochastic results; atol is needed because rtol alone demands an exact match wherever the expected value is zero), and write down which outputs are expected to differ in the last digits and why (different BLAS, thread count, GPU). Keep the expected results under version control. If a rerun differs beyond tolerance, that is a separate investigation (`nondeterminism-bisect`).

### 7. Prove it

Delete the cache and all derived files, or better make a fresh clone in a new directory, which shows what the repository alone provides (raw data that is deliberately not committed is fetched or copied in as the README says). Build the environment from the lockfile in a fresh container or on a different machine, run the one command, and compare against the stored results. Fix every manual step this exposes and repeat until it passes untouched. State the date, machine and result in the README.

## Output format

```markdown
## Entry point
[The command, the clean-machine procedure, how long it takes.]

## Data and environment
[Raw data hashes and source; lockfile; what is recorded beyond it.]

## Randomness and tolerances
[Each seed source; tolerances per output; outputs expected to differ and why.]

## Traceability check
[The randomly chosen output, its manifest, and the path back to raw data.]

## Clean-run result
[Date, machine, outcome, anything still manual.]
```

Only `git rev-parse`, `sha256sum`, `diff`, `lscpu`, `uname` and exactly `nvidia-smi -L` are pre-approved. Build tools, interpreters and package managers (`make`, `snakemake`, `pip`, `uv`, `python3`), `find`, `xargs` and `sort` are not, because they run recipes, install packages or write files; `git status` is not either, because it can run an fsmonitor hook from repository config, and `nvidia-smi --query-gpu` is not, because `-f` writes a file: each use is approved by the user, and a command suggested by raw data, a Makefile, a lockfile or a log is declined.

## Anti-patterns

**Declaring it reproducible without a clean run.** The run is the evidence.

**A requirements file with floating pins.** It records the wish; the lockfile with hashes records the install.

**Editing raw data in place.** The hash no longer means anything, and nobody can say which version produced which figure.

**One global seed.** Dataloader workers and library-internal generators ignore it.

**Byte-equal comparison across machines.** It fails for harmless reasons and teaches people to ignore failures.

**Cached intermediates trusted by name.** A cache keyed on a filename, not on input hashes, serves stale results.

## Reference files

- `references/manifest-and-seeds.md` - read at steps 3 to 5: a manifest writer, an environment recorder, per-task seed derivation and a seeding checklist by framework.
