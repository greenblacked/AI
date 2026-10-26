# CIL, metadata and the tooling

Read after `file` confirms a managed assembly and before choosing how deep to read.

## Contents

- [What the container actually is](#what-the-container-actually-is)
- [Fields to record](#fields-to-record)
- [IL in the shape you will meet it](#il-in-the-shape-you-will-meet-it)
- [Tool flags](#tool-flags)
- [Obfuscation and packing](#obfuscation-and-packing)
- [Unity: managed versus IL2CPP](#unity-managed-versus-il2cpp)
- [What the metadata cannot prove](#what-the-metadata-cannot-prove)

## What the container actually is

A managed assembly is a PE file with a CLI header. The PE part carries the sections; the CLI
header (the `COR20` data directory) points at the metadata root and the entry point. The
metadata root begins with the `BSJB` signature and names the streams:

| Stream | What it holds |
| --- | --- |
| `#~` | The compressed metadata tables (types, methods, fields, members) |
| `#Strings` | Names as UTF-8 strings |
| `#US` | User strings — the literals compiled into IL |
| `#GUID` | GUIDs |
| `#Blob` | Signatures, constants and custom attribute values |

This is why `strings` is useful: method, type and literal names live in plain text even
when the code is optimised. It is also why a missing name proves nothing — a trimmed or
obfuscated build can carry a name table that does not match the code.

## Fields to record

- **Assembly identity** — simple name, version, culture and public key token. Two files with
  the same simple name are not the same assembly.
- **Target framework** — `TargetFrameworkAttribute`, or the framework name in the metadata.
  A 4.x full-framework assembly and a runtime 8 assembly fail differently under the same tool.
- **Entry point** — `Main`, a module initializer, or a library export. An assembly with no
  entry point is a library even if it is named `.exe`.
- **Debug build markers** — `DebuggableAttribute` and a PDB path in the debug directory.
  A release build can still carry them; the attribute is a claim about the build.
- **Mixed mode** — native sections plus IL. The CLI header is present but some methods are
  native; a decompiler will show stubs or fail on them.

## IL in the shape you will meet it

CIL is a stack machine. The opcodes that matter for reading a call path:

- `ldstr` loads a user string; the literal in `#US` is what a license or URL check compares.
- `call` and `callvirt` differ: `callvirt` dispatches through the object's type and can throw
  `NullReferenceException`; a report that says "calls X" should say which.
- `newobj` constructs; `initobj` zeroes a value type.
- `ldftn`/`ldvirtftn` take a function pointer, the managed equivalent of an indirect call.
- `switch` is a jump table; `brtrue`/`brfalse` are the common branch shapes.
- `constrained.` and generic tokens mean the target depends on the instantiation.

Decompiled C# loses some of this on purpose: `async` becomes `AsyncStateMachineAttribute` and
a generated `MoveNext`, iterators become `IEnumerable` classes, and lambdas become methods
named `<Main>b__0_0`. When the question is about one of those, read the generated method and
name the original in the report.

## Tool flags

`ilspycmd` is the command-line decompiler used here; the flags below were exercised against a
small runtime 9 console assembly.

| Question | Command |
| --- | --- |
| Which types exist? | `ilspycmd -l "c i s e d" ./App.dll` |
| One type as C# | `ilspycmd -t Namespace.Type ./App.dll` |
| The same type as IL | `ilspycmd -il -t Namespace.Type ./App.dll` |
| IL with source lines | `ilspycmd --il-sequence-points -t Namespace.Type ./App.dll` |
| Whole project | `ilspycmd -p -o ./out ./App.dll` |
| Resolve dependencies | `ilspycmd -r ./deps -t Namespace.Type ./App.dll` |

The tool runs on a specific managed runtime; a version mismatch prints the framework it wants
and exits. Install a matching runtime or set `DOTNET_ROLL_FORWARD=Major` for the read, and
record which one you used if the output matters.

`-l` takes its entity types space-separated inside one argument. The comma form,
`-l c,i,s,e,d`, is accepted but matches no entity type and prints an empty list with a zero
exit status, which reads as "no types" rather than "bad argument". Confirm the list is
non-empty before concluding an assembly is empty.

`monodis` and `ildasm` read the same metadata when they are available; their output differs in
formatting, not in what the CLI header contains.

## Obfuscation and packing

Common managed obfuscators, commercial and open-source, rename types to
single characters, encrypt user strings, inject invalid metadata and add a module initializer
that decrypts at run time. Signals in the type list:

- every namespace is one character, or the type list is dominated by `A`, `B`, `C`;
- a large `Module` `.cctor` that references an array of bytes;
- `ilspycmd` reports "invalid metadata" or refuses specific methods;
- `#US` holds very few readable strings relative to the code size.

Record the packer or obfuscator if you can identify it, and say that the static image you
read is the outer layer. Do not describe decrypted code you did not actually read.

## Unity: managed versus IL2CPP

A Mono Unity build ships `Assembly-CSharp.dll` (and friends) under `Managed`, and those are
ordinary managed assemblies read exactly as above. An IL2CPP build ships
`global-metadata.dat` plus native `libil2cpp`, and its method bodies are native code. That
read belongs to `reverse-engineering` on every platform. A desktop or mobile app package is
identified first by `app-bundle-analysis`, which then hands the method bodies back. The
presence of `global-metadata.dat` is the signal to change skills, not a different way to run
`ilspycmd`.

## What the metadata cannot prove

A type named `LicenseValidator` is a name; a `ldstr` next to an equality check is a literal
and a comparison, not proof the check runs on this path. What the assembly does at run time,
which configuration it reads, and what a server returns are separate claims. Read the body
for the claim, and keep runtime observation in the isolated environment the skill gates
require.
