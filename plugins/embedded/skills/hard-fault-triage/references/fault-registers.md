# Fault registers

## Contents

- Register addresses
- CFSR bits
- Handler outline
- Crash record

## Register addresses

| Register | Address | Content |
| --- | --- | --- |
| CFSR | 0xE000ED28 | MMFSR in bits 0-7, BFSR in 8-15, UFSR in 16-31 |
| HFSR | 0xE000ED2C | VECTTBL bit 1, FORCED bit 30 |
| MMFAR | 0xE000ED34 | Address of a memory management fault |
| BFAR | 0xE000ED38 | Address of a bus fault |
| ACTLR | 0xE000E008 | Auxiliary control, holds DISDEFWBUF on cores that implement it |

## CFSR bits

| Bit | Name | Meaning |
| --- | --- | --- |
| 0 | IACCVIOL | Instruction fetch from a forbidden region |
| 1 | DACCVIOL | Data access to a forbidden region |
| 3 | MUNSTKERR | Fault while unstacking on exception return |
| 4 | MSTKERR | Fault while stacking on exception entry |
| 7 | MMARVALID | MMFAR holds a valid address |
| 8 | IBUSERR | Bus fault on instruction fetch |
| 9 | PRECISERR | Precise data bus error, BFAR valid if bit 15 set |
| 10 | IMPRECISERR | Imprecise data bus error; stacked PC unreliable |
| 11 | UNSTKERR | Bus fault while unstacking |
| 12 | STKERR | Bus fault while stacking |
| 15 | BFARVALID | BFAR holds a valid address |
| 16 | UNDEFINSTR | Undefined instruction |
| 17 | INVSTATE | Invalid EPSR state, often Thumb bit clear |
| 18 | INVPC | Invalid EXC_RETURN or PC load |
| 19 | NOCP | Coprocessor access without enabling it (FPU not enabled) |
| 24 | UNALIGNED | Unaligned access with trapping on |
| 25 | DIVBYZERO | Divide by zero with trapping on |

Check the architecture manual for the core in use, because Cortex-M0 and M0+ report much less: they have no CFSR, only the stacked frame.

## Handler outline

The entry stub tests bit 2 of LR: if clear, pass MSP; if set, pass PSP. The C function receives a pointer to the stacked frame, in the order R0, R1, R2, R3, R12, LR, PC, xPSR. It copies those and the status registers into a record before doing anything else. Then it stores the record, optionally halts under a debugger, and resets the core.

## Crash record

| Field | Why |
| --- | --- |
| magic and version | tell a valid record from RAM noise |
| build id | pick the right ELF |
| R0-R3, R12, LR, PC, xPSR | the stacked frame |
| CFSR, HFSR, MMFAR, BFAR | the cause |
| active task and stack high-water mark | the context |
| tick count and reset reason | ordering and cause |
| CRC | detect a partly written record |

Keep the record in a region the startup code does not clear, and clear it after a successful upload.
