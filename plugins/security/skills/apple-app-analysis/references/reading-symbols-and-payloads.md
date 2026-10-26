# Reading symbols and payloads

Read after the runtime family is known. This is identification work, not a full native
disassembly: it says where names and logic survive, so the deeper read goes to the right
artifact instead of to the launcher.

## The Mach-O surface

```bash
file ./Example.app/Contents/MacOS/Example
nm -m ./Example.app/Contents/MacOS/Example | head -40
strings -n 8 ./Example.app/Contents/MacOS/Example | head -40
```

`nm -m` prints external and undefined symbols with the library each one comes from, which
is often a better dependency list than `otool -L` for what the app actually calls. A
binary with almost no symbols is stripped, not empty; the code is still there.

Sections worth knowing when they are present:

| Section | What it tends to carry |
| --- | --- |
| `__TEXT,__objc_classname` | Objective-C class names as C strings |
| `__TEXT,__objc_methname` | Selector names |
| `__TEXT,__swift5_types` | Swift type metadata |
| `__DATA,__objc_classlist` | The runtime's class list |
| `__DATA,__const` | String literals and tables |
| `__cstring` | C and framework strings |

Objective-C class and selector names survive stripping far more often than C function
names, because the runtime needs them. `otool -ov` lists the Objective-C metadata when the
binary has it; on a pure Swift or C binary it prints nothing, and that empty result is the
answer, not a failed command.

## Swift symbols

Swift mangles type and function names into symbols beginning with `_$s` (or `_T` on older
toolchains). Demangle them before reporting; Xcode ships the tool as `swift-demangle`, and
`xcrun swift-demangle` invokes it:

```bash
nm ./Example.app/Contents/MacOS/Example | xcrun swift-demangle | head -40
```

A demangled name can expose a module, a type and a method that the stripped binary was
supposed to hide. Treat it as a name the build left behind, not as the source's structure.

## Encryption, again

Confirm before reading any of the above in depth:

```bash
otool -l ./Example.app/Contents/MacOS/Example | grep -A5 LC_ENCRYPTION_INFO
```

`cryptid` 1 means the text pages are encrypted. Symbols in the unencrypted metadata may
still be readable while the code is not; a report that compares symbol names to an empty
disassembly has read two different things.

## Payload per runtime family

**Flutter.** `App.framework/App` on iOS and `libapp.so` on Android carry the Dart AOT
snapshot. Run `file` on it first: the symbols are few and the snapshot is not a Mach-O
class layout you can read with `nm`. Dart-specific tooling is outside this skill; say the
payload was identified and not decompiled.

**React Native with Hermes.** `main.jsbundle` is either plain JavaScript or Hermes
bytecode. Check the first bytes before handing it to a JS parser:

```bash
xxd -l 8 ./Payload/Example.app/main.jsbundle
```

A Hermes bytecode file starts with the Hermes magic rather than `{` or `var`; reading it
as JavaScript produces nonsense. The family's JS is in that bundle, and the native
framework is the runtime that executes it.

**Unity IL2CPP.** The names live in `Data/Managed/Metadata/global-metadata.dat` and the
compiled code in `UnityFramework`/`libil2cpp`. Identify both paths and stop. The method
bodies are native code, so that read belongs to `reverse-engineering`, not to a bundle
inventory. A dumper's mapping is a reconstruction and the report should say so.

**Electron.** The logic is in `app.asar`, not the Mach-O. Hand it to
`packaged-desktop-app-analysis`, which covers ASAR extraction and the fuses.

## What a symbol does not prove

A class named `LicenseValidator` is a name, not a license check. A selector called
`sendAnalytics:` is a selector, not an observed request. The name narrows where to read;
the body has to be read before the claim is made, and a dynamic claim needs the isolated
environment the skill's gates describe.
