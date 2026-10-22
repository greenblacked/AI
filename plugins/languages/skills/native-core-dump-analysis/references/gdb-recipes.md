# gdb recipes for a core file

## Open and orient

```bash
gdb -batch -ex 'info sharedlibrary' app core          # libraries found or missing
gdb -batch -ex 'bt' app core                          # faulting thread only
gdb -batch -ex 'thread apply all bt full' app core    # every thread with locals
gdb -batch -ex 'info threads' app core
eu-unstrip -n --core core                             # build IDs recorded in the core
```

Inside an interactive session: `thread N` switches threads, `frame N` and `info locals` look at a frame, `info registers` shows the registers, `x/16gx $sp` dumps the stack, `x/8i $pc` shows the instructions around the fault, `info proc mappings` lists the memory map.

## Libraries that do not match

Copy the crashed system's libraries to a directory and run `set sysroot /path/to/copy` before loading. If the core came from a container, export the image's filesystem and use that as the sysroot. Check each library's build ID against the list from `eu-unstrip -n --core`.

## Reading the faulting address

| Address | Likely meaning |
| --- | --- |
| Near zero | Null pointer plus a field offset |
| Looks like text (bytes 0x20 to 0x7e) | A buffer overran onto a pointer |
| Close to the stack boundary | Stack overflow or runaway recursion |
| A valid heap address in a freed block | Use after free; confirm under a sanitizer |

## Locks and threads

Find threads blocked in `pthread_mutex_lock` or `futex` frames; the mutex's owner field (print the mutex in the frame) names the holder thread id, which maps to a thread in `info threads`. A cycle of holders and waiters is a deadlock; a holder inside a long call is contention.

## Rust and Go

Rust frames in backtraces demangle by default; `set print asm-demangle on` is for `x/i` and `disassemble` output; panics that abort leave `rust_panic` or `abort` frames, so walk up to the first frame in your crate. For Go, a core from a cgo program shows goroutines as threads running `runtime` frames; read the Go traceback printed to stderr first.
