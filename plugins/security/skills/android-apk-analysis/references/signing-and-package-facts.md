# Signing, splits and package facts

Read after the target digest is recorded and before decompiling. Everything here is read
from the package, not from a store listing.

## Contents

- [Signing schemes](#signing-schemes)
- [AAB is not an APK](#aab-is-not-an-apk)
- [Split sets](#split-sets)
- [Manifest and configured behaviour](#manifest-and-configured-behaviour)
- [Native libraries](#native-libraries)

## Signing schemes

An APK can carry several schemes at once, and which ones are present decides what a
tampered build can get away with:

| Scheme | Where it lives | What it covers |
| --- | --- | --- |
| v1 (JAR) | `META-INF/*.SF`, `*.RSA`/`*.DSA`/`*.EC` | Every entry's digest, per file |
| v2 | APK Signing Block, before the central directory | The whole archive, byte ranges |
| v3 | APK Signing Block | The archive plus a key-rotation lineage |
| v3.1 | APK Signing Block | Rotation for SDK 33+ consumers |
| v4 | A detached `.idsig` beside the APK | Incremental installs only |

Read them with the SDK's own verifier rather than by unzipping `META-INF`:

```bash
apksigner verify --print-certs --verbose ./app.apk
```

The output names each scheme verified, the signer certificate's SHA-256 and, when a
lineage is present, the rotation history. A package with v2/v3 but no v1 is normal for a
modern build; a package with v1 only is a signal about its age or its build pipeline, not
proof of tampering. A v1 signature on a build whose v2 block is absent is also what a
naive repackager produces.

For a package pulled from a device, the certificate proves only that the same key signed
it as the build you compare against. It does not prove the publisher, the store, or that
the code is unmodified since signing.

## AAB is not an APK

An Android App Bundle is a publishing format, not an installable artifact. It is a zip
whose `base/` directory holds a protobuf manifest (`manifest/AndroidManifest.xml`), dex
files under `dex/`, resources under `res/`, and a `BundleConfig.pb`. Do not hand it to
`apktool` and read the protobuf as XML.

Generate the artifacts a device would receive:

```bash
bundletool build-apks --bundle=./app.aab --output=./app.apks --mode=universal
unzip -l ./app.apks          # contains universal.apk and the split set
bundletool dump manifest --bundle=./app.aab
```

`--mode=universal` produces one APK with every ABI and density, which is convenient for
reading and misleading about what most devices download. For the shipped split set, use
the default mode and inspect `splits/`; behaviour in a feature or config split is invisible
in `base.apk`.

## Split sets

A device install may be a base APK plus several `split_config.*.apk` files. Pull every
one before analysing:

```bash
adb shell pm path com.example.app
adb pull /data/app/.../base.apk
adb pull /data/app/.../split_config.arm64_v8a.apk
```

Record the SHA-256 per split and the version code each declares; a mismatched split set is
a finding. Native libraries usually live only in the ABI split, resources and locale
strings in config splits, and a feature module can carry both dex and native code.

## Manifest and configured behaviour

The manifest in an APK is binary XML. Read it with a decoder rather than `strings`:

```bash
aapt2 dump badging ./app.apk
apktool d -s ./app.apk -o ./decoded      # -s keeps dex compressed, skips disassembly
aapt2 dump xmltree --file AndroidManifest.xml ./app.apk
```

Record, at minimum:

- package name, version code, version name, min and target SDK;
- requested permissions, separating dangerous from normal and signature level;
- exported activities, services, receivers and providers, with their intent filters;
- `sharedUserId`, `debuggable`, `allowBackup`, `usesCleartextTraffic`;
- `networkSecurityConfig`, and whether it permits cleartext to any host;
- `android:process`, for components that run outside the main process.

Exported components and boot or package-added receivers are where background behaviour
usually starts. A permission the manifest requests is a capability the app may use, not
proof that it does; the code path still has to be read.

## Native libraries

List them per ABI before reading the code:

```bash
unzip -l ./app.apk | grep 'lib/'
```

A library under `lib/arm64-v8a/` is an ELF; take it to `native-binaries` under
`reverse-engineering` rather than to a DEX decompiler. A package with no native library
still reaches native code through the platform, which is a different claim.
