# Reading dex without fooling yourself

Read after the manifest facts are recorded, when the question needs the code path rather
than the package's declared surface. Every command here reads; none of them runs the app.

## What a dex actually is

A `classes.dex` is a register-based bytecode container with its own string, type, method
and class tables. A modern app ships several (`classes2.dex`, `classes3.dex`, ...) and a
split or feature module can add more. Two consequences:

- A string or class found in one dex is not the whole app; iterate every `classes*.dex`.
- A missing class in `base.apk` may be delivered by a split, a dynamic feature or a
  downloaded dex, so "not present" is not "not used".

```bash
unzip -l ./app.apk | grep -E 'classes[0-9]*\.dex'
```

## Summary first

Start with the shape, not a full decompile:

```bash
jadx --no-src -d ./jadx-index ./app.apk     # resources and manifest only
jadx -d ./jadx-src ./app.apk                # Java reconstruction
dexdump -f ./classes.dex                    # dex header and counts, from build-tools
```

`jadx` renames are not source names. A class called `a.b.c` is an identifier the compiler
or obfuscator left behind; do not translate it into a business meaning without a call
site that shows one.

## Follow references, not string hits

A host or URL in the string table is a literal the app can reach, not a request it makes.
The evidence is the path:

1. find the string index and the method that loads it;
2. follow the callers inward from the component or export that matters;
3. name each hop with an Evidence ID, and mark a hop you did not read.

Use the decompiler's cross-reference view, or `grep -rn` over the decompiled tree for the
literal and then read the enclosing method. Record the method signature, not just the
file, because obfuscation makes file names useless and line numbers are reconstruction.

## Indirection that breaks a naive read

These are the places a report goes wrong if it treats the decompiled tree as source:

- **Reflection** — `Class.forName`, `getDeclaredMethod`, `invoke`. The target string may be
  built at run time; say the call site is reflective and the target is unresolved.
- **Dynamic loading** — `DexClassLoader`, `PathClassLoader`, `InMemoryDexClassLoader`.
  The loaded code may not be in the APK at all; a feature module or a download is a
  separate artifact to collect and analyse on its own.
- **JNI** — a `native` method declares a boundary. The Java side proves the call exists;
  the behaviour is in the `.so`, which is `native-binaries` work.
- **WebView bridges** — `addJavascriptInterface`, `evaluateJavascript`, `loadUrl` with a
  `javascript:` URL or a custom scheme. The Java side is a bridge; the loaded page or
  bundle is another artifact.
- **String encryption and packing** — a packer decrypts classes at run time. If the dex
  count or method bodies look implausible, identify the packer from its loader before
  reading further, and report that the real code was not in the static image you read.

## Obfuscation is a fact to record, not a wall

Record what you observed: single-letter package names, renamed members, removed line
numbers, string encryption, a packer, or a split that carries the logic. None of these is
"the app is hiding something"; they are build choices. The report says which of them
limited the read, and which conclusions therefore rest on names alone.

## Dynamic confirmation stays separate

Static reading answers what code exists and how it is wired. Whether a method runs on
launch, what a server returns, and what a decrypted payload contains are runtime claims.
If the question needs them, use a lab device or emulator with no production credentials, a
separate authorisation, and network capture you control. Do not install an untrusted
sample on a daily-driver phone to "just check".

The same boundary as `dynamic-analysis-and-safety` under `reverse-engineering` applies:
observe inside the isolated environment, and report exactly which observation came from
it. Frida and debugger sessions are dynamic work, not a shortcut past the static read.
