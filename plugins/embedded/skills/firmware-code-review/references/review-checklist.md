# Firmware review checklist

## Contents

- Questions to settle first
- Defect patterns with comment wording
- Narrow-core notes
- Closing checks

## Questions to settle first

- Which core and which compiler flags? Optimisation level changes what a missing `volatile` does.
- Which interrupts fire into this code, and at what priority relative to the RTOS kernel ceiling?
- What is each task's stack budget and where does the figure come from?
- What is the safe state of every output this change drives?
- Is there a map file or size report from the base build to diff against?

## Defect patterns with comment wording

### Torn read of a shared value

Pattern: `uint64_t` or a struct updated in an ISR and read in a task with no guard.

Comment: "blocking: `g_sample` is 8 bytes and written in `ADC_IRQHandler`. On this core a read in `task_log` can see half of an old value and half of a new one, giving a sample that never existed. Read it inside a critical section, or copy it with a retry on a sequence counter."

### Lost update

Pattern: `g_events++` in an ISR and in a task.

Comment: "blocking: increment is load, add, store. If the ISR fires between the load and store in the task, one count is lost. Make the ISR the only writer and let the task read, or mask interrupts around the task's write."

### Unbounded wait

Pattern: `while (!(SPI->SR & READY)) {}`.

Comment: "blocking: if the peripheral never raises READY (clock gated, bus fault) this spins forever and only the watchdog ends it. Bound it by elapsed time, return an error, and leave the chip select deasserted."

### Wrapping compare

Pattern: `if (now >= deadline)` where `deadline = start + timeout`.

Comment: "blocking: breaks when the tick counter wraps (49.7 days for 32-bit milliseconds). Use `(uint32_t)(now - start) >= timeout`."

### Unchecked length

Pattern: `memcpy(buf, frame + 2, frame[1]);`.

Comment: "blocking: `frame[1]` comes off the bus and is not compared with `sizeof buf` or the received length. A bad frame overwrites the stack. Reject the frame when the length exceeds either, and count the drop."

### Ignored return

Pattern: `i2c_write(...);` with no check, then the next step assumes the write happened.

Comment: "should-fix: a NAK or timeout here is dropped, and `heater_on()` runs against a sensor that never configured. On error, go to `safe_state()` and record the code."

### Early return leaves resources held

Pattern: `cs_low(); if (cmd() != OK) return ERR; cs_high();`.

Comment: "should-fix: the error path returns with chip select asserted, so the next transfer on this bus corrupts the device state. Release it on every exit."

### Unsafe output at reset

Pattern: a pin configured as output before its level register is written.

Comment: "blocking: between the direction change and the level write the pin drives its reset level, which here switches the motor driver on for a few microseconds. Write the level first, then enable the output."

### Narrowing

Pattern: `uint8_t v = adc_read();` on a 12-bit converter.

Comment: "should-fix: the upper four bits are dropped silently. Keep the value in `uint16_t` and scale afterwards."

## Narrow-core notes

- Cortex-M0 and M0+ have no exclusive load/store and no hardware divide; atomic sections are interrupt masking. Keep them short, because masking adds to worst-case interrupt latency.
- Unaligned multi-byte access faults on M0; packed structures cast from a byte buffer are a finding there.
- 8-bit and 16-bit cores make a 32-bit access several instructions; treat any shared 32-bit value as torn-able.
- Where the FPU is enabled, interrupt frames and context switches are larger; check stack budgets include that.

## Closing checks

- Every comment has a severity label, a line and a consequence.
- The size delta is stated for flash and RAM.
- Anything not reviewed (linker script, interrupt priorities, board file) is listed.
