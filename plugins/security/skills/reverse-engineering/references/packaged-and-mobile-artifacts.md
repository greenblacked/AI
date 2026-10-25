# Packaged and mobile artifacts (APK, JAR, and similar zip-backed packages)

Read this once `file` tells you the target is a zip-backed package rather than a bare native
binary: an APK or a JAR. Both are a zip container around a known internal layout, so
the first read is the same shape for either, and the commands below are verified against a
zip built with an APK's own layout (`AndroidManifest.xml`, `classes.dex`, `META-INF/CERT.RSA`,
added to the zip in that order — member order turns out to matter, below).

## Confirm the container, then list it without extracting

```bash
file ./target.apk
unzip -l ./target.apk
```

With `AndroidManifest.xml` added to the zip first, `file` reported `Android package (APK),
with AndroidManifest.xml` on the test artifact; adding `classes.dex` first instead gave the
same APK label naming that file. Rebuilding with `META-INF/CERT.RSA` first made `file` fall
back to the generic `Zip archive data, at least v1.0 to extract, compression method=store`.
All three outputs are correct for a zip-backed mobile app package — which one you get
depends on member order, not on whether the file actually is an APK, and exactly which
member or members `file`'s own rule looks for was not traced further than that. An archive
built with `zip` holding only `META-INF/MANIFEST.MF` reported the generic `Zip archive data`
label. An archive built with the `jar` tool carries a 0xCAFE marker and was labelled `Java
archive data (JAR)` in every case tried; see [managed bytecode](managed-bytecode.md) for the
JAR case. Either way, `unzip -l` lists every entry without writing anything to disk — on the
test artifact, the three files just named, nothing more — so list before you extract and
decide what is worth pulling out of what may be a large archive.

```python
import zipfile

z = zipfile.ZipFile("target.apk")
for n in z.namelist():
    print(n)
```

The same listing from the standard library's `zipfile` module, which matters once the next
step is parsing a manifest or a resource table programmatically rather than reading a
directory listing by eye.

## What the layout tells you before you read any code

- **`AndroidManifest.xml`, `classes.dex`, and a `META-INF/*.RSA` or `*.DSA` present:** an
  APK. The manifest (binary XML until decoded) names every component, permission and
  entry point; `classes.dex` is the compiled application code, read with a DEX-aware tool
  (`apktool`, `jadx`) rather than a native disassembler, because it is bytecode for the
  mobile runtime, not machine code. `META-INF` holds the signing certificate, which
  identifies who signed the build, not who wrote the code inside it.
- **Only `META-INF/MANIFEST.MF`, with `.class` files elsewhere in the archive:** a plain JAR;
  the `.class` files are JVM bytecode, read with a JVM-aware decompiler rather than a native
  one, for the same reason as the APK's `classes.dex`.

This file covers only the zip-backed case. A desktop app that bundles its own browser runtime is not one: its
JavaScript ships as a `resources/app.asar` file — a concatenated-file format of its own,
with its own header rather than a zip's, so `file` does not report it as a zip — or as a
plain `resources/app/` directory sitting beside a native launcher binary, in which case the
JavaScript is already source, not something to unpack. Neither case was tested with a real
build of such an app for this skill; read `asar`'s own documentation for the current unpacking
command before using it. A phone app package (an IPA) is a zip with a top-level `Payload/<name>.app/`
directory holding `Info.plist` and the app's native executable directly inside it; this
layout was also not independently verified against a real IPA for this skill, so confirm it
against the platform vendor's own documentation or a sample you have before relying on an assumed path
inside `Payload/`.

## Before extracting a large or untrusted archive

List it first (above) and estimate the extracted size from the listing before extracting
everything; a package can be small on disk and enormous unpacked. For an artifact of unknown
origin, extract and read inside the isolated environment this skill's dynamic-analysis
reference describes (gate 3), not on the machine doing the triage.
