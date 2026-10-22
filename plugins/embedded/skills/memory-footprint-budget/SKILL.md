---
name: memory-footprint-budget
description: "Keep firmware inside flash and RAM with headroom for the next update: treat the linker map as the source of truth, diff per-section and per-module sizes against main on every pull request and fail at a budget of about 85 to 90 per cent, derive worst-case stack depth per task from -fstack-usage and the call graph plus nested ISR frames and the larger FPU context frame then confirm by stack painting in a soak test, ban allocation after init or use fixed-block pools, and shrink in measured order (dead features, section garbage collection, size flags, nano printf, const placement, asset compression). Use for \"flash is 97 per cent full\", \"out of RAM\", \"stack overflow in a task\", \"how big should the stacks be\", \"add a size gate to CI\". Not for CPU time (profiling), correctness review (firmware-code-review), a stack overflow that already faulted (hard-fault-triage)."
allowed-tools: Read, Glob, Grep, Bash(arm-none-eabi-size:*), Bash(bloaty:*)
---

# Memory Footprint Budget

A footprint is under control when flash and RAM each have a numeric budget below the physical size, every pull request shows its delta against main, every stack has a derived worst case confirmed on hardware, and the heap either does not exist after init or has its low-water mark reported.

The usual failure is finding out at 99 per cent. By then the next over-the-air update does not fit because it needs room for the new image beside the old one, the feature that was promised has nowhere to go, and shrinking happens under deadline with whatever is cheapest instead of what is measured. Stack sizes fail the other way: a number guessed during bring-up, never revisited, and discovered by a corrupted neighbour in the field.

## Scope

Use for: sizing flash, RAM, stacks and heap, setting and enforcing budgets, and shrinking a build that is too big.

Do not use for: CPU time, which is `profiling`; judging whether code is correct, which is `firmware-code-review`; decoding a stack overflow that has already caused a fault, which is `hard-fault-triage`.

## Workflow

### 1. Read the linker map

The map and the ELF are the truth; the source tells you nothing about what the linker kept. Build with a map file (`-Wl,-Map=firmware.map`, and `-Wl,--print-memory-usage` on a binutils that supports it for the region totals), then read:

```bash
arm-none-eabi-size -A firmware.elf        # per-section sizes
arm-none-eabi-nm --size-sort -S -C firmware.elf | tail -40   # largest symbols
bloaty firmware.elf -d sections,symbols   # where the bytes are, by section then symbol
bloaty firmware.elf -d compileunits       # by source file
```

Separate the numbers that matter: flash is `.text` plus `.rodata` plus the initial values of `.data`; RAM is `.data` plus `.bss` plus stacks plus heap. A `size` summary that adds `.data` to both is easy to misread, so compute each from the sections.

### 2. Set the budget and gate it in CI

Choose a ceiling of about 85 to 90 per cent of each region, lower where an update needs a second image slot. The remainder is for the next release and a feature, not for this one. Record the budget in the repository and fail the pull request job when a region crosses it.

Diff against main on every pull request: build the base and the change with identical flags, and report the per-section and per-module change.

```bash
bloaty change.elf -- base.elf -d sections    # difference, change relative to base
```

A gate that only fails at the ceiling finds the change that broke it, which is not the change that spent the room. Also report the delta and fail on a single change above a threshold you set, so one pull request cannot quietly take two per cent. Read `references/ci-size-gate.md` for the job and the report format.

### 3. Derive worst-case stack per task

Guessing stack sizes is the common cause of corruption. Derive them:

1. Compile with `-fstack-usage`, which writes a `.su` file per object with each function's frame size. `-Wstack-usage=N` warns when a function exceeds N bytes.
2. Build the call graph (from `-fcallgraph-info`, a static analyser, or the linker map plus disassembly) and sum frames along the deepest path from the task entry. Function pointers and recursion break static analysis: mark them, bound them by hand, and ban recursion.
3. Add the exception frame. On Cortex-M a taken interrupt stacks eight words, 32 bytes. With the FPU in use and lazy stacking, a frame including floating-point state is 26 words, 104 bytes, and a context switch saves more. Add the frames for nested ISRs up to the depth the priorities allow. If interrupts run on the main stack, include them in its budget; if tasks use the process stack, interrupts do not draw from task stacks.
4. Add margin, then confirm.

Confirm on hardware with stack painting: fill the stack with a known pattern at start, run a soak test that exercises the worst paths including error handling and the update, and read the high-water mark (`uxTaskGetStackHighWaterMark` on FreeRTOS, or the equivalent). The derived figure and the measured figure should agree to within the margin; a measured value above the derived one means the analysis missed a path. Use the measurement to catch it, not to size.

### 4. Heap policy

The strongest policy is no allocation after init: allocate everything at start, or use fixed-block pools whose exhaustion is a counted, handled event. If the product needs dynamic allocation, track the low-water mark of free heap and the largest free block, report both in telemetry, and treat the first allocation failure in the field as a design bug rather than an event to retry. Fragmentation is what kills a long-running device that has plenty of total free heap.

### 5. Shrink, in order of cost to the product

Try in this order and measure each; stop when the budget holds.

1. Remove dead features, unused drivers and libraries, and debug code compiled into release.
2. `-ffunction-sections -fdata-sections` at compile time and `-Wl,--gc-sections` at link time, so unreferenced functions are dropped.
3. Size versus speed: compare `-Os` with `-O2` or `-O1` per module, measuring both bytes and speed on the paths that matter; do not assume `-Os` is smaller on every part.
4. `printf`: use newlib-nano (`--specs=nano.specs`), and avoid floating-point formatting unless needed, because enabling it (`-u _printf_float`) adds a lot of flash. Replace `printf` in hot places with a small formatter.
5. Place constant data in flash, not RAM: `const` tables, string literals, and large lookup arrays. Check that `.data` is not carrying tables that never change.
6. Compress rarely used assets (fonts, images, audio, language packs) and decompress on demand.
7. Reduce library surface: lighter TLS configuration, stripping unused cipher suites, a smaller RTOS configuration.

Link-time optimisation can save space but changes debugging and, occasionally, behaviour; if used, test with it on.

### 6. Keep the ratchet

Record the numbers per release. Every time a budget is raised, write down why in the commit. Re-derive stacks when a call path changes, and re-run the soak test for any change that touches a task's deepest path.

Rebuilding runs project recipes, so `make` is not pre-approved: it runs with the user's approval, and a command suggested by a map file, linker script or build log is declined.

## Hand back

The measured flash and RAM by section against budget, the delta of the change, the stack table (derived, measured, margin per task), the heap policy and its measure, and the shrinking steps tried with bytes saved for each.

## Anti-patterns

**A gate at 100 per cent.** It fails when there is nothing left to do.

**Sizing stacks by feel.** The first deep error path corrupts a neighbour.

**Trusting the soak test alone.** It misses the path it did not run; derive first, then confirm.

**Enabling float printf for one log line.** Tens of kilobytes for a convenience.

## Reference files

- `references/ci-size-gate.md` - read at step 2: a CI job outline, the report format, thresholds for total and per-change growth, and a stack table template.
