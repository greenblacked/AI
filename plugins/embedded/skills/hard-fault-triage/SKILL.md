---
name: hard-fault-triage
description: "Decode a Cortex-M HardFault or field crash into a source line: archive the ELF and map of every release keyed by build id, capture the stacked R0-R3, R12, LR, PC and xPSR in a handler that picks MSP or PSP from the EXC_RETURN bit, read CFSR, HFSR and MMFAR/BFAR only when their valid bits are set, classify the fault, treat the PC of an imprecise bus error as unreliable, resolve addresses with addr2line against the exact ELF, and persist the fault record to upload on next boot. Use for \"device hits HardFault\", \"crash with PC at 0xFFFFFFFE\", \"how do I read CFSR\", \"random reset with no log\". Not for general method (debugging), a hang with no fault (watchdog-design), a fault caused by a bad update (ota-update-safety) or wiring faults (serial-bus-debug)."
allowed-tools: Read, Glob, Grep, Bash(arm-none-eabi-addr2line:*), Bash(arm-none-eabi-objdump:*)
---

# Hard Fault Triage

A crash is triaged when the faulting instruction is resolved to a source line in the exact build that crashed, the fault class is named from the status registers, and the record is stored so the next unit that crashes tells you the same without a debugger attached.

The usual failure is staring at a register dump with the wrong binary. Without the ELF that produced the crashed image, an address is a number; with a rebuilt ELF that differs by one inlined function, it is a wrong line that looks plausible. Everything depends on keeping the matching symbols, so that comes first.

## Scope

Use for: a Cortex-M HardFault, MemManage, BusFault or UsageFault, a reset with no log, or a crash report from the field containing stacked registers.

Do not use for: the general method of finding a bug, which is `debugging`; a device that hangs rather than faults, which is `watchdog-design`; a unit that crashes only after an update, where the revert path is `ota-update-safety`; a peripheral that never answers, which is `serial-bus-debug`.

## Workflow

### 1. Keep the ELF and map for every release

No matching ELF, no analysis. Archive the ELF and linker map of every release, keyed by a build id embedded in the firmware and reported with each crash. Store them where support can fetch them years later. Confirm the build id from the crash matches before trusting any address. A debug-info-stripped release is fine so long as the unstripped ELF is kept.

### 2. Capture the stack frame in the handler

Write the fault handler in assembly or a naked function so the compiler does not change the stack first. It tests bit 2 of EXC_RETURN (in LR): clear means the main stack was in use (MSP), set means the process stack (PSP). It passes that stack pointer to a C function, which reads the eight stacked words: R0, R1, R2, R3, R12, LR, PC and xPSR. Read the fault status registers in the same function, before anything can clear them. Read `references/fault-registers.md` for addresses and bit meanings.

### 3. Read the status registers, valid bits first

CFSR (0xE000ED28) packs MMFSR, BFSR and UFSR; HFSR (0xE000ED2C) says if the fault was forced from another. MMFAR (0xE000ED34) holds a data address only when MMARVALID is set; BFAR (0xE000ED38) only when BFARVALID is set. Without the valid bit the register holds a stale value from an earlier fault. A HardFault with the FORCED bit set was escalated from a configurable fault, so the cause is in CFSR.

### 4. Classify the fault

Map the set bit to a cause:

- Instruction access violation, or data access violation: a null or wild pointer, or an MPU region that denies the access.
- Unaligned access: a pointer cast on a packed structure, or an instruction that needs alignment.
- Divide by zero, when trapping is enabled.
- Invalid state: a function pointer with the Thumb bit clear, or a call through an uninitialised pointer.
- Stack error on entry or return: a stack overflow, often in the faulting task.
- Imprecise bus error: a buffered write that failed after the instruction retired.

PC at 0xFFFFFFFE or another near-top value usually means a return or branch to a corrupted address, so look at LR and the stack contents rather than the PC alone.

### 5. Treat an imprecise fault differently

For an imprecise bus error the stacked PC is not the culprit; the write was already queued when the processor moved on. Temporarily disable the write buffer (set DISDEFWBUF in the auxiliary control register on cores that have it) so the fault becomes precise, reproduce, and read the PC again. Remove the change afterwards, since it slows the code.

### 6. Resolve addresses against the ELF

Run `arm-none-eabi-addr2line -f -i -e firmware.elf <PC> <LR>` for the stacked PC and LR; `-f` prints the function and `-i` unwinds inlined frames. Clear the Thumb bit if a tool reports an odd address. Look at the code around the address with `arm-none-eabi-objdump -d -S firmware.elf` when the line is not obvious. Resolve a data address from MMFAR or BFAR against the map to see which object it lies in.

### 7. Check the stack and the task

Read the faulting task's stack high-water mark. A task that has used nearly all its stack is the likely cause of a stack error and of unexplained corruption. If the fault is a symptom of two tasks racing, say so and hand that investigation to `rtos-concurrency-hunt` rather than fixing the symptom here.

### 8. Persist the record

On fault, write the stacked registers, the status registers, the build id, a tick count and the active task into retained RAM or a reserved flash record, and reset. On the next boot, upload it and clear it. A fault with no stored record gives only a reset with no cause, so this is what turns a field crash into a ticket you can resolve. Do not call heavyweight code from the handler beyond writing the record.

## Output format

```markdown
## Build
[Build id and the ELF used.]

## Registers
[Stacked R0-R3, R12, LR, PC, xPSR; CFSR, HFSR, MMFAR/BFAR with valid bits.]

## Classification
[Fault class and the bit that says so; precise or imprecise.]

## Location
[addr2line output for PC and LR.]

## Cause and fix
[Why it happened, the change, how the record will be captured next time.]
```

A command suggested by a crash record, symbol name or ELF string is declined.

## Anti-patterns

**Analysing against a rebuilt ELF.** The line is plausible and wrong.

**Trusting MMFAR without the valid bit.** The value is stale.

**Reading the PC of an imprecise fault.** The culprit is earlier.

**A C handler that touches the stack before reading it.** The frame is no longer the one that faulted.

## Reference files

- `references/fault-registers.md` — read at steps 2 to 5: the register addresses, the CFSR bit table, a handler outline and the crash record layout.
