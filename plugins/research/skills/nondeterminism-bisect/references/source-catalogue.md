# Source catalogue

Contents: signatures of each source, switches, how to confirm, a bisect log template.

## Signatures

| Source | Typical signature | How to confirm |
| --- | --- | --- |
| Unseeded RNG | Large, irregular spread; differs from the first step | Log the first random draw of each run; if it differs, seeding is the cause |
| Shared seed in workers | Duplicated augmentations or samples; correlated results | Print the first draw from each worker; identical values mean a shared stream |
| Hash order | Differs only between interpreter launches, not within one | Run twice with `PYTHONHASHSEED=0`; spread vanishing confirms it |
| Thread count | Same result at N threads, different at M | Run at 1, 2 and 4 threads and plot the metric against threads |
| Parallel reduction | Tiny relative differences (near machine epsilon) that grow through iteration | Single thread removes it; difference shrinks with float64 |
| GPU atomics | Run-to-run differences on GPU only, none on CPU | Deterministic-algorithms switch removes it or raises naming the op |
| Autotuning | Differs between first and later launches, or between GPUs | Disable benchmark or autotune modes and compare |
| Loader order | Differs in the order samples are consumed | Log sample indices per step and diff them across runs |
| Library version | Differs across environments with the same inputs | Diff `pip freeze` or the module list; rerun in one frozen environment |
| CPU model | Differs only between node types | Compare `lscpu` model lines of the differing runs; pin the code path |

## Chaotic amplification

A tiny difference (one unit in the last place) in a chaotic or long iterative system, such as training with many steps or a dynamical simulation, grows until final values differ by far more than any single rounding. The cause is still the reordering; the size of the final spread tells you about the system, not about the size of the bug. Measure the spread at an early step too: if early steps agree to many digits and later ones do not, amplification is the story.

## Bisect log template

```markdown
| # | Change from previous | N runs | Metric min | Metric max | Bitwise equal |
| --- | --- | --- | --- | --- | --- |
| 0 | baseline | 10 | | | |
| 1 | single seed logged and set before first draw | 10 | | | |
```

## MKL and BLAS notes

Intel MKL offers conditional numerical reproducibility through the `MKL_CBWR` environment variable, which fixes the code path so results agree across CPU models at some speed cost. OpenBLAS and other builds have their own thread and kernel selection variables; read the build's documentation before relying on a name. NumPy reports what it was built against through `numpy.show_config()`.
