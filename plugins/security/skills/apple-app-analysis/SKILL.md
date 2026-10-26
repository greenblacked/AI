---
name: apple-app-analysis
description: "Read an Apple application you are authorised to examine — a macOS .app bundle, an IPA, or an app inside a DMG — when the source is missing or does not match what ships: identify the bundle from its Info.plist, read the signature and entitlements, follow the frameworks to the runtime family (native, React Native, Flutter, Unity, Hermes), and check whether the payload is encrypted before planning any deeper read. Use for \"what does this Mac app have access to\", \"what is inside this IPA\", or \"is this app's binary readable at all\". Not for ranking live crash reports (crash-triage), native disassembly of the Mach-O (reverse-engineering), an Android package (reverse-engineering), shipping an iOS build (mobile-release), or extracting a DRM-protected store binary."
allowed-tools: "Read, Glob, Grep, Bash(file:*), Bash(shasum:*), Bash(sha256sum:*), Bash(plutil:*), Bash(codesign:*), Bash(otool:*), Bash(unzip:*), Bash(find:*), Bash(strings:*), Bash(xxd:*), Bash(rea:*), Bash(npx:*)"
---

# Apple app analysis

Good looks like a bundle whose identity, signature and entitlements were read before its code,
whose runtime family was established from the frameworks actually present, and whose
encryption state was checked before anyone planned a decompiler session.

The job fails in a few ways. The `.app` directory is treated as a single binary, so the
frameworks, the plugins and the resource bundles are never listed. An entitlements dump is
read as "permissions the app uses", when an entitlement is a claim the signer made and the
system may or may not honour. A store-downloaded IPA is opened in a decompiler without
checking `cryptid`, and the empty or garbage code sections are reported as a stripped binary.
A React Native or Flutter app is read as if its logic were in the Mach-O, when the
interesting payload is a JavaScript bundle or an AOT blob.

## Scope

Use for: a macOS `.app`, an IPA, an app inside a DMG, or an app extension you own or are
contracted to inspect; answering what an app is allowed to do, what it bundles, and which
runtime its logic actually lives in; and triage of an app before it is deployed to a fleet.

Do not use for: ranking and fixing live crashes, which is `crash-triage`; disassembling the
native Mach-O beyond the identification steps here, which is `reverse-engineering`; an Android
package, which the same skill covers; building, signing or shipping an iOS release, which is
`mobile-release`; or extracting code from a DRM-protected store download.

## Hard gates

1. **Authorisation before the first read.** An app you downloaded is not automatically an app
   you may analyse; write down whose it is and which permission covers it. Keep the original
   and work on a copy.
2. **Signature first, code second.** `codesign` and the entitlements answer what the app
   claims and who signed it. Read them before the binary, because they change how the rest is
   interpreted.
3. **Check the encryption state before planning a deeper read.** A Mach-O with `cryptid` 1 has
   encrypted code sections; a decompiler will show you noise. Extraction or decryption of a
   store binary is out of scope — ask the owner for a decrypted build or an enterprise-signed
   copy instead.
4. **An entitlement is a claim, not an observation.** `com.apple.security.network.client` says
   the signer asked for the network; whether the app uses it is a separate, dynamic claim.
5. **Never run the app on a host with your credentials or your Apple ID.** Launch it in a
   disposable VM, signed out, with the network off unless the behaviour under test needs it.
6. **No DRM or licence circumvention.** Naming a check is the deliverable; a patched binary,
   a decrypted App Store payload or a bypass is out of scope.

## Workflow

### 1. Confirm the bundle and its identity

```bash
file ./Example.app/Contents/MacOS/Example
plutil -p ./Example.app/Contents/Info.plist | head -40
shasum -a 256 ./Example.app/Contents/MacOS/Example
```

`Info.plist` gives the bundle identifier, version, minimum OS, document types, URL schemes and
whether the app declares App Transport Security exceptions. Those declarations are what the
app says it does; the binary and entitlements are what it can do.

### 2. Read the signature and entitlements

```bash
codesign -d --entitlements :- ./Example.app
otool -L ./Example.app/Contents/MacOS/Example
```

The entitlements plist is printed as one long line; read it for sandbox state, keychain access
groups, app groups, associated domains, network client and server, and `get-task-allow`, which
marks a development build that can be attached to. `otool -L` names the frameworks and dylibs
the app links directly — the cheapest signal for what it depends on.

### 3. Establish the runtime family

Look at `Contents/Frameworks` and the linked libraries: `Electron Framework` or `app.asar` is
a packaged desktop app (`packaged-desktop-app-analysis`); `Flutter.framework` plus
`App.framework` means Dart AOT code in `App.framework/App`; `UnityFramework` plus
`Data/Managed` or `global-metadata.dat` means IL2CPP; `hermes.framework` plus an
`index.android.bundle`-style file means React Native. Each family moves the analysis to a
different payload, and [Apple bundle anatomy](references/apple-bundle-anatomy.md) says which
path holds it, alongside the entitlement table, the encryption check and the IPS layout.

### 4. Check encryption before any decompiler

```bash
otool -l ./Example.app/Contents/MacOS/Example | grep -A5 LC_ENCRYPTION_INFO
```

No output means no encryption load command. A `cryptid` of 1 with a non-zero `cryptoff` means
the text is encrypted; stop here and say so rather than reading the decrypted-looking noise.

### 5. Inventory the payload

For an IPA, the outer artifact is a zip: `Payload/Example.app` is the bundle inside. List it
before extracting, then read the bundle as in step 1. For a DMG, read the image read-only and
treat the `.app` inside as the artifact.

### 6. Report

For each finding: the path inside the bundle, the digest of the binary, the entitlement or
framework it came from, and whether it is a declaration, an observation or an unknown. State
what the bundle cannot prove: runtime behaviour, server-side handling, and whether the App
Store build differs from the copy you have.

## Anti-patterns

**Reading an entitlements file as a list of what the app does.** Entitlements are requested
capabilities; the OS grants them, and the code may never call the API. Report the claim and
the evidence for use separately.

**Opening a store IPA in a decompiler without checking `cryptid`.** Encrypted text sections
decompile into plausible-looking nonsense, and a report built on them is worse than no report.

**Treating the Mach-O as the whole app.** A Flutter or React Native app's logic is almost
entirely in a framework, a bundle or a metadata file; the native binary is a launcher.

**Running the app with your own Apple ID to see the login flow.** That is your credentials in
someone else's client, and it is the failure gate 5 exists to prevent.
