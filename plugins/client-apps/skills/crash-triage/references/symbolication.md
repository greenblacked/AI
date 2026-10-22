# Symbolication

How to tell a stack is unsymbolicated, how to symbolicate one locally, and how to make
the build pipeline do it for every build. Read this at step 2 as soon as any top frame
is unreadable.

## Contents

- [The rule](#the-rule)
- [iOS](#ios)
- [Android, Kotlin and Java](#android-kotlin-and-java)
- [Android native code](#android-native-code)
- [Flutter and React Native](#flutter-and-react-native)
- [Pipeline checklist](#pipeline-checklist)
- [Recovering a build that already shipped](#recovering-a-build-that-already-shipped)

## The rule

Symbols are matched by an identifier unique to each build — a Mach-O UUID on Apple
platforms, a version code for an R8 mapping file, an ELF Build ID for a native library.
A rebuild from the same commit usually produces a different identifier, so the only
symbols that work are the ones produced by the build that shipped. Treat them as release
artefacts with the same retention as the binary.

## iOS

- **Produce them:** Release builds need `DEBUG_INFORMATION_FORMAT = dwarf-with-dsym`.
  The archive's `dSYMs` folder holds one per binary, including embedded frameworks.
  Binary frameworks from vendors need their own dSYMs from the vendor.
- **Check a match:** the crash report's Binary Images section lists each image's UUID.
  `dwarfdump --uuid App.app.dSYM` prints the dSYM's UUIDs per architecture. They must
  match exactly.
- **Find one locally:** `mdfind "com_apple_xcode_dsym_uuids == <UUID>"` searches
  Spotlight's index of dSYMs on the Mac that built the archive.
- **Symbolicate one frame:** `atos -arch arm64 -o App.app.dSYM/Contents/Resources/DWARF/App -l <load address> <frame address>`,
  with the load address from Binary Images.
- **Upload:** Crashlytics ships a run-script phase and an `upload-symbols` tool
  (`upload-symbols -gsp GoogleService-Info.plist -p ios <path to dSYMs>`); Sentry uses
  `sentry-cli debug-files upload`, and `sentry-cli debug-files check` reports what a file
  contains. Xcode Organizer symbolicates its own crash reports when symbols are included
  with the App Store upload.
- Since Bitcode was deprecated in Xcode 14, the App Store no longer recompiles the
  binary, so the archive's own dSYMs are the right ones. Older Bitcode builds needed
  dSYMs downloaded from App Store Connect.

## Android, Kotlin and Java

- **Tell-tale:** frames such as `a.b.c(SourceFile:12)` or `com.example.a.b(Unknown Source)`.
- **Produce it:** with R8 enabled, each release variant writes
  `app/build/outputs/mapping/<variant>/mapping.txt`. It is valid only for that build.
- **Symbolicate locally:** R8's `retrace` tool, shipped with the Android SDK command-line
  tools, takes the mapping file and a stack trace file.
- **Upload:** Play reads the mapping from the app bundle's metadata on recent Android
  Gradle Plugin versions, or from a manual upload against the version in the Play
  Console. Crashlytics' and Sentry's Gradle plugins upload it per build; confirm the task
  ran in the release build log, not just that the plugin is applied.

## Android native code

- **Tell-tale:** tombstone frames with a `pc` offset into a `.so` and a `BuildId`, but no
  function name.
- **Produce them:** keep the unstripped libraries from the build. Setting
  `debugSymbolLevel` to `SYMBOL_TABLE` or `FULL` in the `ndk` block of `defaultConfig`
  packages symbols into the app bundle for Play. `readelf -n libfoo.so` prints a
  library's Build ID for matching.
- **Symbolicate locally:** `ndk-stack -sym <dir of unstripped libs for the ABI> -dump tombstone.txt`.
- **Upload:** Crashlytics needs native symbol upload enabled in its Gradle extension;
  Sentry's `sentry-cli debug-files upload` accepts ELF files.
- A crash inside a third-party SDK's library needs that vendor's symbols; ask for them
  or report the Build ID and offset to the vendor.

## Flutter and React Native

- **Flutter:** building with `--obfuscate --split-debug-info=<dir>` writes Dart symbol
  files per architecture. `flutter symbolize -i <stack file> -d <symbols file>` decodes a
  stack locally; crash services need those files uploaded per build (Crashlytics through
  the Firebase CLI's `crashlytics:symbols:upload`).
- **React Native:** upload the JavaScript bundle's source map per build, and the Hermes
  source map when Hermes is enabled; the native side still needs dSYMs and the R8 mapping
  as above.

## Pipeline checklist

1. The release build fails if a symbol upload step fails, rather than shipping a build
   whose crashes nobody can read.
2. Symbols are archived as build artefacts keyed by version and build number, kept for as
   long as that version can still be installed.
3. The crash service's "missing symbols" or "missing dSYM" warning is checked after each
   release, and a missing one is treated as a pipeline incident.
4. Every binary framework and native SDK is listed with where its symbols come from.

## Recovering a build that already shipped

- Look first in CI artefacts, the Xcode archive on the build machine, and the Play Console
  or App Store Connect for that version.
- A rebuild from the same commit rarely matches the UUID or Build ID, so it will not
  symbolicate the field's reports.
- If the symbols are gone, record that the version's crashes are unreadable, fix the
  pipeline for the next build, and triage that version by the next build's reports of the
  same signature.
