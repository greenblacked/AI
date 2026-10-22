# Reading sanitizer reports

Read this when a report does not fit the order in the skill, or the error type is unfamiliar.

## AddressSanitizer

| First line | Usual cause | Look at |
| --- | --- | --- |
| `heap-use-after-free` | A pointer, reference or iterator outlived the object | The freed-by stack: who released it, and which owner did not know |
| `heap-buffer-overflow` | An index or length exceeded the allocation | Where the length was computed, and the allocation stack for the real size |
| `stack-buffer-overflow` | A local array indexed out of range | The frame named in the report, and the variable it points at |
| `stack-use-after-scope` | A pointer to a block-local variable used after the block ended | The scope the variable lives in |
| `stack-use-after-return` | A pointer to a local escaped the function; needs `detect_stack_use_after_return=1` | What stored the pointer |
| `global-buffer-overflow` | A static or global array overrun | The symbol named in the report |
| `attempting double-free` | Two owners released the same pointer | The first free stack and the second |
| `alloc-dealloc-mismatch` | `new[]` released with `delete`, or `malloc` with `delete` | Allocation and release sites |
| `detected memory leaks` (LeakSanitizer) | Allocation never released at exit | The allocation stack; direct leaks before indirect |

In every memory report the three stacks are: where the bad access happened, where the memory was released (if it was), and where it was allocated. The cause is the relationship between the last two.

## UndefinedBehaviorSanitizer

Each finding reads `file:line: runtime error: <what>`. With `print_stacktrace=1` you also get the call path. Common ones: `signed integer overflow`, `shift exponent N is too large`, `null pointer passed as argument N, which is declared to never be null`, `load of misaligned address`, `member call on null pointer`, `index N out of bounds`. A finding in a hash or checksum routine on unsigned arithmetic is not reported by `-fsanitize=undefined`, since unsigned wraparound is defined behaviour; only Clang's `-fsanitize=integer` (`unsigned-integer-overflow`) reports it, and there findings in hash code are expected. Signed overflow is a bug. Treat `-fsanitize=undefined` findings as bugs even when the program appears to work, since another compiler version may act on the assumption.

## ThreadSanitizer

A `WARNING: ThreadSanitizer: data race` shows two accesses, at least one a write, with no happens-before edge between them, each with its thread and stack, plus where each thread was created. Fix by guarding the shared variable with one mutex used on both sides, using an atomic with the right memory order, or removing the sharing. Other reports: `lock-order-inversion` (two mutexes taken in opposite orders; fix by a global order), `thread leak`, `mutex destroyed while locked`. A race on a flag read in a loop is not benign; the compiler may hoist the read.

If TSan aborts at start-up on a recent kernel with a message about memory mapping, the cause can be the kernel's address-space randomisation range; check the sanitizer's own documentation for your compiler version before lowering the setting.

## MemorySanitizer

`use-of-uninitialized-value` with origin tracking names where the value was allocated. Trace from the use back to the allocation, then to the field or branch that skipped initialisation. A false report usually means a dependency was not built instrumented; confirm before suppressing.

## Valgrind, when no sanitizer build is possible

```bash
valgrind --leak-check=full --track-origins=yes --error-exitcode=1 ./test_binary
```

`--error-exitcode=1` makes CI fail. Expect a large slowdown and no stack or global overflow detection.
