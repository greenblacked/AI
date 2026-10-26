# Native binaries (ELF, PE, Mach-O)

Read this once `file` has told you the target is a native executable or library, not a
packaged app. The commands below are verified against a small ELF binary built for this
file — a `check_license` function compared against a fixed string, the shape of a real
license check — and read back exactly what each tool actually printed.

## Identify the format before anything else

```bash
file ./target
```

On the test binary this printed `ELF 64-bit LSB pie executable, x86-64, ... dynamically
linked, ... with debug_info, not stripped`. That one line already answers four questions:
architecture, whether it is stripped (symbol names survive or not), whether it is
dynamically or statically linked (which other libraries matter), and whether debug
information is present (source-level debugging is possible). A 64-bit PE binary reports
`PE32+ executable` and a 64-bit Mach-O one `Mach-O 64-bit executable`; the tools below are
ELF-first, so a PE or Mach-O target is better read with a disassembler built for that format
(Ghidra and radare2 both read all three) rather than with `objdump`/`nm`/`readelf`.

## Strings: the cheapest signal

```bash
strings -n 6 ./target
```

`-n 6` drops short, noisy matches. On the test binary this surfaced `DEMO-1234`, `Access
granted`, `Access denied` and the `usage: %s <key>` format string — a candidate comparison
value and both outcome messages, before a single instruction was read. A string found this
way is a lead to where a check lives, not a finding: confirm where it is actually used (gate
4), and report that a comparison against a fixed value sits at that address rather than the
value itself (gate 5) unless the target is your own test binary or a CTF challenge.

## Symbols: what the binary itself calls its functions

```bash
nm ./target | grep ' T \| t '
```

`T` marks a global text symbol in the symbol table, `t` a local one; both are code. On the
test binary this listed `check_license` and `main` by name, because the binary was not
stripped. Stripping the same binary (`strip`) made `file` report `stripped` and `nm` alone
report `no symbols`. `nm -D` still printed a dynamic symbol table on the stripped copy, but
not the names this skill is usually after: for an ordinary executable that table is mostly
what it imports from shared libraries (`printf`, `strcmp`, `__libc_start_main`), not what it
defines itself; a shared library's own exports show the same way, which is where `nm -D`
becomes the useful read instead of a dead end. Past that, work from addresses and call
patterns rather than names.

## Disassembly of one function at a time

```bash
objdump -d --disassemble=check_license ./target
```

`--disassemble=<name>` limits output to one function, which matters once a binary has more
than a handful. On the test binary this showed `check_license`'s prologue
(`endbr64; push %rbp; mov %rsp,%rbp; sub $0x10,%rsp`) followed by the call into `strcmp` and
the comparison of its result — exactly a license-key check, read statically. Without a
symbol name, disassemble the whole `.text` section (`objdump -d ./target`) and work from
`main`'s calls outward, or load the binary into a decompiler (Ghidra, radare2 (`r2`) or its
fork rizin, or a commercial one) for a higher-level read; treat its output as a hypothesis
(gate 4), not as source.

## Linked libraries and what they imply

```bash
readelf -d ./target | grep NEEDED
```

The `Dynamic section`'s `NEEDED` entries name the shared libraries the binary asks for
directly — on the test binary, `libc.so.6`. `grep` keeps every one of them, where `head`
would cut a long list short. That list is direct dependencies only: a library those
libraries need in turn does not appear in it, and neither does anything loaded at runtime.
On the system this file was checked against, `curl` named three libraries directly, while
its own `libcurl.so.4` named fourteen, twelve of them missing from `curl`'s list and several
of them network or TLS libraries (`libssh.so.4`, `libnghttp2.so.14`, `libssl.so.3`). To
follow the chain without running anything, read each named library's own `NEEDED` entries
the same way, finding its file with `ldconfig -p` or on the library search path. Do not
reach for `ldd` on the target: its own manual says never to use it on an untrusted
executable, because some versions run the program to answer. A binary linking a network
library when the task description says "offline" is itself a finding worth confirming
dynamically (next file), and the absence of one from the direct list proves nothing.
