# Managed bytecode (JVM, and briefly other managed runtimes)

Read this once you have identified a `.class` file or a JAR (see [packaged and mobile
artifacts](packaged-and-mobile-artifacts.md) for the container step). Managed bytecode is
not machine code: a `.class` file runs on the JVM, not on the processor directly, so a
native disassembler has nothing to read it with, and the right tool is one built for the
runtime instead. The commands below are verified against a small `.class` file built for
this file: a private `checkLicense` method comparing its argument against a fixed string
with `String.equals`, compiled with `javac`.

## Identify, then read the public shape before the bytecode

```bash
file ./License.class
javap License.class
```

On the test file, `file` reported `compiled Java class data, version 65.0` — the version
number is the class file format version, not the language version, and a decompiler or
JVM too old for that version will refuse to load it. `javap` with no flags lists the public
and package-private members: on the test class, the constructor and `main`, but not the
private `checkLicense`, because plain `javap`'s default visibility (effectively
`-package`) stops at private.

## The full disassembly, including private methods and the constant pool

```bash
javap -c -p ./License.class
```

`-p` adds private members to the listing (package-private ones were already shown without
it), and `-c` disassembles the bytecode of each one. On the test class this showed
`checkLicense`'s body: `ldc #7` loading the constant
pool entry `DEMO-1234` as a string literal, followed by `invokevirtual` on `String.equals`.
A `ldc` of a literal next to an `equals` or a comparison method is the bytecode-level version
of a license check — the same signal `strings` and a disassembler give for a native binary,
and it carries the same caveat: the constant pool entry is a lead to where the comparison
lives, not a finding to report as the check's value, unless you are in gate 5's stated
exception.

## A JAR's own identification, separate from a bare zip's

```bash
jar cfe demo.jar License License.class   # how a JAR is normally built, for reference
file demo.jar
unzip -l demo.jar
```

An archive built with the `jar` tool was labelled `Java archive data (JAR)` in every case
tried, with `file` 5.45: with a class and a manifest, with only a manifest, and with only a
text file and no manifest. The `jar` tool marks the archive's first entry with an extra field
whose header ID is 0xCAFE, which `file` recognises; the bytes `fe ca 00 00` sit right after
the first entry's name. A plain `zip` got the JAR label only for some layouts: a manifest
first followed by a class file did, while the manifest alone, the class alone, the class
first, and the manifest with a text file did not. So the label is a hint about how the
archive was built, not proof of what is inside. `unzip -l` is what tells you: it lists every
`.class` file inside, and each one is read the same way as the bare `.class` file above.

## Running the class, within gate 3

```bash
java -cp . License wrong
```

On the test class this printed the failure-path message, confirming the comparison is
reached and fails on an incorrect argument — the same dynamic confirmation a native binary
gets from a breakpoint or a trace, and the same gate 5 rule applies: only ever run this with
an input you expect to fail, or with your own test binary's or a CTF's own answer, never with
a value recovered from someone else's software to show that it succeeds.

## Other managed runtimes

A Common Intermediate Language (CIL, ECMA-335) assembly (a `.dll` or `.exe`) is the same idea
— bytecode for a managed runtime, not machine code — but no toolchain (`dotnet`, `mono`),
disassembler (`ildasm`, `monodis`) or decompiler (ILSpy, dnSpy) was available to
verify anything against for this skill, including what `file` reports for one; take any
specific label as unverified until you check it yourself. CIL is packaged inside an ordinary
PE container either way, so do not read the assembly with the tools in
[native binaries](native-binaries.md) on the strength of that container alone — disassembling
the PE's native code sections will not show you the managed method bodies. Read the chosen
tool's own documentation for the current invocation before using it.
