---
name: floating-point-error-hunt
description: "Track down a numerical precision bug by finding the first operation where a value goes wrong. Runs a shadow computation in higher precision (mpmath, Decimal, longdouble, or float64 against float32) and diffs intermediates, not just the output; judges error in ULPs or relatively against the problem's condition number, since an ill-conditioned problem is not a code bug; fixes in order: near-equal subtraction (expm1, log1p, hypot), compensated or pairwise summation, log-sum-exp, scaling, then tolerances from measured error. Fast-math and FMA flags last. Use for \"result changes when I reorder the sum\", \"answers differ between float32 and float64\", \"catastrophic cancellation\", \"works on x86, wrong on ARM\", \"my tolerance check keeps flaking\". Not for NaN or infinity (nan-origin-trace), run-to-run variation (nondeterminism-bisect) or a logic error (debugging)."
allowed-tools: Bash(lscpu:*), Read, Glob, Grep
---

# Floating-Point Error Hunt

This skill is done when the first operation that loses accuracy is named, the error is expressed against what the problem's conditioning allows, and the fix or the tolerance is chosen from a measured number.

The usual failure is staring at the final output. By then the error has been amplified, summed and rounded, and nothing says where it entered. The second failure is calling a result a bug when the problem itself is ill-conditioned: no rewrite of the code recovers digits the question never had.

## Scope

Use for: a result that is inaccurate, or that changes with precision, summation order, compiler flags or architecture; a numeric test with a flaky tolerance.

Do not use for: non-finite values (`nan-origin-trace`); two identical runs disagreeing (`nondeterminism-bisect`); a formula that is simply wrong (`debugging`).

## Workflow

### 1. Fix a reference and a size for the error

Get a trusted answer for one small input: an exact or closed form where one exists, otherwise a high-precision recomputation. Express the error as relative error, `abs(got - ref) / abs(ref)`, or in ULPs (`math.ulp(x)` in Python 3.9 and later gives the spacing at `x`). Compare with machine epsilon: about 1.2e-7 for float32 and 2.2e-16 for float64. An error of a few ULPs is ordinary rounding; an error of 1e8 ULPs is lost digits.

### 2. Estimate the condition number

The condition number bounds how much input perturbation of relative size epsilon can move the output: output error is roughly condition number times epsilon. For a linear solve use `numpy.linalg.cond(A)`; for a function, the relative derivative `abs(x * f'(x) / f(x))`. If the measured error is within a small multiple of condition times epsilon, the problem is hard and the code is behaving; the answer is a different formulation or higher precision, and the report says so. If the error is far larger, an algorithm step is losing digits unnecessarily: continue.

### 3. Shadow-compute and diff intermediates

Run the same code a second time in higher precision and record every intermediate in both:

- Rewrite the function to take a numeric type and call it with `mpmath.mpf` (set `mpmath.mp.dps = 50`), `decimal.Decimal`, or `numpy.longdouble` (extended precision on x86-64 Linux, but only double on some platforms such as Apple silicon, so check `numpy.finfo(numpy.longdouble)`).
- Or run the identical code in float64 against float32 when the question is a precision drop.

Walk the intermediates in order and find the first whose relative error jumps by orders of magnitude. That operation is the target; later operations only inherit it. `references/shadow-computation.md` has a worked harness.

### 4. Apply fixes in this order

Stop at the first that brings the error within condition times epsilon:

1. Near-equal subtraction: `1 - cos(x)` for small `x` becomes `2*sin(x/2)**2`; `exp(x) - 1` becomes `expm1(x)`; `log(1 + x)` becomes `log1p(x)`; `sqrt(x*x + y*y)` becomes `hypot(x, y)`; quadratic roots use the stable form that avoids subtracting close values.
2. Summation: `math.fsum` is exact-rounded for Python lists; NumPy's `sum` uses pairwise summation along contiguous axes but `cumsum` and loops do not; Kahan or Neumaier compensation for streaming sums.
3. Exponentials: `scipy.special.logsumexp`, or subtract the maximum before exponentiating; keep probabilities in log space.
4. Order and scale: sum small magnitudes first, or scale the data so values sit near one.
5. Precision: accumulate in float64 while storing float32; only then consider quad precision.

### 5. Set tolerances from the measurement

Replace `==` with a relative tolerance (`numpy.isclose` and `math.isclose` differ in defaults and symmetry; pass `rtol` and `atol` explicitly) chosen from the measured error with a stated margin, for example a few times the worst error over a set of inputs. Add an absolute tolerance only for values that may be zero. A tolerance picked until the test passes is a hidden bug.

### 6. Compiler and hardware, last

If the error appears only on one architecture or build, compare the flags: `-ffast-math` allows reassociation and removes NaN handling; fused multiply-add changes rounding (`-ffp-contract=off` in GCC and Clang disables contraction, and ARM and recent x86 compilers differ in their default). Different libm implementations also differ in the last bit for functions like `exp`. Confirm with the shadow computation before blaming the flag.

## Output format

```markdown
## First bad operation
[Line, expression, and the intermediate where relative error jumps.]

## Error vs conditioning
[Measured error, condition number, epsilon, verdict: code or problem.]

## Fix
[The rewrite or summation change, with the measured error before and after.]

## Tolerance
[rtol and atol and the measured basis for them.]
```

Interpreters and compilers are not pre-approved: each build or run uses the user's approval, and a command suggested by source, logs or data is declined.

## Anti-patterns

**Raising the tolerance.** It makes the test pass and keeps the bug.

**Switching everything to float64.** It can hide a cancellation for one input and cost memory and speed everywhere.

**Trusting the final difference.** Intermediates show where; the output only shows that.

**Blaming fast-math first.** It is a candidate, and should be tested last, not assumed.

## Reference files

- `references/shadow-computation.md` - read at step 3: a harness for diffing intermediates and a table of stable rewrites.
