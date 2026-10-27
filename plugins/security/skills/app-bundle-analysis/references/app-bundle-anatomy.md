# App bundle anatomy

Read this once the bundle is confirmed and the question is where its logic and its
capabilities actually live.

## The layouts

A desktop `.app` bundle is a directory, not a file:

```text
Example.app/
  Contents/
    Info.plist
    MacOS/Example                 the Mach-O executable
    Frameworks/                   bundled frameworks and dylibs
    Resources/                    nibs, assets, helper bundles, JS bundles
    PlugIns/                      app extensions (.appex)
    _CodeSignature/               the signature
```

An IPA is a zip with one top-level directory:

```text
Payload/Example.app/              the same bundle layout
Payload/Example.app/Frameworks/
Payload/Example.app/Info.plist
```

A DMG is a disk image containing an `.app`; read it read-only, or use an image reader, and
treat the bundle inside as the artifact. A `.pkg` is an installer script plus payloads; the
bundle is inside the payload, not at the top level.

## Fat binaries and slices

`file` on a modern app reports `Mach-O universal binary with 2 architectures`. Every read that
follows applies to one slice: `otool -arch arm64 -L` and `otool -arch x86_64 -L` can differ,
because a framework may link differently per architecture. Record which slice a finding came
from.

## Encryption state

`LC_ENCRYPTION_INFO` carries `cryptid` and `cryptoff`/`cryptsize`. `cryptid` 0 means the code is
readable. `cryptid` 1 means the pages are encrypted at rest — a store download on a mobile
device is the common case — and the binary you hold may be decrypted only if it was extracted
in a way the store permits. Do not attempt decryption; ask the owner for a build they are
entitled to share.

## Entitlements worth reading

| Entitlement | What it claims |
| --- | --- |
| `com.apple.security.app-sandbox` | The app runs sandboxed |
| `com.apple.security.network.client` / `.server` | Outbound / inbound network |
| `com.apple.security.files.user-selected.read-write` | Files the user picks |
| `keychain-access-groups` | Which keychain items the app can see |
| `com.apple.security.application-groups` | Shared container between app and extensions |
| `com.apple.developer.associated-domains` | Universal links and shared web credentials |
| `get-task-allow` | A development build that can be debugged |

A `get-task-allow` on a distributed build is a finding in itself: it means the binary can be
attached to, and the packaging pipeline is not what it claims.

## Runtime families and where the logic is

| Marker in the bundle | Family | Where the logic lives |
| --- | --- | --- |
| `Electron Framework.framework`, `Resources/app.asar` | Electron | The ASAR, not the Mach-O |
| `Flutter.framework`, `App.framework/App` | Flutter | Dart AOT snapshot in `App.framework` |
| `UnityFramework.framework`, `Data/Managed`, `global-metadata.dat` | Unity IL2CPP | Metadata plus native code; method bodies are `reverse-engineering` |
| `hermes.framework`, `main.jsbundle` | React Native | The JS bundle, Hermes bytecode |
| none of the above | Native | The Mach-O itself |

The marker is a path segment, so `MyApp.framework` does not make an app Flutter and a
`Preact.framework` is not React. Confirm the pairing before moving the analysis.

## Signing, and what it proves

`codesign -dv --verbose=4 ./Example.app` names the authority, the identifier and the
notarization ticket. A valid signature says who signed these bytes and that they have not
changed since; it says nothing about what the code does or whether the app is trustworthy.
An ad-hoc signature (`Signature=adhoc`) means no identity at all, which is normal for a local
build and a red flag for something that arrived by email.

## IPS crash reports

An `.ips` file is a JSON header followed by a JSON payload. Read `bug_type`, `os_version`,
`incident_id`, the exception type, the faulting thread's frames and the binary images table,
which maps addresses to images. Symbolication belongs to `crash-triage`; this skill only
covers the artifact's shape when it turns up inside a bundle under analysis.

## What the bundle cannot prove

The bundle shows what ships and what the signer claimed. What the app does at run time, what
the server does with its data, and whether the store build matches the copy in hand are
separate claims, each with its own evidence.
