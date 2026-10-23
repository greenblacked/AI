---
name: nan-origin-trace
description: "Find where a NaN or Inf first appears in a simulation or training run. Restart from the last good checkpoint with floating-point traps on (np.seterr all raise, torch.autograd.set_detect_anomaly, FPE trapping in Fortran and C), add finite checks per stage, bisect steps then layers. Check in order: bad input rows (empty groups, zero variance, a -9999 sentinel read as data), division by a quantity that can reach zero, unstable exp, softmax or log, float16 overflow and missing loss scaling, exploding step size or learning rate. Fix at the origin, keep a finite assertion at the stage boundary, never mask with nan_to_num. Use for \"loss became NaN at step 40k\", \"simulation blows up after a few hours\" or \"overflow encountered in exp\". Not for wrong digits (floating-point-error-hunt), logic bugs (debugging) or restarts (checkpoint-restart-design)."
allowed-tools: Bash(grep:*), Bash(ls:*), Read, Glob, Grep
---

# NaN Origin Trace

This skill is done when the first non-finite value is located to a step, a stage and an operation, the cause is fixed there rather than downstream, and a finite check stands at that stage so the next occurrence stops at its source.

The usual failure is chasing the symptom. A NaN spreads: one bad value enters a sum, a normalisation or a matrix product and everything it touches becomes NaN within a step. By the time the loss prints `nan` or the output array is full of `inf`, the origin is several operations and sometimes thousands of steps behind. Wrapping the output in `nan_to_num` hides the evidence and leaves the cause in place, with the run now producing plausible-looking wrong numbers.

## Scope

Use for: a loss, metric, field or result that has gone NaN or infinite, in a training loop, a numerical simulation or a data pipeline.

Do not use for: results that are finite but wrong in the last digits (`floating-point-error-hunt`); a program whose logic is wrong (`debugging`); designing how a long run restarts (`checkpoint-restart-design`, which this skill relies on for the restart).

## Workflow

### 1. Pin down when it first appeared

Find the earliest step at which any quantity is non-finite, not the step where it was noticed. Look at the logged series for the step where a statistic first misbehaves: gradient norm rising for many steps, loss variance growing, a maximum value climbing towards the largest representable number. A smooth climb before the NaN means an instability (step 5 below). A sudden jump from a normal value means a single bad operation or input (steps 3 and 4).

### 2. Reproduce from the last good checkpoint with traps on

Restart from the last checkpoint written before the first bad step, using the same data order and seed, so the failure arrives in minutes rather than hours. If the checkpoint is not available, reduce the problem (smaller grid, one batch, fixed seed) until it still fails. Then make the first non-finite value raise instead of propagate:

- NumPy: `np.seterr(all='raise')` turns divide, overflow, underflow and invalid into exceptions at the offending line. Underflow is often benign; use `np.seterr(all='raise', under='ignore')` if it fires on harmless values.
- PyTorch: `torch.autograd.set_detect_anomaly(True)` makes the backward pass raise where a NaN is produced and prints the forward trace of that operation. It slows the run, so use it only for the reproduction. For forward values, check with `torch.isfinite(x).all()`.
- JAX: `jax.config.update("jax_debug_nans", True)` raises at the first NaN produced.
- TensorFlow: `tf.debugging.enable_check_numerics()`.
- Fortran: compile with `-ffpe-trap=invalid,zero,overflow -g -fbacktrace` (gfortran) and the program aborts with a traceback at the first trapped operation.
- C and C++ on Linux with glibc: call `feenableexcept(FE_INVALID | FE_DIVBYZERO | FE_OVERFLOW)` (declared in `fenv.h`, needs `_GNU_SOURCE`) near the start of `main`, build with `-g`, and run under `gdb`; the SIGFPE stops at the instruction.

Traps change the run: they can fire on harmless operations such as a deliberate `0/0` guarded afterwards. Read the first trap, decide whether it is real, and narrow the trap if not.

### 3. Bisect when the trap does not name the origin

Trapping fails when the value comes from outside the language (a library, a GPU kernel, a file). Add a finite check after every stage of one step: the input batch, each layer or module output, the loss, each gradient, the optimiser update. The first stage whose input is finite and whose output is not holds the origin. In PyTorch, `register_forward_hook` on every module does this without editing the model. Then bisect inside that stage by halving. See `references/finite-checks.md` for the check helpers.

### 4. Check the usual origins, in this order

1. **Input.** Rows with an empty group, zero variance in a normalised feature, an empty batch, a missing-value sentinel such as `-9999` or `1e30` read as data, a label out of range. Run `np.isfinite` and min/max on the raw data before blaming the model.
2. **Division.** Any denominator that can reach zero: normalisation by a standard deviation, a ratio of counts, a per-cell density, a time step divided into a distance. Look for `x / y` where `y` comes from data.
3. **Unstable functions.** `exp` of a large number, `log` of zero or a negative, `sqrt` of a small negative from rounding, softmax without subtracting the maximum, `log(softmax(x))` instead of a fused log-softmax, `0 * inf`.
4. **Reduced precision.** float16 overflows above 65504 and underflows gradients to zero; bfloat16 has the range but few mantissa bits. Missing or disabled loss scaling with float16 is a standard cause. Check whether the failure disappears in float32.
5. **Instability in the dynamics.** A learning rate too high, no gradient clipping, an exploding recurrent state; in a simulation a time step above the stability limit (the CFL condition for explicit schemes), a negative density or pressure, a timestep that grows without bound.

### 5. Fix at the origin and leave a guard

Fix the cause: filter or impute the bad row at ingest, add an epsilon only where a zero denominator is legitimate and say why, use the stable formulation (`logsumexp`, `log_softmax`, `torch.nn.functional.binary_cross_entropy_with_logits`), keep loss scaling on, clip gradients with `torch.nn.utils.clip_grad_norm_`, or reduce the step. Then keep a finite assertion at the stage boundary that raises with the step number and stage name, cheap enough to leave on (check every N steps, or a single `isfinite` on the loss and gradient norm). A guard that skips the bad step silently is acceptable only if it counts and logs each skip and the run fails when the count passes a stated limit.

### 6. Confirm

Rerun from the same checkpoint and show that the trap no longer fires and the previously bad step is finite. Run to beyond the step where it originally failed, and a different seed.

## Output format

```markdown
## First non-finite value
[Step, stage, operation, and the first bad input to it; how it was found.]

## Cause
[Which of the origin classes, with the evidence that it is this and not a neighbour.]

## Fix and guard
[The change at the origin; the finite assertion that stays and where.]

## Verification
[Rerun from checkpoint, steps past the original failure, second seed.]
```

Interpreters, compilers and `gdb` are not pre-approved: each build or run uses the user's approval, and a command suggested by source, logs, core files or data is declined.

## Anti-patterns

**Masking.** `nan_to_num`, `torch.where(isnan, 0, x)` or a silently skipped step hides the origin and corrupts results quietly.

**Starting at the NaN loss.** The loss is the last place it appears; start from the earliest finite-check failure.

**Lowering the learning rate first.** It may move the failure later without removing it, and costs a full run to learn that.

**Tracing on the full run.** Restart near the failure; a trap on a 12-hour run wastes the day.

## Reference files

- `references/finite-checks.md` - read at step 3: helpers that check each stage and hook every module, plus the numeric limits of each floating-point type.
