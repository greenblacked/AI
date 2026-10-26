# Dynamic analysis and the environment it runs in

Read this before running anything you did not write, and before confirming a static finding
(gate 4) by watching the target run. The commands below are verified against the same test
binary as [native binaries](native-binaries.md): a `check_license` function that compares
its argument against a fixed string.

## Which environment this step is allowed to happen in (gate 3)

Before any command in this file: is the target yours, a course's known-safe sample, or
something of unknown or untrusted origin (a sample for malware triage, an unfamiliar binary
found somewhere, a CTF challenge you have not fully read yet)? The first two can run on a
normal development machine. The third runs only in an isolated, disposable environment —
a VM or container with no access to your real credentials, files or network, snapshotted
before the target runs so you can revert rather than clean up. Say in your notes which case
you are in; do not decide this silently.

## A breakpoint confirms a specific function is reached, with specific arguments

```bash
gdb -q -batch -ex "break check_license" -ex "run wrong" -ex "finish" -ex "quit" ./target
```

On the test binary this stopped at `check_license(key=... "wrong")`, printed the source line,
and `finish` showed the return value (`0`, meaning the comparison failed). That is strictly
stronger evidence than the static read in the native-binaries reference: it confirms the
function is reached on this exact input and shows the exact value it returned, rather than
inferring both from the disassembly. Change the breakpoint and the arguments to match
whatever static reading turned up as worth confirming.

## A syscall trace confirms what the process actually touches

```bash
strace -e trace=write ./target wrong
```

`-e trace=<name>` limits the trace to the syscalls worth reading; on the test binary this
showed the single `write(1, "Access denied\n", 14)` an incorrect argument produces — the
check's failure path, confirmed by watching the process run rather than inferred from the
disassembly. Trace `network` or `openat` the same way to confirm or refute a claim about what
a binary reaches over the network or on disk — a strong check against a binary described as
"doesn't touch the network" before you trust that description. Running the target with a
value that would make the check succeed is the thing gate 5 keeps out of this file as much as
out of the report: tracing the failure path, or a breakpoint on the comparison itself as in
the previous section, confirms the same mechanism without producing a working key.

## What this reference does not cover

A userspace function-call tracer (`ltrace` or equivalent) was not available in the
environment this skill was verified in and its commands are not given here; use it the same
way as `strace` when it is available, scoped to the function names that matter. Instrumenting
a running process to call its own functions with chosen arguments (dynamic binary
instrumentation, hooking) is a stronger technique than either of the above for a target that
resists simple tracing, but its exact invocation depends on the tool and was not verified for
this skill — read that tool's own documentation, and keep gate 3 in force while you do.
