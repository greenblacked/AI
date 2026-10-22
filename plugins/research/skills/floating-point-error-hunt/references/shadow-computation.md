# Shadow computation

Contents: harness, stable rewrites, choosing the reference.

## Harness

Write the numeric function so it is generic over the number type, with every named intermediate recorded.

```python
import math
import mpmath

mpmath.mp.dps = 50


def compute(x, y, sqrt, record):
    a = x * x
    record("a", a)
    b = y * y
    record("b", b)
    d = a - b  # suspect: near-equal subtraction
    record("d", d)
    return sqrt(abs(d))


def run(x, y, kind):
    out = {}
    if kind == "hp":
        compute(mpmath.mpf(x), mpmath.mpf(y), mpmath.sqrt, out.__setitem__)
    else:
        compute(kind(x), kind(y), lambda v: v**0.5, out.__setitem__)
    return out


import numpy as np

x_low = np.float32(1.0000001)  # the input as the low-precision run sees it
low = run(float(x_low), 1.0, np.float32)
high = run(float(x_low), 1.0, "hp")  # same value, exactly, in the reference run
for k in high:
    ref, got = float(high[k]), float(low[k])
    rel = abs(got - ref) / abs(ref) if ref else abs(got)
    print(f"{k:4s} relative error {rel:.3e}")
```

Feed both runs the identical value, here the float32 input converted exactly to a double, otherwise the input conversion itself shows as error. Measure that representation error separately (compare the decimal literal with its float32 value): a subtraction of nearly equal numbers is exact in floating point when the operands are close enough, so a large error after it can be input representation amplified by conditioning, not the subtraction. The first intermediate whose relative error is orders of magnitude above machine epsilon is the target.

## Stable rewrites

| Unstable | Stable | Why |
| --- | --- | --- |
| `exp(x) - 1` | `expm1(x)` | avoids cancellation near zero |
| `log(1 + x)` | `log1p(x)` | same |
| `sqrt(x*x + y*y)` | `hypot(x, y)` | avoids overflow and underflow |
| `1 - cos(x)` | `2*sin(x/2)**2` | cancellation near zero |
| `(-b + sqrt(b*b - 4*a*c)) / (2*a)` | compute the larger-magnitude root, get the other as `c/(a*root)` | avoids subtracting close values |
| `log(sum(exp(v)))` | `logsumexp(v)` | avoids overflow |
| variance as `mean(x*x) - mean(x)**2` | Welford update or two-pass | the difference of two large close numbers |
| `a*b - c*d` | consider `math.fma` where available or an error-free transform | cancellation in the difference of products |

## Choosing the reference

Use an exact answer if one exists. Otherwise use a higher precision of the same algorithm, and check the reference itself by raising `mp.dps` and confirming the digits you rely on do not change. A reference computed with the same unstable formula in higher precision still shows where double precision loses digits, which is what the hunt needs.
