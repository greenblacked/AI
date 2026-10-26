---
name: packaged-desktop-app-analysis
description: "Open up a packaged desktop application you are authorised to examine when its source is missing: identify the packaging first — Electron with an ASAR bundle, a Node single executable, PyInstaller, or a bundled JVM or .NET app — read the application's own JavaScript or bytecode out of the container, check which runtime switches the package exposes, and confirm behaviour without running it on a machine that holds your credentials. Use for \"this app is Electron, where is its source\", \"what is inside this PyInstaller exe\", or \"why does the app ignore --inspect\". Not for a native binary's disassembly (reverse-engineering), an Apple bundle's structure or entitlements (apple-app-analysis), a phone package (reverse-engineering), a web app's shipped bundle (reverse-engineering), or rebuilding a feature you are licensed to copy (feature-recreation)."
allowed-tools: "Read, Glob, Grep, Bash(file:*), Bash(shasum:*), Bash(sha256sum:*), Bash(xxd:*), Bash(strings:*), Bash(unzip:*), Bash(find:*), Bash(otool:*), Bash(rea:*), Bash(npx:*)"
---

# Packaged desktop app analysis

Good looks like the packaging named from its own bytes, the application's JavaScript or
bytecode read from the container as data, and every claim about what the app does tied to a
path inside the package rather than to the installer's description.

The job fails in a few ways. The installer is treated as the application, so the DMG or MSI
is unpacked and read while the actual ASAR or CArchive inside it is never opened. An Electron
app is launched with `--inspect` before its fuses are read, and the flags are silently
ignored because the package disabled them — the analysis then reports "no main process
target" as a finding about the app. Extracted JavaScript is described as the vendor's source
tree, when it is a derived bundle with minified names and no original layout. And the app is
run on the analyst's workstation, with the real profile, tokens and browser session, because
it was "just a small tool".

## Scope

Use for: an Electron, Node single-executable, PyInstaller, bundled JVM or .NET desktop
application you own or are contracted to inspect; reading what a shipped app contains when
there is no source; confirming whether a package can be attached to a debugger at all; and
triage of a suspicious installer before it is deployed.

Do not use for: disassembling the native framework or runtime inside the package, which is
`reverse-engineering` with its native reference; the structure, signature and entitlements of
an Apple `.app` or IPA, which is `apple-app-analysis`; a phone package, which
`reverse-engineering` covers; a web application's served bundle, which the same skill covers
in its browser reference; or building your own implementation of a feature, which is
`feature-recreation`.

## Hard gates

1. **Authorisation, and a disposable host.** Write down the permission before the first
   command. Never launch the application on the workstation that holds your credentials,
   history or tokens; use a VM or container with no real account signed in, and keep the
   network off unless the behaviour under test needs it.
2. **Read the container as data.** `unzip`, an ASAR extractor and an archive inventory are
   reads. An installer, an `install.sh`, a post-install script or a startup hook inside the
   package is evidence, not a step.
3. **Derived output is not original source.** Extracted JavaScript, reconstructed `.pyc`
   headers and IL are what the packaging produced, not the project the vendor built. Say
   which path in the package a finding came from, and never present recovered names or
   structure as the original ones.
4. **Check the runtime switches before you try to observe.** Electron fuses, Node's
   single-executable configuration and a bundled runtime's flags decide what observation is
   possible. Reading them first turns "the debugger found nothing" into "this package
   disabled that path".
5. **No licence, DRM or anti-cheat circumvention.** Naming the mechanism is the deliverable;
   the patched fuse bytes, the unpacked-and-repacked bundle and the bypass are out of scope.
6. **Every claim cites a path inside the package.** The ASAR member, the extracted file, the
   section offset — not "the app collects telemetry" with nothing behind it.

## Workflow

### 1. Identify the packaging

```bash
file ./Example.AppImage
shasum -a 256 ./Example.AppImage
```

`file` on the outer artifact rarely names the packaging one level down. List the container
before extracting anything — `unzip -l` for a zip-shaped package, the bundle layout for a
macOS `.app`, the installer's file list for an MSI or DEB — and look for the marker that
identifies the runtime: `app.asar` for Electron, a `sea` blob or an appended Node executable,
a PyInstaller CArchive cookie, a bundled `libjvm` or a `.dll` single-file bundle. The
reference below gives the marker for each and what it implies.

### 2. Inventory and extract through the right reader

For an ASAR or an extracted JavaScript tree, REA's `analyze_javascript_application` returns a
module graph with paths, hashes and route hints, and `inspect_artifact` inventories a zip,
DMG, MSI or PyInstaller executable without executing it. For a PyInstaller package, the same
pair reports the CArchive layout and can publish its members into an extraction directory;
bytecode decompilation is not part of that capability, so a `.pyc` you recover is derived
bytes with a reconstructed header, not the vendor's source.

### 3. Read the switches the package exposes

For an Electron package, `inspect_electron_fuses` reads the fuse wire out of the binary and
answers the questions that decide what you can do next: whether `--inspect` is honoured,
whether `ELECTRON_RUN_AS_NODE` is allowed, whether the app validates an embedded ASAR
integrity hash, and whether it loads code only from `app.asar`. Read it before attaching a
debugger; a fuse that is off explains an empty target list without any bug in your tooling.

### 4. Read the application's own code

Work from the entry point the package declares (`main` in the ASAR's package metadata, the
single-executable's entry, the CArchive's script) outward: what it opens, what it starts at
launch, which endpoints it talks to, and where it keeps state. Minified bundles are read at
the call sites that matter, not by trying to reconstruct the original module names.

### 5. Report

For each finding: the package path, the member or extracted path, the digest of the
container, and whether it was observed, inferred or unresolved. State what the package cannot
show — the server-side behaviour, the build configuration, or the code the packager stripped.

## Anti-patterns

**Reading the installer and calling it the app.** The DMG, MSI or DEB is a delivery wrapper;
the application is the ASAR, CArchive or runtime bundle inside it, and the wrapper's scripts
are only interesting on their own terms.

**Attaching a debugger before reading the fuses.** An Electron app with Inspector arguments
disabled produces an empty target list, and that is the package working as designed, not
evidence about the main process.

**Reporting extracted bundle internals as the vendor's architecture.** A minified module
named `a` that calls an endpoint is a fact about the bundle; "the app's networking module"
is a claim the bundle does not support.

**Launching the app on your own machine to "just see".** It inherits your profile, your
tokens and your network, in a package whose origin you have not established.

**Repacking a modified ASAR.** That is a circumvention artifact, and gate 5 keeps it out of
the deliverable.
