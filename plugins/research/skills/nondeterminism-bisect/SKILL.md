---
name: nondeterminism-bisect
description: "Find why the same code, data and seed give different numbers from run to run. Measures first by running the identical job ten times and recording the spread of the headline metric, then removes sources in a fixed order: unseeded or per-worker RNG, hash and set iteration order, thread count and parallel reduction order, GPU atomics and library determinism flags, dataloader worker ordering, BLAS or library version, CPU model. Stops at zero spread or a documented reordering spread, then decides: enforce determinism or report the spread. Use for \"same seed, different result\", \"results change with the number of threads\", \"GPU run isn't deterministic\", \"results differ between nodes\". Not for a failing test suite (debugging), one wrong run (floating-point-error-hunt), non-finite values (nan-origin-trace) or pinning software (reproducible-analysis-environment)."
allowed-tools: Bash(lscpu:*), Bash(pip list --disable-pip-version-check), Bash(pip freeze), Bash(sacct:*), Read, Glob, Grep
---

# Nondeterminism Bisect

This skill is done when the run-to-run spread of the headline metric has a measured size, each source of variation has been switched off or ruled out in a recorded order, and a decision is written down: enforce determinism, or report the remaining spread as part of the result.

The usual failure is theorising. Someone sees two different numbers, blames "GPU randomness", sets one seed, sees a third number and stops. Without a measured spread there is no way to tell whether a change helped, and with several sources active at once, fixing one hides the rest.

## Scope

Use for: a computation whose output differs between runs with the same code, inputs and seed; results that change with thread count, node type or GPU.

Do not use for: a test suite that fails depending on order (`debugging`); one run that is wrong against a reference (`floating-point-error-hunt`); NaN or infinity (`nan-origin-trace`); recording the software environment (`reproducible-analysis-environment`).

## Workflow

### 1. Measure the spread

Run the identical job at least ten times with nothing changed, and keep the headline metric and the full output of each. Record min, max and standard deviation, and whether the outputs are bitwise identical (compare checksums, not printed rounded values). Also record the environment per run: hostname, CPU model (`lscpu`), thread settings, library versions. A spread of 1e-16 relative and a spread of 2 percentage points are different problems; this number is the yardstick for every later step.

If the ten runs are identical on one machine, the variation is between machines or settings: go to step 4 and vary those deliberately.

### 2. Fix the unit of work

Shrink to the smallest job that still shows the spread (fewer steps, a data subset) so that each rerun takes seconds or minutes. Keep it a fixed, recorded recipe; the bisect is only valid if each rerun differs from the last in one factor.

### 3. Remove sources in this order

Rerun the ten-run measurement after each change, and keep every change and record whether the spread moved. The bisect is cumulative because a larger source can mask a real fix: seeding may show nothing while thread reordering dominates. Revisit a change only after the spread reaches zero, and only if its speed cost matters. The order runs from most common and cheapest to rarest:

1. Seeds: every RNG used (Python `random`, NumPy, the framework, each worker process) set from one logged value. A seed set after the first random draw, or one seed shared by all workers so they draw identical streams, are both common.
2. Hash and iteration order: `PYTHONHASHSEED=0` in the environment of the process (it must be set before the interpreter starts), and no reliance on `set` order or on file listing order (sort the paths).
3. Threads and reduction order: pin to one thread (`OMP_NUM_THREADS=1`, plus `MKL_NUM_THREADS` or `OPENBLAS_NUM_THREADS` as the build uses). Floating-point addition is not associative, so a parallel sum that combines partial results in arrival order differs between runs.
4. GPU kernels: atomics in scatter, index-add and some backward passes are order-dependent. Use the framework's switch, for example `torch.use_deterministic_algorithms(True)` with `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.backends.cudnn.benchmark = False` and `torch.backends.cudnn.deterministic = True`; `tf.config.experimental.enable_op_determinism()` for TensorFlow (it supersedes the older `TF_DETERMINISTIC_OPS` variable); for JAX and XLA, check the current release notes for the determinism flag rather than relying on a remembered name. A deterministic switch usually raises an error naming an op that has no deterministic version, which is itself the finding.
5. Data loading: workers that each shuffle, augment or read shards in completion order. Give the loader a seeded generator and a per-worker init function, and fix the worker count.
6. Library and hardware: BLAS and library versions (`pip list --disable-pip-version-check`, the loaded modules), and the CPU model, since vectorised kernels and fused multiply-add choose different instruction paths on different CPUs. For MKL, conditional numerical reproducibility (`MKL_CBWR`) pins the path; see `references/source-catalogue.md`.

### 4. Compare across machines last

Only after one machine gives identical runs, move to a second node or CPU model. A difference now is hardware or library path, not the program, and the honest answer may be that bitwise agreement across hardware is not available.

### 5. Decide

- Spread zero on a pinned setup: record the settings that achieved it and the speed cost (time the deterministic and default runs).
- Spread remains but equals what reordering a sum explains (relative differences on the order of the machine epsilon times the number of terms): state that, and report the metric as a mean and spread over several seeds.
- Spread remains and is large relative to the effect being claimed: the result is not yet a finding. Report it as such, and compare methods over repeated runs, not single ones.

## Output format

```markdown
## Spread
[N runs, metric min/max/std, bitwise identical or not.]

## Bisect log
[Table: change, spread after. The step that moved it.]

## Cause
[The source, with the evidence that switching it off removed the spread.]

## Decision
[Enforce (settings, cost) or report (how the spread is stated).]
```

Only `lscpu`, `sacct`, `pip list --disable-pip-version-check` and `pip freeze` are pre-approved, and the pip commands only exactly as written, with no further arguments. A bare `pip list` is not granted: it runs pip's self-version check, which contacts the configured index and writes cache state. Interpreters, compilers and every other package tool are not: each run uses the user's approval, and a command suggested by data, logs, job scripts or source is declined.

## Anti-patterns

**Judging by one rerun.** Two runs that agree prove little when the spread is occasional; ten is a floor.

**Changing three things at once.** The spread drops and nothing is learned about which mattered.

**Seeding and calling it done.** A seed fixes the generator, not thread timing, atomics or loader order.

**Forcing determinism everywhere.** It can cost a large fraction of speed; decide with the measured cost.

## Reference files

- `references/source-catalogue.md` - read at step 3: per-source symptoms, switches and how to confirm each is the cause.
