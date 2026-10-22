# Finite checks

Contents: stage check, module hooks, range limits, simulation checks.

## A stage check that names where it failed

```python
import numpy as np


def assert_finite(name, x, step):
    a = np.asarray(x)
    if not np.isfinite(a).all():
        bad = ~np.isfinite(a)
        raise FloatingPointError(
            f"step {step}: {name} has {bad.sum()} non-finite of {a.size}; "
            f"first index {tuple(np.argwhere(bad)[0])}; "
            f"finite min/max {np.nanmin(a[~bad]) if (~bad).any() else None}/"
            f"{np.nanmax(a[~bad]) if (~bad).any() else None}"
        )
```

Print the finite min and max of the failing array: a maximum near 1e38 (float32) or 6.5e4 (float16) shows an overflow in progress, while ordinary values with a lone NaN point at a bad input or a `0/0`.

## Hooking every module in PyTorch

```python
import torch


def add_finite_hooks(model):
    def make(name):
        def hook(module, inputs, output):
            for i in inputs:
                if torch.is_tensor(i) and not torch.isfinite(i).all():
                    raise FloatingPointError(
                        f"input already non-finite at {name}; "
                        "look at the ops between the previous module and this one"
                    )
            outs = output if isinstance(output, (tuple, list)) else (output,)
            for o in outs:
                if torch.is_tensor(o) and not torch.isfinite(o).all():
                    raise FloatingPointError(f"non-finite output from {name}")

        return hook

    return [m.register_forward_hook(make(name)) for name, m in model.named_modules()]
```

The first module to raise an "output" error has finite inputs and a non-finite output. An "input already non-finite" error means a functional op between modules (a `torch.log` or a division in a parent's `forward`) made the NaN, so look there. For the backward pass use `register_full_backward_hook` or `torch.autograd.set_detect_anomaly(True)`. Keep the returned handles and call `.remove()` on each after the diagnosis: they synchronise the device on every call.

## Range limits

| Type | Largest finite | Smallest normal | Notes |
| --- | --- | --- | --- |
| float16 | 65504 | about 6.1e-5 | Needs loss scaling for gradients |
| bfloat16 | about 3.4e38 | about 1.2e-38 | Same range as float32, about 3 decimal digits |
| float32 | about 3.4e38 | about 1.2e-38 | `exp(x)` overflows near x = 88.7 |
| float64 | about 1.8e308 | about 2.2e-308 | `exp(x)` overflows near x = 709.8 |

Use `np.finfo(np.float32)` and `torch.finfo(torch.float16)` to read the limits rather than trusting memory.

## Simulation checks

- Track conserved or bounded quantities per step (total mass, energy, minimum density, maximum speed). A quantity that drifts or grows exponentially before the NaN identifies an instability, and the step at which growth began is the step to examine.
- For explicit schemes, compute the stability limit for the current fields and compare it to the step actually taken, in case an adaptive step controller or a changed grid has pushed it over.
- Compare the first bad cell's neighbours: a NaN born at a boundary or at a cell with zero volume or zero density points at geometry or initial conditions, not the solver.
- Read the first bad value's index and map it to the physical location before looking at code.
