# Managed bytecode (JVM, and briefly .NET)

Read this once you have identified a `.class` file or a JAR (see
[packaged and mobile artifacts](packaged-and-mobile-artifacts.md) for the container step).
Managed bytecode is not machine code: a JVM `.class` file runs on the Java Virtual Machine,
not the processor directly, so a native disassembler has nothing to read it with, and the
right tool is one built for the runtime instead. The commands below are verified against a
small `.class` file built for this file: a `checkLicense` method comparing its argument
against a fixed string with `String.equals`, compiled with `javac`.

## Identify, then read the public shape before the bytecode

```bash
file ./License.class
javap License.class
```

On the test file, `file` reported `compiled Java class data, version 65.0` — the version
number is the class file format version, not the Java language version, and a decompiler or
JVM too old for that version will refuse to load it. `javap` with no flags lists the public
and protected members: on the test class, the constructor and `main`, but not the
package-private `checkLicense`, because plain `javap` hides anything not reachable from
outside the class.

## The full disassembly, including private methods and the constant pool

```bash
javap -c -p ./License.class
```

`-p` includes private and package-private members, and `-c` disassembles the bytecode of
each one. On the test class this showed `checkLicense`'s body: `ldc #7` loading the constant
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

A JAR built with the `jar` tool and containing an actual class file was identified
specifically: `file` reported `Java archive data (JAR)`, not the generic zip label. A
hand-built zip holding only a bare `META-INF/MANIFEST.MF` text file, with no class file
inside it, reported the generic `Zip archive data` instead — so it is the presence of real
class files, not the manifest alone, that this version of `file` keys on; which exact rule
it applies was not traced further than that. Either way, `unzip -l` lists every `.class`
file inside, and each one is read the same way as the bare `.class` file above.

## Running the class, within gate 3

```bash
java -cp . License wrong
```

On the test class this printed the failure-path message, confirming the comparison is
reached and fails on an incorrect argument — the same dynamic confirmation a native binary
gets from a breakpoint or a trace, and the same gate 5 rule applies: only ever run this with
an input you expect to fail, or with your own test binary's or a CTF's own answer, never with
a value recovered from someone else's software to show that it succeeds.

## .NET and other managed runtimes

A .NET assembly (a `.dll` or `.exe` containing Common Intermediate Language) is the same idea
— bytecode for a managed runtime, not machine code — but its own disassembler (`ildasm`,
`monodis`, or a decompiler such as ILSpy or dnSpy) was not available to verify commands
against for this skill. `file` reports a .NET assembly as a `PE32` executable, because CIL is
still packaged inside the PE container; do not read it with the tools in
[native binaries](native-binaries.md), because disassembling the PE's native code sections
will not show you the managed method bodies. Read the chosen tool's own documentation for the
current invocation before using it.
