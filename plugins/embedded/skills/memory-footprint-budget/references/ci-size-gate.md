# CI size gate

## Contents

- Job outline
- Report format
- Thresholds
- Stack table template
- Reading a regression

## Job outline

1. Build the base revision (the target branch) and the change with the same toolchain version and flags. A different compiler version moves sizes by more than most changes do, so pin it.
2. Keep each ELF and map as build artefacts.
3. Extract region totals (flash and RAM) from sections, not from a combined summary:
   - Flash: `.text` + `.rodata` + `.data` load image (and any `.ARM.exidx` or vector table sections your linker script places in flash).
   - RAM: `.data` + `.bss` + reserved stacks + heap region.
4. Run the diff: `bloaty change.elf -- base.elf -d sections` for the section view and `-d compileunits` for the module view.
5. Compare with the committed budget and fail on a breach.
6. Post the report as a comment or job summary.

## Report format

```text
Flash   412,160 / 524,288 (78.6%)   budget 85%   +1,204 vs main
RAM      61,440 / 98,304  (62.5%)   budget 85%     +64 vs main
Largest growth by module:
  drivers/uart.c      +880
  net/mqtt_client.c   +240
```

State both the absolute use and the percentage, because a percentage alone hides which region grew.

## Thresholds

| Gate | Suggested rule | Reason |
| --- | --- | --- |
| Region ceiling | Fail above 85 to 90 per cent | Leaves room for the next update and a feature |
| Single-change growth | Fail above a fixed byte count, for example 2 per cent of the region | Stops one pull request spending the headroom |
| OTA slot | Image size plus margin must fit the smaller slot | An image that does not fit cannot be delivered |
| Override | Allowed with a stated reason in the commit | Keeps the gate honest without blocking real needs |

Choose the figures for the product and write them next to the budget file.

## Stack table template

| Task | Deepest path | Frames summed (bytes) | ISR allowance | Margin | Allocated | Painted high-water | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| net | recv, parse, tls | derived | nested ISR frames plus FPU frame if used | chosen | set | measured in soak | ok or revise |

A row is revised when the measured figure exceeds the derived one, which means the analysis missed a path, or when the margin falls below the chosen floor.

## Reading a regression

- Large growth in `.rodata` after a library update: look for new tables or strings.
- Growth in `.bss` with no new feature: a buffer size constant changed, or a per-instance buffer was multiplied.
- Growth in `.text` of a few kilobytes at once: a new library pulled in a formatter, a math routine or a soft-float path.
- No growth in sections but a failing link: the region definition in the linker script changed.
